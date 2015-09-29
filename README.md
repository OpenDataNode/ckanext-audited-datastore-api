ckanext-audited-datastore
-------

CKAN extension that makes wrapped API calls for audited access to CKAN datastore resources. This
extension adds two new API calls:

* /api/action/audited_datastore_create
* /api/action/audited_datastore_update

audited_datastore_create
-------
Wrapper on datastore_create API call. Adds two new timestamp columns / fields:

* modified_timestamp
* deleted_timestamp

This API calls all the parameters as datastore_create and adds an optional parameter:

* update_time (ISO date time) - time set to modified_timestamp when creating records (optional). If not given, system actual time will be used.
* primary_key - changed to mandatory parameter (see datastore_create)

audited_datastore_update
-------
Wrapper on datastore_upsert API call. Ensures that only changed records to be updated (The modified_timestamp
to be set). For the missing records in given parameters, also sets the deleted_timestamp field.

Additional parameters:

* update_time (ISO date time) - time set to modified_timestamp for records updated by this API call (optional). If not given, system actual time will be used.
* delete_absent (boolean) - if True, records not present in the API request will be marked as deleted (optional, default value is True)

In the response JSON, there are only records that were created/updated (have only modified_timestamp set) or
'deleted' (have modified_timestamp and deleted_timestamp set).

Installation
-------

Activate ckan virtualenv ``` . /usr/lib/ckan/default/bin/activate ```

From the extension folder start the installation: ``` python setup.py install ```

Add extension to ckan config: /etc/ckan/default/production.ini

```ApacheConf
ckan.plugins = audited_datastore
```

Restart application server.

Licenses
-------

[GNU Affero General Public License, Version 3.0](http://www.gnu.org/licenses/agpl-3.0.html) is used for licensing of the code (see LICENSE)