import unittest
import uuid

import mongomock
from mongoengine import connect, disconnect, get_connection

from omnia.dv.models import DataObject, PosixDataObject


class TestDataObject(unittest.TestCase):
    def setUp(self) -> None:
        self.mec = get_connection()
        self.host = str(uuid.uuid4())
        self.path = "/".join(str(uuid.uuid4()).split("-"))

    def tearDown(self) -> None:
        DataObject.objects().first().delete()

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

    def test_posixDataObject_save(self):
        prefix = "posix"
        tags = ["tag1", "tag2"]
        description = "description text"
        posix_dobj = PosixDataObject(
            description=description,
            mec=self.mec,
            host=self.host,
            path=self.path,
            tags=tags,
        )
        posix_dobj.save()

        with self.mec:
            fresh_dobj = DataObject.objects().first()
            assert fresh_dobj.host == self.host
            assert fresh_dobj.path == self.path
            assert fresh_dobj.prefix == prefix
            self.assertIn(tags[0], fresh_dobj.tags)
            self.assertIn(tags[0], fresh_dobj.tags)
            assert fresh_dobj.description == description
            self.assertIsNotNone(fresh_dobj.creation_date)

    def test_posixDataObject_compute(self):
        path = "tests/data/file.bin"
        checksum = (
            "875617088a4f08e5d836b8629f6bf16d9bc5bf4b1c43b8520af0bcb3d4814a62"
        )
        size = 1353
        mimetype = "application/octet-stream"
        posix_dobj = PosixDataObject(mec=self.mec, host=self.host, path=path)
        posix_dobj.compute()
        posix_dobj.save()

        with self.mec:
            fresh_dobj = DataObject.objects().first()
            assert fresh_dobj.checksum == checksum
            assert fresh_dobj.file_size == size
            assert fresh_dobj.mimetype == mimetype

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
