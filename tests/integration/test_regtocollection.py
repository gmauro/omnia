import unittest
import uuid

from mongoengine import connect, disconnect, get_connection

from omnia.dv.models import DataCollection
from omnia.config_manager import ConfigurationManager
from omnia.dv.models import PosixDataObject, DataObject


class TestRegToCollection(unittest.TestCase):
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

    def setUp(self) -> None:
        cm = ConfigurationManager()
        self.mec = get_connection(alias=cm.get_mdbc_alias)
        self.host = str(uuid.uuid4())
        self.path = "/".join(str(uuid.uuid4()).split("-"))

    def tearDown(self) -> None:
        DataObject.objects().first().delete()
        DataCollection.objects().first().delete()

    def testRegDobjToCollection(self):
        collection_label = "c1"
        c = DataCollection(label=collection_label)
        c.save()

        posix_dobj = PosixDataObject(
            mec=self.mec, host=self.host, path=self.path
        )
        posix_dobj.collections = [collection_label]
        posix_dobj.save()

        with self.mec:
            fresh_dobj = DataObject.objects().first()
            self.assertIn(c, fresh_dobj.collections)
