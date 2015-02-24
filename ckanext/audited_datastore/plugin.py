'''
Created on 20.2.2015

@author: mvi
'''

import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckanext.datastore.db as db
import ckanext.datastore.logic.schema as dsschema
from ckanext.datastore.logic.action import _check_read_only
import logging
import pylons
import re
import sqlalchemy
from sqlalchemy.exc import (IntegrityError, DBAPIError, DataError)
from datetime import datetime

log = logging.getLogger('ckanext')

NotFound = logic.NotFound
get_action = logic.get_action
_validate = ckan.lib.navl.dictization_functions.validate
LAST_MODIFIED_COLUMN = 'modified_timestamp'
DELETED_TIME_COLUMN = 'deleted_timestamp'
UPDATE_TIMESTAMP_FIELD = 'update_time'

# ==================== AUTH methods ====================

def audited_datastore_create_auth(context, data_dict=None):
    logic.check_access('datastore_create', context, data_dict)
    return {'success': True }


def audited_datastore_update_auth(context, data_dict=None):
    logic.check_access('datastore_upsert', context, data_dict)
    return {'success': True }

# ==================== api methods ====================

def audited_datastore_create(context, data_dict=None):
    logic.check_access('audited_datastore_create', context, data_dict)
    log.debug('starting: audited_datastore_create')
    
    check_and_bust('fields', data_dict)
    check_and_bust('records', data_dict)

    data_dict['fields'].append({"id": LAST_MODIFIED_COLUMN, "type": "timestamp"})
    data_dict['fields'].append({"id": DELETED_TIME_COLUMN, "type": "timestamp"})
    
    update_time = data_dict.pop(UPDATE_TIMESTAMP_FIELD, str(datetime.utcnow()))
    
    if re.compile('[+-]\d\d:\d\d$').search(update_time):
        update_time = to_timestamp_naive(update_time)
    
    for record in data_dict['records']:
        record[LAST_MODIFIED_COLUMN] = update_time
        record[DELETED_TIME_COLUMN] = None
    
    return get_action('datastore_create')(context, data_dict)   
    

def audited_datastore_update(context, data_dict=None):
    logic.check_access('audited_datastore_update', context, data_dict)
    log.debug('starting: audited_datastore_update')
    
    # most of this copy pasted from datastore_upsert
    
    schema = context.get('schema', dsschema.datastore_upsert_schema())
    schema.pop('__junk', None)
    records = data_dict.pop('records', None)
    update_time = data_dict.pop(UPDATE_TIMESTAMP_FIELD, str(datetime.utcnow()))
    
    if re.compile('[+-]\d\d:\d\d$').search(update_time):
        update_time = to_timestamp_naive(update_time)
    
    data_dict, errors = _validate(data_dict, schema, context)
    
    if errors:
        raise tk.ValidationError(errors)

    _check_read_only(context, data_dict)

    data_dict['connection_url'] = pylons.config['ckan.datastore.write_url']

    res_id = data_dict['resource_id']
    resources_sql = sqlalchemy.text(u'''SELECT 1 FROM "_table_metadata"
                                        WHERE name = :id AND alias_of IS NULL''')
    results = db._get_engine(data_dict).execute(resources_sql, id=res_id)
    res_exists = results.rowcount > 0

    if not res_exists:
        raise tk.ObjectNotFound(tk._(
            u'Resource "{0}" was not found.'.format(res_id)
        ))

    result = do_audit(context, data_dict, records, update_time)

    result.pop('id', None)
    result.pop('connection_url')
    return result
    
    

# ==================== help methods ====================

def to_timestamp_naive(datetime_str):
    from dateutil.parser import parse
    datetime = parse(datetime_str)
    naive = datetime.replace(tzinfo=None) - datetime.utcoffset()
    return naive.isoformat(' ')

def check_and_bust(key, dict):
    if key not in dict or not dict[key]:
        raise NotFound("Key '{0}' was not found or has no value set.".format(key))


