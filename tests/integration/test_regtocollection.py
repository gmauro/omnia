import unittest
import uuid

import mongomock
from mongoengine import connect, disconnect, get_connection

from omnia.dv.models import DataCollection, DataObject, PosixDataObject


class TestRegToCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        connect(
            "mongoenginetest",
            host="mongodb://localhost",
            mongo_client_class=mongomock.MongoClient,
        )

    @classmethod
    def tearDownClass(cls):
        disconnect()

    def setUp(self) -> None:
        self.mec = get_connection()
        self.host = str(uuid.uuid4())
        self.path = "/".join(str(uuid.uuid4()).split("-"))

    def tearDown(self) -> None:
        DataObject.objects().first().delete()
        DataCollection.objects().first().delete()

    def testRegDobjToCollection(self):
        collection_label = "c1"
        c = DataCollection(label=collection_label)
        c.save()

        posix_dobj = PosixDataObject(mec=self.mec, host=self.host, path=self.path)
        posix_dobj.collections = [collection_label]
        posix_dobj.save()

        with self.mec:
            fresh_dobj = DataObject.objects().first()
            self.assertIn(c, fresh_dobj.collections)
