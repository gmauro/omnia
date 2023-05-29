import unittest

import mongomock
from mongoengine import connect, disconnect, get_connection

from omnia.ids.models import GwasTrait, GwasTraitID


class TestGwasDataIDOffline(unittest.TestCase):
    def test_gwasDataID_id(self):
        """
        If gwas_did_obj is not mapped, then gwas_did_obj.pk has to be None
        """
        gwas_did_obj = GwasTraitID(uk="gwas_1")
        assert gwas_did_obj.pk is None

    def test_gwasDataID_uk(self):
        good = ["gwas_1", "gwas_12345678"]
        for i in good:
            gwas_did_obj = GwasTraitID(uk=i)
            assert gwas_did_obj.uk == i

        bad = ["gwas_a1", "xwas_1", "gwas-1", "gwas:1", "gwa_1"]
        for i in bad:
            self.assertRaises(ValueError, GwasTraitID, uk=i)


class TestGwasDataID(unittest.TestCase):
    def setUp(self) -> None:
        self.uk = "gwas_1"
        self.mec = get_connection()
        self.gdid = GwasTraitID(mec=self.mec, uk=self.uk)

    def tearDown(self) -> None:
        GwasTrait.objects().first().delete()

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

    def test_is_connected(self):
        self.assertIsNotNone(self.mec)
        gdid = self.gdid
        self.assertTrue(gdid.is_connected)
        gdid.save()

    def test_ensure_is_mapped(self):
        gdid = self.gdid
        self.assertFalse(gdid.ensure_is_mapped())

        gdid.save()
        self.assertTrue(gdid.ensure_is_mapped())

    def test_is_mapped(self):
        gdid = self.gdid
        self.assertFalse(gdid.is_mapped)

        gdid.map()
        self.assertFalse(gdid.is_mapped)

        gdid.save()
        gdid.map()
        self.assertTrue(gdid.is_mapped)

    def test_map(self):
        gdid = self.gdid
        gdid.save()

        gdid.uk = "gwas_2"
        self.assertFalse(gdid.map())

        gdid.uk = "gwas_1"
        self.assertTrue(gdid.map())

    def test_save(self):
        uk = self.uk
        tags = ["tag1", "tag2"]
        description = "description text"
        url = "http://url.it"

        gdid = GwasTraitID(uk=uk, description=description, url=url, tags=tags, mec=self.mec)
        gdid.save()

        with self.mec:
            mdb_obj = GwasTrait.objects().first()
            assert mdb_obj.unique_key == uk
            self.assertIn(tags[0], mdb_obj.tags)
            self.assertIn(tags[1], mdb_obj.tags)
            assert mdb_obj.description == description
            self.assertIsNotNone(mdb_obj.creation_date)
            assert mdb_obj.url == url
            self.assertIsNotNone(mdb_obj.pk)

    def test_view(self):
        gdid = self.gdid
        self.assertFalse(gdid.view())
        gdid.save()
        self.assertIsNotNone(gdid.view())
        self.assertIs(type(gdid.view()), dict)
        assert len(gdid.view()) > 0

    def test_modify(self):
        uk = ["gwas_1", "gwas_2"]
        tags = [["tag1", "tag2"], ["tag3", "tag4"]]
        description = ["text1", "text2"]
        url = ["http://url.it", "http://url.com"]

        gdid = GwasTraitID(uk=uk[0], description=description[0], url=url[0], tags=tags[0], mec=self.mec)
        gdid.save()

        result = gdid.modify(unique_key=uk[1], description=description[1], url=url[1], tags=tags[1])

        self.assertTrue(result)

        with self.mec:
            mdb_obj = GwasTrait.objects().first()
            assert mdb_obj.unique_key == uk[1]
            self.assertIn(tags[1][0], mdb_obj.tags)
            self.assertIn(tags[1][1], mdb_obj.tags)
            assert mdb_obj.description == description[1]
            self.assertIsNotNone(mdb_obj.modification_date)
            assert mdb_obj.url == url[1]
            self.assertIsNotNone(mdb_obj.pk)

    def test_delete(self):
        gdid = self.gdid
        gdid.save()

        objects = GwasTrait.objects()
        assert len(objects) == 1

        gdid.delete()
        objects = GwasTrait.objects()
        assert len(objects) == 0

        # to avoid raising exception in TearDown
        gdid = self.gdid
        gdid.save()
