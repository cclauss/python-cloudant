#!/usr/bin/env python
# Copyright (c) 2015 IBM. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
_design_document_tests_

design_document module - Unit tests for the DesignDocument class

See configuration options for environment variables in unit_t_db_base
module docstring.

"""
import os
import unittest

from cloudant.document import Document 
from cloudant.design_document import DesignDocument
from cloudant.view import View, QueryIndexView
from cloudant.error import CloudantArgumentError, CloudantException

from .unit_t_db_base import UnitTestDbBase

class DesignDocumentTests(UnitTestDbBase):
    """
    DesignDocument unit tests
    """

    def setUp(self):
        """
        Set up test attributes
        """
        super(DesignDocumentTests, self).setUp()
        self.db_set_up()

    def tearDown(self):
        """
        Reset test attributes
        """
        self.db_tear_down()
        super(DesignDocumentTests, self).tearDown()

    def test_constructor_with_docid(self):
        """
        Test instantiating a DesignDocument providing an id
        not prefaced with '_design/'
        """
        ddoc = DesignDocument(self.db, 'ddoc001')
        self.assertIsInstance(ddoc, DesignDocument)
        self.assertEqual(ddoc.get('_id'), '_design/ddoc001')
        self.assertEqual(ddoc.get('views'), {})

    def test_constructor_with_design_docid(self):
        """
        Test instantiating a DesignDocument providing an id
        prefaced with '_design/'
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        self.assertIsInstance(ddoc, DesignDocument)
        self.assertEqual(ddoc.get('_id'), '_design/ddoc001')
        self.assertEqual(ddoc.get('views'), {})

    def test_constructor_without_docid(self):
        """
        Test instantiating a DesignDocument without providing an id
        """
        ddoc = DesignDocument(self.db)
        self.assertIsInstance(ddoc, DesignDocument)
        self.assertIsNone(ddoc.get('_id'))
        self.assertEqual(ddoc.get('views'), {})

    def test_create_design_document_with_docid_encoded_url(self):
        """
        Test creating a design document providing an id that has an encoded url
        """
        ddoc = DesignDocument(self.db, '_design/http://example.com')
        self.assertFalse(ddoc.exists())
        self.assertIsNone(ddoc.get('_rev'))
        ddoc.create()
        self.assertTrue(ddoc.exists())
        self.assertTrue(ddoc.get('_rev').startswith('1-'))

    def test_fetch_existing_design_document_with_docid_encoded_url(self):
        """
        Test fetching design document content from an existing document where
        the document id requires an encoded url
        """
        ddoc = DesignDocument(self.db, '_design/http://example.com')
        ddoc.create()
        new_ddoc = DesignDocument(self.db, '_design/http://example.com')
        new_ddoc.fetch()
        self.assertEqual(new_ddoc, ddoc)

    def test_update_design_document_with_encoded_url(self):
        """
        Test that updating a design document where the document id requires that
        the document url be encoded is successful.
        """
        # First create the design document
        ddoc = DesignDocument(self.db, '_design/http://example.com')
        ddoc.save()
        # Now test that the design document gets updated
        ddoc.save()
        self.assertTrue(ddoc['_rev'].startswith('2-'))
        remote_ddoc = DesignDocument(self.db, '_design/http://example.com')
        remote_ddoc.fetch()
        self.assertEqual(remote_ddoc, ddoc)

    def test_delete_design_document_success_with_encoded_url(self):
        """
        Test that we can remove a design document from the remote
        database successfully when the document id requires an encoded url.
        """
        ddoc = DesignDocument(self.db, '_design/http://example.com')
        ddoc.create()
        self.assertTrue(ddoc.exists())
        ddoc.delete()
        self.assertFalse(ddoc.exists())
        self.assertEqual(ddoc, {'_id': '_design/http://example.com'})

    def test_add_a_view(self):
        """
        Test that adding a view adds a View object to
        the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        self.assertEqual(ddoc.get('views'), {})
        ddoc.add_view(
            'view001',
            'function (doc) {\n  emit(doc._id, 1);\n}'
        )
        self.assertListEqual(list(ddoc.get('views').keys()), ['view001'])
        self.assertIsInstance(ddoc.get('views')['view001'], View)
        self.assertEqual(
            ddoc.get('views')['view001'],
            {'map': 'function (doc) {\n  emit(doc._id, 1);\n}'}
        )

    def test_adding_existing_view(self):
        """
        Test that adding an existing view fails as expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_view(
            'view001',
            'function (doc) {\n  emit(doc._id, 1);\n}'
        )
        try:
            ddoc.add_view('view001', 'function (doc) {\n  emit(doc._id, 2);\n}')
            self.fail('Above statement should raise an Exception')
        except CloudantArgumentError as err:
            self.assertEqual(
                str(err),
                'View view001 already exists in this design doc'
            )

    def test_adding_query_index_view(self):
        """
        Test that adding a query index view fails as expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc['language'] = 'query'
        with self.assertRaises(CloudantException) as cm:
            ddoc.add_view('view001', {'foo': 'bar'})
        err = cm.exception
        self.assertEqual(
            str(err),
            'Cannot add a MapReduce view to a '
            'design document for query indexes.'
        )

    def test_update_a_view(self):
        """
        Test that updating a view updates the contents of the correct
        View object in the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_view('view001', 'not-a-valid-map-function')
        self.assertEqual(
            ddoc.get('views')['view001'],
            {'map': 'not-a-valid-map-function'}
        )
        ddoc.update_view(
            'view001',
            'function (doc) {\n  emit(doc._id, 1);\n}'
        )
        self.assertEqual(
            ddoc.get('views')['view001'],
            {'map': 'function (doc) {\n  emit(doc._id, 1);\n}'}
        )

    def test_update_non_existing_view(self):
        """
        Test that updating a non-existing view fails as expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        try:
            ddoc.update_view(
                'view001',
                'function (doc) {\n  emit(doc._id, 1);\n}'
            )
            self.fail('Above statement should raise an Exception')
        except CloudantArgumentError as err:
            self.assertEqual(
                str(err),
                'View view001 does not exist in this design doc'
            )

    def test_update_query_index_view(self):
        """
        Test that updating a query index view fails as expected.
        """
        # This is not the preferred way of dealing with query index
        # views but it works best for this test.
        data = {
            '_id': '_design/ddoc001',
            'language': 'query',
            'views': {
                'view001': {'map': {'fields': {'name': 'asc', 'age': 'asc'}},
                            'reduce': '_count',
                            'options': {'def': {'fields': ['name', 'age']},
                                        'w': 2}
                            }
                    }
        }
        self.db.create_document(data)
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.fetch()
        with self.assertRaises(CloudantException) as cm:
            ddoc.update_view(
                'view001',
                'function (doc) {\n  emit(doc._id, 1);\n}'
            )
        err = cm.exception
        self.assertEqual(
            str(err),
            'Cannot update a query index view using this method.'
        )

    def test_delete_a_view(self):
        """
        Test deleting a view from the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_view('view001', 'function (doc) {\n  emit(doc._id, 1);\n}')
        self.assertEqual(
            ddoc.get('views')['view001'],
            {'map': 'function (doc) {\n  emit(doc._id, 1);\n}'}
        )
        ddoc.delete_view('view001')
        self.assertEqual(ddoc.get('views'), {})

    def test_delete_a_query_index_view(self):
        """
        Test deleting a query index view fails as expected.
        """
        # This is not the preferred way of dealing with query index
        # views but it works best for this test.
        data = {
            '_id': '_design/ddoc001',
            'language': 'query',
            'views': {
                'view001': {'map': {'fields': {'name': 'asc', 'age': 'asc'}},
                            'reduce': '_count',
                            'options': {'def': {'fields': ['name', 'age']},
                                        'w': 2}
                            }
                    }
        }
        self.db.create_document(data)
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.fetch()
        with self.assertRaises(CloudantException) as cm:
            ddoc.delete_view('view001')
        err = cm.exception
        self.assertEqual(
            str(err),
            'Cannot delete a query index view using this method.'
        )

    def test_fetch_map_reduce(self):
        """
        Ensure that the document fetch from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing MapReduce views.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        view_map = 'function (doc) {\n  emit(doc._id, 1);\n}'
        view_reduce = '_count'
        db_copy = '{0}-copy'.format(self.db.database_name)
        ddoc.add_view('view001', view_map, view_reduce)
        ddoc.add_view('view002', view_map, view_reduce, dbcopy=db_copy)
        ddoc.add_view('view003', view_map)
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        self.assertNotEqual(ddoc_remote, ddoc)
        ddoc_remote.fetch()
        self.assertEqual(ddoc_remote, ddoc)
        self.assertTrue(ddoc_remote['_rev'].startswith('1-'))
        self.assertEqual(ddoc_remote, {
            '_id': '_design/ddoc001',
            '_rev': ddoc['_rev'],
            'lists': {},
            'indexes': {},
            'views': {
                'view001': {'map': view_map, 'reduce': view_reduce},
                'view002': {'map': view_map, 'reduce': view_reduce, 'dbcopy': db_copy},
                'view003': {'map': view_map}
            }
        })
        self.assertIsInstance(ddoc_remote['views']['view001'], View)
        self.assertIsInstance(ddoc_remote['views']['view002'], View)
        self.assertIsInstance(ddoc_remote['views']['view003'], View)

    def test_fetch_no_views(self):
        """
        Ensure that the document fetched from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing no views.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        ddoc_remote.fetch()
        self.assertEqual(set(ddoc_remote.keys()),
                         {'_id', '_rev', 'indexes', 'views', 'lists'})
        self.assertEqual(ddoc_remote['_id'], '_design/ddoc001')
        self.assertTrue(ddoc_remote['_rev'].startswith('1-'))
        self.assertEqual(ddoc_remote['_rev'], ddoc['_rev'])
        self.assertEqual(ddoc_remote.views, {})

    def test_fetch_query_views(self):
        """
        Ensure that the document fetch from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing query index views.
        """
        # This is not the preferred way of dealing with query index
        # views but it works best for this test.
        data = {
            '_id': '_design/ddoc001',
            'indexes': {},
            'lists': {},
            'language': 'query',
            'views': {
                'view001': {'map': {'fields': {'name': 'asc', 'age': 'asc'}},
                            'reduce': '_count',
                            'options': {'def': {'fields': ['name', 'age']},
                                        'w': 2}
                            }
                    }
        }
        doc = self.db.create_document(data)
        self.assertIsInstance(doc, Document)
        data['_rev'] = doc['_rev']
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.fetch()
        self.assertIsInstance(ddoc, DesignDocument)
        self.assertEqual(ddoc, data)
        self.assertIsInstance(ddoc['views']['view001'], QueryIndexView)

    def test_fetch_text_indexes(self):
        """
        Ensure that the document fetch from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing query index views.
        """
        # This is not the preferred way of dealing with query index
        # views but it works best for this test.
        data = {
            '_id': '_design/ddoc001',
            'language': 'query',
            'lists': {},
            'indexes': {'index001':
                     {'index': {'index_array_lengths': True,
                                'fields': [{'name': 'name', 'type': 'string'},
                                           {'name': 'age', 'type': 'number'}],
                                'default_field': {'enabled': True,
                                                  'analyzer': 'german'},
                                'default_analyzer': 'keyword',
                                'selector': {}},
                      'analyzer': {'name': 'perfield',
                                   'default': 'keyword',
                                   'fields': {'$default': 'german'}}}}}
        doc = self.db.create_document(data)
        self.assertIsInstance(doc, Document)
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.fetch()
        self.assertIsInstance(ddoc, DesignDocument)
        data['_rev'] = doc['_rev']
        data['views'] = dict()
        self.assertEqual(ddoc, data)
        self.assertIsInstance(ddoc['indexes']['index001'], dict)

    def test_fetch_text_indexes_and_query_views(self):
        """
        Ensure that the document fetch from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing query index views and text index definitions.
        """
        # This is not the preferred way of dealing with query index
        # views but it works best for this test.
        data = {
            '_id': '_design/ddoc001',
            'language': 'query',
            'lists': {},
            'views': {
                'view001': {'map': {'fields': {'name': 'asc', 'age': 'asc'}},
                            'reduce': '_count',
                            'options': {'def': {'fields': ['name', 'age']},
                                        'w': 2}
                            }
                    },
            'indexes': {'index001': {
                'index': {'index_array_lengths': True,
                          'fields': [{'name': 'name', 'type': 'string'},
                                     {'name': 'age', 'type': 'number'}],
                          'default_field': {'enabled': True,
                                            'analyzer': 'german'},
                          'default_analyzer': 'keyword',
                          'selector': {}},
                'analyzer': {'name': 'perfield',
                             'default': 'keyword',
                             'fields': {'$default': 'german'}}}}}
        doc = self.db.create_document(data)
        self.assertIsInstance(doc, Document)
        data['_rev'] = doc['_rev']
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.fetch()
        self.assertIsInstance(ddoc, DesignDocument)
        self.assertEqual(ddoc, data)
        self.assertIsInstance(ddoc['indexes']['index001'], dict)
        self.assertIsInstance(ddoc['views']['view001'], QueryIndexView)

    def test_text_index_save_fails_when_lang_is_not_query(self):
        """
        Tests that save fails when language is not query and a search index
        string function is expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc['indexes']['index001'] = {
            'index': {'index_array_lengths': True,
                      'fields': [{'name': 'name', 'type': 'string'},
                                 {'name': 'age', 'type': 'number'}],
                      'default_field': {'enabled': True, 'analyzer': 'german'},
                      'default_analyzer': 'keyword',
                      'selector': {}},
            'analyzer': {'name': 'perfield','default': 'keyword',
                         'fields': {'$default': 'german'}}}
        self.assertIsInstance(ddoc['indexes']['index001']['index'], dict)
        with self.assertRaises(CloudantException) as cm:
            ddoc.save()
        err = cm.exception
        self.assertEqual(
            str(err),
            'Function for search index index001 must be of type string.'
        )

    def test_text_index_save_fails_with_existing_search_index(self):
        """
        Tests that save fails when language is not query and both a query text
        index and a search index exist in the design document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        search_index = ('function (doc) {\n  index("default", doc._id); '
                        'if (doc._id) {index("name", doc.name, '
                        '{"store": true}); }\n}')
        ddoc.add_search_index('search001', search_index)
        self.assertIsInstance(
            ddoc['indexes']['search001']['index'], str
        )
        ddoc.save()
        self.assertTrue(ddoc['_rev'].startswith('1-'))
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        ddoc_remote.fetch()
        ddoc_remote['indexes']['index001'] = {
            'index': {'index_array_lengths': True,
                      'fields': [{'name': 'name', 'type': 'string'},
                                 {'name': 'age', 'type': 'number'}],
                      'default_field': {'enabled': True, 'analyzer': 'german'},
                      'default_analyzer': 'keyword',
                      'selector': {}},
            'analyzer': {'name': 'perfield','default': 'keyword',
                         'fields': {'$default': 'german'}}}
        self.assertIsInstance(ddoc_remote['indexes']['index001']['index'], dict)
        with self.assertRaises(CloudantException) as cm:
            ddoc_remote.save()
        err = cm.exception
        self.assertEqual(
            str(err),
            'Function for search index index001 must be of type string.'
        )

    def test_mr_view_save_fails_when_lang_is_query(self):
        """
        Tests that save fails when language is query but views are map reduce
        views.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        view_map = 'function (doc) {\n  emit(doc._id, 1);\n}'
        view_reduce = '_count'
        db_copy = '{0}-copy'.format(self.db.database_name)
        ddoc.add_view('view001', view_map, view_reduce, dbcopy=db_copy)
        ddoc['language'] = 'query'
        with self.assertRaises(CloudantException) as cm:
            ddoc.save()
        err = cm.exception
        self.assertEqual(
            str(err),
            'View view001 must be of type QueryIndexView.'
        )

    def test_mr_view_save_succeeds(self):
        """
        Tests that save succeeds when no language is specified and views are map
        reduce views.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        view_map = 'function (doc) {\n  emit(doc._id, 1);\n}'
        view_reduce = '_count'
        db_copy = '{0}-copy'.format(self.db.database_name)
        ddoc.add_view('view001', view_map, view_reduce, dbcopy=db_copy)
        ddoc.save()
        self.assertTrue(ddoc['_rev'].startswith('1-'))

    def test_query_view_save_fails_when_lang_is_not_query(self):
        """
        Tests that save fails when language is not query but views are query
        index views.
        """
        # This is not the preferred way of dealing with query index
        # views but it works best for this test.
        data = {
            '_id': '_design/ddoc001',
            'language': 'query',
            'views': {
                'view001': {'map': {'fields': {'name': 'asc', 'age': 'asc'}},
                            'reduce': '_count',
                            'options': {'def': {'fields': ['name', 'age']},
                                        'w': 2}
                            }
                    }
        }
        self.db.create_document(data)
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.fetch()
        with self.assertRaises(CloudantException) as cm:
            ddoc['language'] = 'not-query'
            ddoc.save()
        err = cm.exception
        self.assertEqual(str(err), 'View view001 must be of type View.')

        with self.assertRaises(CloudantException) as cm:
            del ddoc['language']
            ddoc.save()
        err = cm.exception
        self.assertEqual(str(err), 'View view001 must be of type View.')

    def test_query_view_save_succeeds(self):
        """
        Tests that save succeeds when language is query and views are query
        index views.
        """
        # This is not the preferred way of dealing with query index
        # views but it works best for this test.
        data = {
            '_id': '_design/ddoc001',
            'language': 'query',
            'views': {
                'view001': {'map': {'fields': {'name': 'asc', 'age': 'asc'}},
                            'reduce': '_count',
                            'options': {'def': {'fields': ['name', 'age']},
                                        'w': 2}
                            }
                    }
        }
        self.db.create_document(data)
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.fetch()
        self.assertTrue(ddoc['_rev'].startswith('1-'))
        ddoc.save()
        self.assertTrue(ddoc['_rev'].startswith('2-'))

    def test_save_with_no_views(self):
        """
        Tests the functionality when saving a design document without a view.
        The locally cached DesignDocument should contain an empty views dict
        while the design document saved remotely should not include the empty
        views sub-document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.save()
        # Ensure that locally cached DesignDocument contains an
        # empty views dict.
        self.assertEqual(set(ddoc.keys()), {'_id', '_rev', 'indexes', 'views', 'lists'})
        self.assertEqual(ddoc['_id'], '_design/ddoc001')
        self.assertTrue(ddoc['_rev'].startswith('1-'))
        self.assertEqual(ddoc.views, {})
        # Ensure that remotely saved design document does not
        # include a views sub-document.
        resp = self.client.r_session.get(ddoc.document_url)
        raw_ddoc = resp.json()
        self.assertEqual(set(raw_ddoc.keys()), {'_id', '_rev'})
        self.assertEqual(raw_ddoc['_id'], ddoc['_id'])
        self.assertEqual(raw_ddoc['_rev'], ddoc['_rev'])

    def test_setting_id(self):
        """
        Ensure when setting the design document id that it is
        prefaced by '_design/'
        """
        ddoc = DesignDocument(self.db)
        ddoc['_id'] = 'ddoc001'
        self.assertEqual(ddoc['_id'], '_design/ddoc001')
        del ddoc['_id']
        self.assertIsNone(ddoc.get('_id'))
        ddoc['_id'] = '_design/ddoc002'
        self.assertEqual(ddoc['_id'], '_design/ddoc002')

    def test_iterating_over_views(self):
        """
        Test iterating over views within the DesignDocument
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        view_map = 'function (doc) {\n  emit(doc._id, 1);\n}'
        ddoc.add_view('view001', view_map)
        ddoc.add_view('view002', view_map)
        ddoc.add_view('view003', view_map)
        view_names = []
        for view_name, view in ddoc.iterviews():
            self.assertIsInstance(view, View)
            view_names.append(view_name)
        self.assertTrue(
            all(x in view_names for x in ['view001', 'view002', 'view003'])
        )

    def test_list_views(self):
        """
        Test the retrieval of view name list from DesignDocument
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        view_map = 'function (doc) {\n  emit(doc._id, 1);\n}'
        ddoc.add_view('view001', view_map)
        ddoc.add_view('view002', view_map)
        ddoc.add_view('view003', view_map)
        self.assertTrue(
            all(x in ddoc.list_views() for x in [
                'view001',
                'view002',
                'view003'
            ])
        )

    def test_get_view(self):
        """
        Test retrieval of a view from the DesignDocument
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        view_map = 'function (doc) {\n  emit(doc._id, 1);\n}'
        view_reduce = '_count'
        ddoc.add_view('view001', view_map)
        ddoc.add_view('view002', view_map, view_reduce)
        ddoc.add_view('view003', view_map)
        self.assertIsInstance(ddoc.get_view('view002'), View)
        self.assertEqual(
            ddoc.get_view('view002'),
            {
            'map': 'function (doc) {\n  emit(doc._id, 1);\n}',
            'reduce': '_count'
            }
        )

    def test_get_info(self):
        """
        Test retrieval of info endpoint from the DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        ddoc_remote.fetch()
        info = ddoc_remote.info()
        info['view_index'].pop('signature')
        info['view_index'].pop('disk_size')
        # Remove Cloudant specific sizes object
        if 'sizes' in info['view_index']:
            info['view_index'].pop('sizes')
            name = ddoc_remote['_id']
        else:
            name = 'ddoc001'
        self.assertEqual(
            info,
            {'view_index': {'update_seq': 0, 'waiting_clients': 0,
                            'language': 'javascript',
                            'purge_seq': 0, 'compact_running': False,
                            'waiting_commit': False, 'updater_running': False,
                            'data_size': 0}, 'name': name})

    @unittest.skipUnless(
        os.environ.get('RUN_CLOUDANT_TESTS') is not None,
        'Skipping Cloudant _search_info endpoint test'
    )
    def test_get_search_info(self):
        """
        Test retrieval of search_info endpoint from the DesignDocument.
        """
        self.populate_db_with_documents(100)
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_search_index(
            'search001',
            'function (doc) {\n  index("default", doc._id); '
            'if (doc._id) {index("name", doc.name, {"store": true}); }\n}'
        )
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        ddoc_remote.fetch()
        search_info = ddoc_remote.search_info('search001')
        search_info['search_index'].pop('disk_size')
        self.assertEqual(
            search_info,
            {'name': '_design/ddoc001/search001',
             'search_index': {'doc_del_count': 0, 'doc_count': 100,
                              'pending_seq': 101, 'committed_seq': 0},
             })

    def test_add_a_search_index(self):
        """
        Test that adding a search index adds a search index object to
        the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        self.assertEqual(ddoc.get('indexes'), {})
        ddoc.add_search_index(
            'search001',
            'function (doc) {\n  index("default", doc._id); '
            'if (doc._id) {index("name", doc.name, {"store": true}); }\n}'
        )
        self.assertListEqual(list(ddoc.get('indexes').keys()), ['search001'])
        self.assertEqual(
            ddoc.get('indexes')['search001'],
            {'index': 'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, {"store": true}); }\n}'}
         )

    def test_add_a_search_index_with_analyzer(self):
        """
        Test that adding a search index with an analyzer adds a search index
        object to the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        self.assertEqual(ddoc.get('indexes'), {})
        ddoc.add_search_index(
            'search001',
            'function (doc) {\n  index("default", doc._id); '
            'if (doc._id) {index("name", doc.name, {"store": true}); }\n}',
            {'name': 'perfield', 'default': 'english', 'fields': {
                'spanish': 'spanish'}}
        )
        self.assertListEqual(list(ddoc.get('indexes').keys()), ['search001'])
        self.assertEqual(
            ddoc.get('indexes')['search001'],
            {'index': 'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, {"store": true}); }\n}',
                'analyzer': {"name": "perfield", "default": "english", "fields":
                    {"spanish": "spanish"}}}
         )

    def test_adding_existing_search_index(self):
        """
        Test that adding an existing search index fails as expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_search_index(
            'search001',
            'function (doc) {\n  index("default", doc._id); '
            'if (doc._id) {index("name", doc.name, {"store": true}); }\n}',
        )
        with self.assertRaises(CloudantArgumentError) as cm:
            ddoc.add_search_index(
                'search001',
                'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, '
                '{"store": true}); }\n}'
            )
        err = cm.exception
        self.assertEqual(
            str(err),
            'An index with name search001 already exists in this design doc'
        )

    def test_update_a_search_index(self):
        """
        Test that updating a search index updates the contents of the correct
        search index object in the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_search_index('search001', 'not-a-valid-search-index')
        self.assertEqual(
            ddoc.get('indexes')['search001'],
            {'index': 'not-a-valid-search-index'}
        )
        ddoc.update_search_index(
            'search001',
            'function (doc) {\n  index("default", doc._id); '
            'if (doc._id) {index("name", doc.name, {"store": true}); }\n}',
        )
        self.assertEqual(
            ddoc.get('indexes')['search001'],
            {'index': 'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, '
                '{"store": true}); }\n}'}
        )

    def test_update_a_search_index_with_analyzer(self):
        """
        Test that updating a search analyzer updates the contents of the correct
        search index object in the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_search_index('search001',
                              'not-a-valid-search-index',
                              'email')
        self.assertEqual(
            ddoc.get('indexes')['search001'],
            {'index': 'not-a-valid-search-index', 'analyzer': 'email'}
        )
        ddoc.update_search_index(
            'search001',
            'function (doc) {\n  index("default", doc._id); '
            'if (doc._id) {index("name", doc.name, {"store": true}); }\n}',
            'simple'
        )
        self.assertEqual(
            ddoc.get('indexes')['search001'],
            {'index': 'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, '
                '{"store": true}); }\n}',
             'analyzer': 'simple'
            }
        )

    def test_update_non_existing_search_index(self):
        """
        Test that updating a non-existing search index fails as expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        with self.assertRaises(CloudantArgumentError) as cm:
            ddoc.update_search_index(
                'search001',
                'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, '
                '{"store": true}); }\n}'
            )
        err = cm.exception
        self.assertEqual(
            str(err),
            'An index with name search001 does not exist in this design doc'
        )

    def test_delete_a_search_index(self):
        """
        Test deleting a search index from the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_search_index(
            'search001',
            'function (doc) {\n  index("default", doc._id); '
            'if (doc._id) {index("name", doc.name, '
            '{"store": true}); }\n}'
        )
        self.assertEqual(
            ddoc.get('indexes')['search001'],
            {'index': 'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, '
                '{"store": true}); }\n}'}
        )
        ddoc.delete_index('search001')
        self.assertEqual(ddoc.get('indexes'), {})

    def test_fetch_search_index(self):
        """
        Ensure that the document fetch from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing search indexes.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        search_index = ('function (doc) {\n  index("default", doc._id); '
                        'if (doc._id) {index("name", doc.name, '
                        '{"store": true}); }\n} ')
        ddoc.add_search_index('search001', search_index)
        ddoc.add_search_index('search002', search_index, 'simple')
        ddoc.add_search_index('search003', search_index, 'standard')
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        self.assertNotEqual(ddoc_remote, ddoc)
        ddoc_remote.fetch()
        self.assertEqual(ddoc_remote, ddoc)
        self.assertTrue(ddoc_remote['_rev'].startswith('1-'))
        self.assertEqual(ddoc_remote, {
            '_id': '_design/ddoc001',
            '_rev': ddoc['_rev'],
            'indexes': {
                'search001': {'index': search_index},
                'search002': {'index': search_index, 'analyzer': 'simple'},
                'search003': {'index': search_index, 'analyzer': 'standard'}
            },
            'views': {},
            'lists': {}
        })

    def test_fetch_no_search_index(self):
        """
        Ensure that the document fetched from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing no search indexes.
        The :func:`~cloudant.design_document.DesignDocument.fetch` function
        adds the ``indexes`` key in the locally cached DesignDocument if
        indexes do not exist in the remote design document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        ddoc_remote.fetch()
        self.assertEqual(set(ddoc_remote.keys()),
                         {'_id', '_rev', 'indexes', 'views', 'lists'})
        self.assertEqual(ddoc_remote['_id'], '_design/ddoc001')
        self.assertTrue(ddoc_remote['_rev'].startswith('1-'))
        self.assertEqual(ddoc_remote['_rev'], ddoc['_rev'])
        self.assertEqual(ddoc_remote.indexes, {})

    def test_search_index_save_fails_when_lang_is_query(self):
        """
        Tests that save fails when language is query and a text index dict
        definition is expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc['language'] = 'query'
        ddoc['indexes']['search001'] = {
            'index': 'function (doc) {\n  index("default", doc._id); '
                     'if (doc._id) {index("name", doc.name, '
                     '{"store": true}); }\n}',
            'analyzer': 'standard'}
        self.assertIsInstance(ddoc['indexes']['search001']['index'], str)
        with self.assertRaises(CloudantException) as cm:
            ddoc.save()
        err = cm.exception
        self.assertEqual(
            str(err),
            'Definition for query text index search001 must be of type dict.'
        )

    def test_search_index_save_fails_with_existing_text_index(self):
        """
        Tests that save fails when language is query and both a search index
        and a text index exist in the design document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc['language'] = 'query'
        ddoc['indexes']['index001'] = {
            'index': {'index_array_lengths': True,
                      'fields': [{'name': 'name', 'type': 'string'},
                                 {'name': 'age', 'type': 'number'}],
                      'default_field': {'enabled': True, 'analyzer': 'german'},
                      'default_analyzer': 'keyword',
                      'selector': {}},
            'analyzer': {'name': 'perfield','default': 'keyword',
                         'fields': {'$default': 'german'}}}
        ddoc.save()
        self.assertTrue(ddoc['_rev'].startswith('1-'))
        search_index = ('function (doc) {\n  index("default", doc._id); '
                        'if (doc._id) {index("name", doc.name, '
                        '{"store": true}); }\n}')
        ddoc.add_search_index('search001', search_index)
        self.assertIsInstance(
            ddoc['indexes']['search001']['index'], str
        )
        with self.assertRaises(CloudantException) as cm:
            ddoc.save()
        err = cm.exception
        self.assertEqual(
            str(err),
            'Definition for query text index search001 must be of type dict.'
        )

    def test_search_index_save_succeeds(self):
        """
        Tests that save succeeds when no language is specified for search
        indexes.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        search_index = ('function (doc) {\n  index("default", doc._id); '
                        'if (doc._id) {index("name", doc.name, '
                        '{"store": true}); }\n}')
        ddoc.add_search_index('search001', search_index)
        ddoc.save()
        self.assertTrue(ddoc['_rev'].startswith('1-'))

    def test_save_with_no_search_indexes(self):
        """
        Tests the functionality when saving a design document without a search
        index. Both the locally cached and remote DesignDocument should not
        include the empty indexes sub-document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.save()
        # Ensure that locally cached DesignDocument contains an
        # empty search indexes and views dict.
        self.assertEqual(set(ddoc.keys()), {'_id', '_rev', 'indexes', 'views', 'lists'})
        self.assertEqual(ddoc['_id'], '_design/ddoc001')
        self.assertTrue(ddoc['_rev'].startswith('1-'))
        # Ensure that remotely saved design document does not
        # include a search indexes sub-document.
        resp = self.client.r_session.get(ddoc.document_url)
        raw_ddoc = resp.json()
        self.assertEqual(set(raw_ddoc.keys()), {'_id', '_rev'})
        self.assertEqual(raw_ddoc['_id'], ddoc['_id'])
        self.assertEqual(raw_ddoc['_rev'], ddoc['_rev'])

    def test_iterating_over_search_indexes(self):
        """
        Test iterating over search indexes within the DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        search_index = ('function (doc) {\n  index("default", doc._id); '
                        'if (doc._id) {index("name", doc.name, '
                        '{"store": true}); }\n}')
        ddoc.add_search_index('search001', search_index)
        ddoc.add_search_index('search002', search_index)
        ddoc.add_search_index('search003', search_index)
        search_index_names = []
        for search_index_name, search_index in ddoc.iterindexes():
            search_index_names.append(search_index_name)
        self.assertTrue(
            all(x in search_index_names for
                x in ['search001', 'search002', 'search003'])
        )

    def test_list_search_indexes(self):
        """
        Test the retrieval of search index name list from DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        index = 'function (doc) {\n  index("default", doc._id); '
        'if (doc._id) {index("name", doc.name, '
        '{"store": true}); }\n}'
        ddoc.add_search_index('search001', index)
        ddoc.add_search_index('search002', index)
        ddoc.add_search_index('search003', index)
        self.assertTrue(
            all(x in ddoc.list_indexes() for x in [
                'search001',
                'search002',
                'search003'
            ])
        )

    def test_get_search_index(self):
        """
        Test retrieval of a search index from the DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        index = ('function (doc) {\n  index("default", doc._id); '
                 'if (doc._id) {index("name", doc.name, '
                 '{"store": true}); }\n}')
        ddoc.add_search_index('search001', index)
        ddoc.add_search_index('search002', index)
        ddoc.add_search_index('search003', index)
        self.assertEqual(
            ddoc.get_index('search002'),
            {'index': 'function (doc) {\n  index("default", doc._id); '
                'if (doc._id) {index("name", doc.name, '
                '{"store": true}); }\n}'}
        )

    def test_rewrite_rule(self):
        """
        Test that design document URL is rewritten to the expected test document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc['rewrites'] = [
            {"from": "",
             "to": "/../../rewrite_doc",
             "method": "GET",
             "query": {}
             }
        ]
        self.assertIsInstance(ddoc.rewrites, list)
        self.assertIsInstance(ddoc.rewrites[0], dict)
        ddoc.save()
        doc = Document(self.db, 'rewrite_doc')
        doc.save()
        resp = self.client.r_session.get('/'.join([ddoc.document_url, '_rewrite']))
        self.assertEquals(
            resp.json(),
            {
                '_id': 'rewrite_doc',
                '_rev': doc['_rev']
            }
        )

    def test_add_a_list_function(self):
        """
        Test that adding a list function adds a list object to
        the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        self.assertEqual(ddoc.get('lists'), {})
        ddoc.add_list_function(
            'list001',
            'function(head, req) { provides(\'html\', function() '
            '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
            '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
            'html += \'</ol></body></html>\'; return html; }); }'
        )
        self.assertListEqual(list(ddoc.get('lists').keys()), ['list001'])
        self.assertEqual(
            ddoc.get('lists'),
            {'list001': 'function(head, req) { provides(\'html\', function() '
             '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
             '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
             'html += \'</ol></body></html>\'; return html; }); }'}
         )

    def test_adding_existing_list_function(self):
        """
        Test that adding an existing list function fails as expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_list_function(
            'list001',
            'function(head, req) { provides(\'html\', function() '
            '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
            '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
            'html += \'</ol></body></html>\'; return html; }); }'
        )
        with self.assertRaises(CloudantArgumentError) as cm:
            ddoc.add_list_function(
                'list001',
                'function (doc) { existing list }'
            )
        err = cm.exception
        self.assertEqual(
            str(err),
            'A list with name list001 already exists in this design doc'
        )

    def test_update_a_list_function(self):
        """
        Test that updating a list function updates the contents of the correct
        list object in the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_list_function('list001', 'not-a-valid-list-function')
        self.assertEqual(
            ddoc.get('lists')['list001'],
            'not-a-valid-list-function'
        )
        ddoc.update_list_function(
            'list001',
            'function(head, req) { provides(\'html\', function() '
            '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
            '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
            'html += \'</ol></body></html>\'; return html; }); }'
        )
        self.assertEqual(
            ddoc.get('lists')['list001'],
            'function(head, req) { provides(\'html\', function() '
            '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
            '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
            'html += \'</ol></body></html>\'; return html; }); }'
        )

    def test_update_non_existing_list_function(self):
        """
        Test that updating a non-existing list function fails as expected.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        with self.assertRaises(CloudantArgumentError) as cm:
            ddoc.update_list_function(
                'list001',
                'function(head, req) { provides(\'html\', function() '
                '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
                '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
                'html += \'</ol></body></html>\'; return html; }); }'
            )
        err = cm.exception
        self.assertEqual(
            str(err),
            'A list with name list001 does not exist in this design doc'
        )

    def test_delete_a_list_function(self):
        """
        Test deleting a list function from the DesignDocument dictionary.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.add_list_function(
            'list001',
            'function(head, req) { provides(\'html\', function() '
            '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
            '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
            'html += \'</ol></body></html>\'; return html; }); }'
        )
        self.assertEqual(
            ddoc.get('lists')['list001'],
            'function(head, req) { provides(\'html\', function() '
            '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
            '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
            'html += \'</ol></body></html>\'; return html; }); }'
        )
        ddoc.delete_list_function('list001')
        self.assertEqual(ddoc.get('lists'), {})

    def test_fetch_list_functions(self):
        """
        Ensure that the document fetch from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing list functions.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        list_func = ('function(head, req) { provides(\'html\', function() '
                     '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
                     '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
                     'html += \'</ol></body></html>\'; return html; }); }')
        ddoc.add_list_function('list001', list_func)
        ddoc.add_list_function('list002', list_func)
        ddoc.add_list_function('list003', list_func)
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        self.assertNotEqual(ddoc_remote, ddoc)
        ddoc_remote.fetch()
        self.assertEqual(ddoc_remote, ddoc)
        self.assertTrue(ddoc_remote['_rev'].startswith('1-'))
        self.assertEqual(ddoc_remote, {
            '_id': '_design/ddoc001',
            '_rev': ddoc['_rev'],
            'lists': {
                'list001': list_func,
                'list002': list_func,
                'list003': list_func
            },
            'indexes': {},
            'views': {}
        })

    def test_fetch_no_list_functions(self):
        """
        Ensure that the document fetched from the database returns the
        DesignDocument format as expected when retrieving a design document
        containing no list functions.
        The :func:`~cloudant.design_document.DesignDocument.fetch` function
        adds the ``lists`` key in the locally cached DesignDocument if
        list functions do not exist in the remote design document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        ddoc_remote.fetch()
        self.assertEqual(set(ddoc_remote.keys()),
                         {'_id', '_rev', 'indexes', 'views', 'lists'})
        self.assertEqual(ddoc_remote['_id'], '_design/ddoc001')
        self.assertTrue(ddoc_remote['_rev'].startswith('1-'))
        self.assertEqual(ddoc_remote['_rev'], ddoc['_rev'])
        self.assertEqual(ddoc_remote.lists, {})

    def test_save_with_no_list_functions(self):
        """
        Tests the functionality when saving a design document without list functions.
        Both the locally cached and remote DesignDocument should not
        include the empty lists sub-document.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc.save()
        # Ensure that locally cached DesignDocument contains lists dict
        self.assertEqual(set(ddoc.keys()), {'_id', '_rev', 'lists', 'indexes', 'views'})
        self.assertEqual(ddoc['_id'], '_design/ddoc001')
        self.assertTrue(ddoc['_rev'].startswith('1-'))
        # Ensure that remotely saved design document does not
        # include a lists sub-document.
        resp = self.client.r_session.get(ddoc.document_url)
        raw_ddoc = resp.json()
        self.assertEqual(set(raw_ddoc.keys()), {'_id', '_rev'})
        self.assertEqual(raw_ddoc['_id'], ddoc['_id'])
        self.assertEqual(raw_ddoc['_rev'], ddoc['_rev'])

    def test_iterating_over_list_functions(self):
        """
        Test iterating over list functions within the DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        list_func = ('function(head, req) { provides(\'html\', function() '
                     '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
                     '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
                     'html += \'</ol></body></html>\'; return html; }); }')
        ddoc.add_list_function('list001', list_func)
        ddoc.add_list_function('list002', list_func)
        ddoc.add_list_function('list003', list_func)
        list_names = []
        for list_name, list_func in ddoc.iterlists():
            list_names.append(list_name)
        self.assertTrue(
            all(x in list_names for
                x in ['list001', 'list002', 'list003'])
        )

    def test_listing_list_functions(self):
        """
        Test retrieving a list of list function names from DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        list_func = ('function(head, req) { provides(\'html\', function() '
                     '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
                     '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
                     'html += \'</ol></body></html>\'; return html; }); }')
        ddoc.add_list_function('list001', list_func)
        ddoc.add_list_function('list002', list_func)
        ddoc.add_list_function('list003', list_func)
        self.assertTrue(
            all(x in ddoc.list_list_functions() for x in [
                'list001',
                'list002',
                'list003'
            ])
        )

    def test_get_list_function(self):
        """
        Test retrieval of a list function from the DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        list_func = ('function(head, req) { provides(\'html\', function() '
                     '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
                     '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
                     'html += \'</ol></body></html>\'; return html; }); }')
        ddoc.add_list_function('list001', list_func)
        ddoc.add_list_function('list002', list_func)
        ddoc.add_list_function('list003', list_func)
        self.assertEqual(
            ddoc.get_list_function('list002'),
            'function(head, req) { provides(\'html\', function() '
            '{var html = \'<html><body><ol>\\n\'; while (row = getRow()) '
            '{ html += \'<li>\' + row.key + \':\' + row.value + \'</li>\\n\';} '
            'html += \'</ol></body></html>\'; return html; }); }'
        )

    @unittest.skipUnless(
        os.environ.get('RUN_CLOUDANT_TESTS') is not None,
        'Skipping Cloudant specific Cloudant Geo tests'
    )
    def test_geospatial_index(self):
        """
        Test retrieval and query of Cloudant Geo indexes from the DesignDocument.
        """
        ddoc = DesignDocument(self.db, '_design/ddoc001')
        ddoc['st_indexes'] = {
                'geoidx': {
                    'index': 'function(doc) { '
                             'if (doc.geometry && doc.geometry.coordinates) { '
                             'st_index(doc.geometry);}} '
                }
        }
        ddoc.save()
        ddoc_remote = DesignDocument(self.db, '_design/ddoc001')
        self.assertNotEqual(ddoc_remote, ddoc)
        ddoc_remote.fetch()
        self.assertEqual(ddoc_remote, {
            '_id': '_design/ddoc001',
            '_rev': ddoc['_rev'],
            'st_indexes': ddoc['st_indexes'],
            'indexes': {},
            'views': {},
            'lists': {}
        })
        # Document with geospatial point
        geodoc = Document(self.db, 'doc001')
        geodoc['type'] = 'Feature'
        geodoc['geometry'] = {
          "type": "Point",
          "coordinates": [
            -71.1,
            42.3
          ]
        }
        geodoc.save()
        # Geospatial query for a well known point
        geo_result = self.client.r_session.get('/'.join([ddoc_remote.document_url,
                                            '_geo',
                                            'geoidx?g=point(-71.1%2042.3)'])).json()
        self.assertIsNotNone(geo_result['bookmark'])
        geo_result.pop('bookmark')
        self.assertEqual(geo_result,
                         {'rows': [
                             {'id': 'doc001',
                              'geometry':
                                  {'type': 'Point',
                                   'coordinates': [-71.1, 42.3]}}]
                         })

if __name__ == '__main__':
    unittest.main()
