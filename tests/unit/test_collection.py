import unittest

import mongomock
from mongoengine import connect, disconnect

from omnia.dv.models import DataCollection


class TestDataCollection(unittest.TestCase):
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

    def tearDown(self) -> None:
        DataCollection.objects().first().delete()

    def test_saveDataCollection(self):
        c = DataCollection(label="c1")
        c.save()

        fresh_collection = DataCollection.objects().first()
        assert fresh_collection.label == "c1"
