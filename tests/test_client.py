import unittest
from unittest.mock import patch, MagicMock
from requests.structures import CaseInsensitiveDict
from deepdub import DeepdubClient


class TestDeepdubClient(unittest.TestCase):
    @patch('deepdub.client.requests.Session')
    def test_init(self, mock_session):
        # Test initialization with API key
        client = DeepdubClient(api_key="test_key")
        self.assertEqual(client.api_key, "test_key")
        
    @patch('deepdub.client.requests.Session')
    @patch('os.environ', {"DEEPDUB_API_KEY": "env_test_key"})
    def test_init_with_env(self, mock_session):
        # Test initialization with environment variable
        client = DeepdubClient()
        self.assertEqual(client.api_key, "env_test_key")
        
    @patch('deepdub.client.requests.get')
    def test_list_voices(self, mock_get):
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {"voices": [{"id": "1", "name": "Test Voice"}]}
        
        # Create a proper CaseInsensitiveDict for headers
        headers = CaseInsensitiveDict()
        headers['content-type'] = 'application/json'
        mock_response.headers = headers
        
        mock_get.return_value = mock_response
        
        # Test list_voices method
        client = DeepdubClient(api_key="test_key")
        result = client.list_voices()
        
        # Assertions
        self.assertEqual(result, {"voices": [{"id": "1", "name": "Test Voice"}]})
        mock_get.assert_called_once()


if __name__ == '__main__':
    unittest.main() 