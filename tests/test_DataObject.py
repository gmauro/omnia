import unittest
import uuid

from mongoengine import connect, disconnect, get_connection
from omnia.config_manager import ConfigurationManager
from omnia.dv.models import PosixDataObject, DataObject


class TestDataObject(unittest.TestCase):
    def setUp(self) -> None:
        cm = ConfigurationManager()
        self.mec = get_connection(alias=cm.get_mdbc_alias)
        self.host = str(uuid.uuid4())
        self.path = "/".join(str(uuid.uuid4()).split("-"))

    def tearDown(self) -> None:
        DataObject.objects().first().delete()

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

    def test_posixDataObject_save(self):
        prefix = "posix"
        posix_dobj = PosixDataObject(
            mec=self.mec, host=self.host, path=self.path
        )
        posix_dobj.save()

        with self.mec:
            fresh_dobj = DataObject.objects().first()
            assert fresh_dobj.host == self.host
            assert fresh_dobj.path == self.path
            assert fresh_dobj.prefix == prefix

    def test_posixDataObject_unique_key(self):
        posix_dobj = PosixDataObject(
            mec=self.mec, host=self.host, path=self.path
        )
        posix_dobj.save()

        assert posix_dobj.unique_key == "{}:{}".format(self.host, self.path)

    def test_posixDataObject_is_mapped(self):
        posix_dobj = PosixDataObject(
            mec=self.mec, host=self.host, path=self.path
        )
        self.assertFalse(posix_dobj.is_mapped)

        posix_dobj.save()
        self.assertTrue(posix_dobj.is_mapped)
