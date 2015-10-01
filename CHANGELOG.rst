---------
Changelog
---------

v1.2.1-SNAPSHOT 2015-10-01

Bug fixes:
 * "primary_key" parameter is mandatory when calling audited_datastore_create
 * internal error while comparing timestamps

Features:
 * added paramter "delete_absent" (default value is True). When True records not present in the records will be deleted

v1.2.0 2015-09-28

Bug fixes:
 * fixed changed method parameters in CKAN version 2.3

v1.1.2 2015-08-11

Bug fixes:
 * Datastore resource not updating records properly if there are more than 100 records
 * Changed i18n .po file name, so it wouldn't clash with the names of other CKAN plugins

Notes:
 * To unify versions with ODN releases, the version jumped from 0.2.0 to 1.1.2

v0.2.0 2015-04-22

Bug fixes:
 * transition changes from CKAN v2.2.X to v2.3

v0.1.3 2015-04-22

Bug fixes:
 * couldn't create resource in one step with making it datastore resource