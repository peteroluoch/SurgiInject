"""
Comprehensive test cases for the MistralClient class
Tests API fallback logic, mock response strategy, and key usage
"""

import unittest
import os
from unittest.mock import patch, Mock, MagicMock
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.mistral_client import MistralClient, run_model


class TestMistralClient(unittest.TestCase):
    """Comprehensive test cases for MistralClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_prompt = """
        SOURCE CODE:
        def test_function():
            pass
        
        INSTRUCTION:
        Add error handling to this function.
        """
        
    def test_init_with_groq_key_only(self):
        """Test initialization with only Groq API key"""
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test_groq_key'}, clear=True):
            client = MistralClient()
            self.assertEqual(client.groq_api_key, 'test_groq_key')
            self.assertIsNone(client.api_key)
            self.assertFalse(client.mock_mode)
            self.assertEqual(client.active_provider, 'groq')
    
    def test_init_with_mistral_key_only(self):
        """Test initialization with only Mistral API key"""
        with patch.dict(os.environ, {'MISTRAL_API_KEY': 'test_mistral_key'}, clear=True):
            client = MistralClient()
            self.assertIsNone(client.groq_api_key)
            self.assertEqual(client.api_key, 'test_mistral_key')
            self.assertFalse(client.mock_mode)
            self.assertEqual(client.active_provider, 'mistral')
    
    def test_init_with_both_keys(self):
        """Test initialization with both API keys"""
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test_groq_key',
            'MISTRAL_API_KEY': 'test_mistral_key'
        }, clear=True):
            client = MistralClient()
            self.assertEqual(client.groq_api_key, 'test_groq_key')
            self.assertEqual(client.api_key, 'test_mistral_key')
            self.assertFalse(client.mock_mode)
    
    def test_init_with_no_keys(self):
        """Test initialization with no API keys (mock mode)"""
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient()
            self.assertIsNone(client.groq_api_key)
            self.assertIsNone(client.api_key)
            self.assertTrue(client.mock_mode)
            self.assertEqual(client.active_provider, 'mock')
    
    @patch('models.mistral_client.requests.post')
    def test_groq_api_success(self, mock_post):
        """Test successful Groq API call"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Enhanced code with error handling'}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test_groq_key'}, clear=True):
            client = MistralClient()
            result = client.generate_response(self.test_prompt)
            
            self.assertEqual(result, 'Enhanced code with error handling')
            mock_post.assert_called_once()
            
            # Verify the API call parameters
            call_args = mock_post.call_args
            self.assertEqual(call_args[1]['timeout'], 10)
            self.assertIn('Authorization', call_args[1]['headers'])
            self.assertEqual(call_args[1]['headers']['Authorization'], 'Bearer test_groq_key')
    
    @patch('models.mistral_client.requests.post')
    def test_groq_api_retry_logic(self, mock_post):
        """Test Groq API retry logic on failure"""
        # Mock failed responses for first 2 attempts, success on 3rd
        mock_post.side_effect = [
            Exception("Network error"),
            Exception("Timeout error"),
            Mock(json=lambda: {'choices': [{'message': {'content': 'Success after retry'}}]})
        ]
        mock_post.return_value.raise_for_status.return_value = None
        
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test_groq_key'}, clear=True):
            client = MistralClient()
            
            # Should fall back to mock after retries fail
            with patch.object(client, '_mock_response', return_value='Mock response') as mock_mock:
                result = client.generate_response(self.test_prompt)
                self.assertEqual(result, 'Mock response')
                mock_mock.assert_called_once()
    
    @patch('models.mistral_client.requests.post')
    def test_mistral_api_fallback(self, mock_post):
        """Test fallback to Mistral API when Groq fails"""
        # Mock Groq failure, Mistral success
        mock_post.side_effect = [
            Exception("Groq API error"),  # Groq fails
            Mock(json=lambda: {'choices': [{'message': {'content': 'Mistral API response'}}]})  # Mistral succeeds
        ]
        mock_post.return_value.raise_for_status.return_value = None
        
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test_groq_key',
            'MISTRAL_API_KEY': 'test_mistral_key'
        }, clear=True):
            client = MistralClient()
            result = client.generate_response(self.test_prompt)
            
            self.assertEqual(result, 'Mistral API response')
            # Should have called both APIs
            self.assertEqual(mock_post.call_count, 2)
    
    def test_mock_response_strategy_bug_fix(self):
        """Test mock response strategy for bug fixes"""
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient()
            
            bug_prompt = "Fix the bug in this function"
            result = client.generate_response(bug_prompt)
            
            self.assertIn('[SURGIINJECT]', result)
            self.assertIn('bug fix', result.lower())
    
    def test_mock_response_strategy_test_enhancement(self):
        """Test mock response strategy for test enhancements"""
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient()
            
            test_prompt = "Add test coverage to this code"
            result = client.generate_response(test_prompt)
            
            self.assertIn('[SURGIINJECT]', result)
            self.assertIn('test', result.lower())
    
    def test_mock_response_strategy_performance(self):
        """Test mock response strategy for performance optimization"""
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient()
            
            perf_prompt = "Optimize this code for better performance"
            result = client.generate_response(perf_prompt)
            
            self.assertIn('[SURGIINJECT]', result)
            self.assertIn('performance', result.lower())
    
    def test_mock_response_escalation(self):
        """Test mock response escalation logic"""
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient()
            
            escalation_prompt = "ESCALATION REQUEST: Previous response was weak"
            result = client.generate_response(escalation_prompt)
            
            self.assertIn('ESCALATED RESPONSE', result)
            self.assertIn('High Quality Enhancement', result)
    
    def test_run_model_convenience_function(self):
        """Test the run_model convenience function"""
        with patch.dict(os.environ, {}, clear=True):
            result = run_model(self.test_prompt)

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
            self.assertIn('[SURGIINJECT]', result)

    def test_provider_selection_groq_priority(self):
        """Test that Groq is selected when both keys are present"""
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test_groq_key',
            'MISTRAL_API_KEY': 'test_mistral_key'
        }, clear=True):
            client = MistralClient()
            self.assertEqual(client.active_provider, 'groq')
            self.assertFalse(client.mock_mode)

    def test_mock_strategy_dispatch_map(self):
        """Test that mock strategies use dispatch map correctly"""
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient()

            # Test that dispatch map is initialized
            self.assertIsInstance(client.mock_strategies, dict)
            self.assertIn('bug', client.mock_strategies)
            self.assertIn('test', client.mock_strategies)
            self.assertIn('security', client.mock_strategies)

            # Test strategy selection
            bug_result = client.generate_response("Fix bug in this code")
            self.assertIn('bug', bug_result.lower())

            security_result = client.generate_response("Add security to this code")
            self.assertIn('security', security_result.lower())

    def test_weak_response_escalation_detection(self):
        """Test that weak responses trigger escalation warnings"""
        with patch.dict(os.environ, {}, clear=True):
            client = MistralClient()

            # Test with minimal code that might trigger weak response detection
            weak_prompt = "def test(): pass"
            with patch('models.mistral_client.logger') as mock_logger:
                result = client.generate_response(weak_prompt)

                # Check if warning about weak response was logged
                warning_calls = [call for call in mock_logger.warning.call_args_list
                               if 'weak' in str(call).lower()]
                self.assertTrue(len(warning_calls) > 0 or 'SURGIINJECT' in result)

    @patch('models.mistral_client.requests.post')
    def test_api_failure_fallback_chain(self, mock_post):
        """Test complete fallback chain: Groq fails -> Mistral fails -> Mock"""
        # Mock both APIs to fail
        mock_post.side_effect = Exception("API failure")

        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test_groq_key',
            'MISTRAL_API_KEY': 'test_mistral_key'
        }, clear=True):
            client = MistralClient()

            # Should fallback to mock after both APIs fail
            result = client.generate_response(self.test_prompt)

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
            self.assertIn('[SURGIINJECT]', result)

            # Should have attempted both APIs
            self.assertEqual(mock_post.call_count, 6)  # 3 attempts each (2 retries + 1 initial)

    def test_active_provider_logging(self):
        """Test that active provider is logged correctly"""
        test_cases = [
            ({'GROQ_API_KEY': 'test_groq'}, 'groq'),
            ({'MISTRAL_API_KEY': 'test_mistral'}, 'mistral'),
            ({}, 'mock')
        ]

        for env_vars, expected_provider in test_cases:
            with patch.dict(os.environ, env_vars, clear=True):
                with patch('models.mistral_client.logger') as mock_logger:
                    client = MistralClient()
                    self.assertEqual(client.active_provider, expected_provider)

                    # Check that provider selection was logged
                    info_calls = [str(call) for call in mock_logger.info.call_args_list]
                    provider_logged = any(expected_provider in call.lower() for call in info_calls)
                    self.assertTrue(provider_logged, f"Provider {expected_provider} not logged")


if __name__ == '__main__':
    unittest.main()
