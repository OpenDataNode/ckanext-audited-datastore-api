from setuptools import setup, find_packages

version = '1.2.1'

setup(
    name='ckanext-audited-datastore-api',
    version=version,
    description="""
    Adds audited forms api calls for datastore_create and datastore_upsert
    """,
    long_description="""
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Martin Virag',
    author_email='martin.virag@eea.sk',
    url='',
    license='',
    packages=find_packages(exclude=['examples', 'tests']),
    namespace_packages=['ckanext',
                        'ckanext.audited_datastore',
                        ],
    package_data={'': [
                       'i18n/*/LC_MESSAGES/*.po',
                       ]
                  },
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.html', 'ckan', None),
        ]
    }, # for babel.extract_messages, says which are source files for translating
    entry_points=\
    """
    [ckan.plugins]
    audited_datastore=ckanext.audited_datastore.plugin:AuditedDatastorePlugin
    """,
)