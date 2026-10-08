import unittest
from unittest.mock import patch

from omnia.mongo.connection_manager import MongoEngineConnectionManager, get_mec, get_mec_from_config


class TestMongoEngineConnectionManager(unittest.TestCase):
    @patch("omnia.mongo.connection_manager.connect")
    @patch("omnia.mongo.connection_manager.disconnect")
    def test_connection_manager_context(self, mock_disconnect, mock_connect):
        # Test with a custom URI
        test_uri = "mongodb://test:test@localhost:27017/testdb"
        with MongoEngineConnectionManager(uri=test_uri) as manager:
            self.assertEqual(manager.uri, test_uri)
            mock_connect.assert_called_once_with(host=test_uri)

        mock_disconnect.assert_called_once()

        # Reset mocks
        mock_connect.reset_mock()
        mock_disconnect.reset_mock()

        # Test with the URI supplied by configuration. Keep this mocked: the
        # real configuration may be user- or deployment-specific.
        configured_uri = "mongodb://localhost:27018/omnia_dev?connectTimeoutMS=2000"
        with patch.object(MongoEngineConnectionManager, "_get_uri_from_config", return_value=configured_uri):
            with MongoEngineConnectionManager() as manager:
                self.assertEqual(manager.uri, configured_uri)
                mock_connect.assert_called_once_with(host=configured_uri)

        mock_disconnect.assert_called_once()

    @patch("omnia.mongo.connection_manager.MongoEngineConnectionManager._get_uri_from_config")
    def test_get_uri_from_config(self, mock_get_uri):
        # Test when config import succeeds
        mock_get_uri.return_value = "mongodb://config:uri@localhost:27017/configdb"
        manager = MongoEngineConnectionManager()
        self.assertEqual(manager.uri, "mongodb://config:uri@localhost:27017/configdb")

        # Test when config import fails
        mock_get_uri.return_value = ""
        manager = MongoEngineConnectionManager()
        self.assertEqual(manager.uri, "")

    def test_get_mec(self):
        # Test with custom URI
        test_uri = "mongodb://test:test@localhost:27017/testdb"
        manager = get_mec(uri=test_uri)
        self.assertIsInstance(manager, MongoEngineConnectionManager)
        self.assertEqual(manager.uri, test_uri)

        # Test with the URI supplied by configuration.
        configured_uri = "mongodb://localhost:27018/omnia_dev?connectTimeoutMS=2000"
        with patch.object(MongoEngineConnectionManager, "_get_uri_from_config", return_value=configured_uri):
            manager = get_mec()
            self.assertIsInstance(manager, MongoEngineConnectionManager)
            self.assertEqual(manager.uri, configured_uri)

    @patch("omnia.mongo.connection_manager.MongoEngineConnectionManager._get_uri_from_config")
    def test_get_mec_from_config(self, mock_get_uri):
        # Test with config URI
        mock_get_uri.return_value = "mongodb://config:uri@localhost:27017/configdb"
        manager = get_mec_from_config()
        self.assertIsInstance(manager, MongoEngineConnectionManager)
        self.assertEqual(manager.uri, "mongodb://config:uri@localhost:27017/configdb")

        # Test with default URI
        mock_get_uri.return_value = ""
        manager = get_mec_from_config()
        self.assertIsInstance(manager, MongoEngineConnectionManager)
        self.assertEqual(manager.uri, "")