def transaction_search(context, data_dict, timeout):
    fields = []
    fields[:] = [field.get('id') for field in db._get_fields(context, data_dict)]
    try:
        # check if table already existes
        context['connection'].execute(
            u'SET LOCAL statement_timeout TO {0}'.format(timeout))
        
        dict_search = {
            'resource_id': data_dict['resource_id'],
            'fields': fields
        }
        return db.search_data(context, dict_search)
    except DBAPIError, e:
        if e.orig.pgcode == db._PG_ERR_CODE['query_canceled']:
            raise db.ValidationError({
                'query': ['Search took too long']
            })
        raise db.ValidationError({
            'query': ['Invalid query'],
            'info': {
                'statement': [e.statement],
                'params': [e.params],
                'orig': [str(e.orig)]
            }
        })
        context['connection'].close()
    
    return None


def transaction_upsert(context, data_dict, timeout, trans):
    try:
        db.upsert_data(context, data_dict)
        trans.commit()
        return db._unrename_json_field(data_dict)
    except IntegrityError, e:
        if e.orig.pgcode == db._PG_ERR_CODE['unique_violation']:
            raise db.ValidationError({
                'constraints': ['Cannot insert records or create index because'
                                ' of uniqueness constraint'],
                'info': {
                    'orig': str(e.orig),
                    'pgcode': e.orig.pgcode
                }
            })
        raise
    except DataError, e:
        raise db.ValidationError({
            'data': e.message,
            'info': {
                'orig': [str(e.orig)]
            }})
    except DBAPIError, e:
        if e.orig.pgcode == db._PG_ERR_CODE['query_canceled']:
            raise db.ValidationError({
                'query': ['Query took too long']
            })
        raise
    except Exception, e:
        trans.rollback()
        raise
    finally:
        context['connection'].close()


def transaction_audit(context, data_dict, old_records, new_records, update_time, primary_keys):
    for record in old_records['records']:
        pks = {}
        
        for pk in primary_keys:
            pks[pk] = record.get(pk)
        
        new_record = pop_item(new_records, pks)
    
        if not new_record:
            if record[DELETED_TIME_COLUMN]:
                # already deleted
                continue
            # delete
            record[DELETED_TIME_COLUMN] = update_time
            record[LAST_MODIFIED_COLUMN] = update_time
            data_dict['records'].append(record)
    
        elif should_update(record, new_record):
            # update
            new_record[DELETED_TIME_COLUMN] = None
            new_record[LAST_MODIFIED_COLUMN] = update_time
            data_dict['records'].append(new_record)
    
    # what was left = new records => create
    for new_record in new_records:
        new_record[DELETED_TIME_COLUMN] = None
        new_record[LAST_MODIFIED_COLUMN] = update_time
        data_dict['records'].append(new_record)


def do_audit(context, data_dict, new_records, update_time):
    engine = db._get_engine(data_dict)
    context['connection'] = engine.connect()
    timeout = context.get('query_timeout', db._TIMEOUT)

    trans = context['connection'].begin()
    
    primary_keys = db._get_unique_key(context, data_dict)
    
    # DO SEARCH
    log.debug('starting SEARCH phase')
    old_records = transaction_search(context, data_dict, timeout)
    
    # audit data
    log.debug('starting AUDIT phase')
    data_dict['records'] = []
    transaction_audit(context, data_dict, old_records, new_records, update_time, primary_keys)
              
    # DO UPSERT
    log.debug('starting UPSERT phase')
    data_dict.pop('__junk', None)
    
    return transaction_upsert(context, data_dict, timeout, trans)


def should_update(old_record, new_record):
    del_ts = old_record.pop(DELETED_TIME_COLUMN)
    upd_ts = old_record.pop(LAST_MODIFIED_COLUMN)
    
    # update if:
    #    1. column is different
    #    2. its 'deleted' record
    if del_ts or cmp(old_record, new_record) != 0:
        return True
    
    return False

# TODO optimalize
def pop_item(dict_list, primary_keys):

    for i in range(len(dict_list)):
        check = True
        item = dict_list[i]
        for pk in primary_keys.keys():
            if item.get(pk) != primary_keys.get(pk):
                check = False
                break
        if check:
            return dict_list.pop(i)
        
    return None
    

# ==================== plugin ====================

class AuditedDatastorePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)

    def get_auth_functions(self):
        return {
                'audited_datastore_create': audited_datastore_create_auth,
                'audited_datastore_update': audited_datastore_update_auth,
        }
    
    def get_actions(self):
        return {
                'audited_datastore_create': audited_datastore_create,
                'audited_datastore_update': audited_datastore_update,
        }

