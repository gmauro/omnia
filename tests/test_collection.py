import unittest

from mongoengine import connect, disconnect

from omnia.dv.models import DataCollection


class TestDataCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        connect(
            "mongoenginetest",
            host="mongomock://localhost",
            alias="omnia_dv_alias",
        )

    @classmethod
    def tearDownClass(cls):
        disconnect()

    def test_saveDataCollection(self):
        c = DataCollection(label="c1")
        c.save()

        fresh_collection = DataCollection.objects().first()
        assert fresh_collection.label == "c1"
