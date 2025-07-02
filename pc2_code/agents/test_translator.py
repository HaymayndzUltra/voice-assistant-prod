import unittest
import time
import json
import zmq
import threading
from main_pc_code.FORMAINPC.consolidated_translator import TranslatorServer, TranslationPipeline, SessionManager, TranslationCache
from pc2_code.config.system_config import get_config_for_service, config

class TestConsolidatedTranslator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment before running tests."""
        # Load test configuration
        cls.config = {
            'zmq_port': config['zmq.translator_port'],
            'zmq_bind_address': config['network.bind_address'],
            'log_level': config['system.log_level'],
            'logs_dir': config['system.logs_dir'],
            'cache_dir': config['system.cache_dir'],
            'cache': {
                'max_size': 1000,
                'ttl': 3600,
                'cleanup_interval': 300
            },
            'session': {
                'max_history': 100,
                'timeout': 3600,
                'cleanup_interval': 300
            },
            'engines': {
                'nllb': {
                    'enabled': True,
                    'port': 5581,
                    'host': 'localhost',
                    'timeout': 30
                },
                'phi': {
                    'enabled': True,
                    'port': 11434,
                    'host': 'localhost',
                    'timeout': 30
                },
                'google': {
                    'enabled': True,
                    'api_key': 'test_key',
                    'timeout': 30
                },
                'dictionary': {
                    'enabled': True,
                    'path': 'data/dictionary.json',
                    'timeout': 5
                }
            },
            'translation_confidence': {
                'high_threshold_pattern': 0.98,
                'high_threshold_nllb': 0.85,
                'medium_threshold_nllb': 0.60,
                'low_threshold': 0.30,
                'default_google_confidence': 0.90
            }
        }
        
        # Initialize server
        cls.server = TranslatorServer(cls.config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        # Initialize ZMQ client
        cls.context = zmq.Context()
        cls.socket = cls.context.socket(zmq.REQ)
        cls.socket.connect(f"tcp://localhost:{cls.config['zmq_port']}")
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        cls.socket.close()
        cls.context.term()
        
    def test_01_health_check(self):
        """Test health check endpoint."""
        request = {
            'action': 'health_check'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertEqual(response['status'], 'healthy')
        self.assertIn('cache_stats', response)
        self.assertIn('engines', response)
        self.assertIn('uptime', response)
        
    def test_02_basic_translation(self):
        """Test basic translation functionality."""
        request = {
            'action': 'translate',
            'text': 'Hello, how are you?',
            'source_lang': 'en_Latn',
            'target_lang': 'tl_Latn',
            'session_id': 'test_session_1'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertIn('status', response)
        if response['status'] == 'success':
            self.assertIn('translated_text', response)
            self.assertIn('engine_used', response)
            self.assertIn('quality_score', response)
        else:
            self.assertIn('message', response)
        
    def test_03_auto_language_detection(self):
        """Test automatic language detection."""
        request = {
            'action': 'translate',
            'text': 'Kamusta ka?',
            'target_lang': 'en_Latn',
            'session_id': 'test_session_2'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertIn('status', response)
        if response['status'] == 'success':
            self.assertEqual(response['source_lang'], 'tl_Latn')
        else:
            self.assertIn('message', response)
        
    def test_04_session_management(self):
        """Test session management functionality."""
        session_id = 'test_session_3'
        
        # Add multiple translations to session
        texts = [
            'Good morning',
            'How are you today?',
            'Thank you very much'
        ]
        
        for text in texts:
            request = {
                'action': 'translate',
                'text': text,
                'source_lang': 'en_Latn',
                'target_lang': 'tl_Latn',
                'session_id': session_id
            }
            self.socket.send_json(request)
            response = self.socket.recv_json()
            self.assertIn('status', response)
            
        # Get session history
        request = {
            'action': 'get_session',
            'session_id': session_id
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertIn('status', response)
        if response['status'] == 'success':
            self.assertIn('session', response)
            self.assertIn('stats', response['session'])
        
    def test_05_cache_functionality(self):
        """Test translation caching."""
        text = 'This is a test for caching'
        session_id = 'test_session_4'
        
        # First translation
        request = {
            'action': 'translate',
            'text': text,
            'source_lang': 'en_Latn',
            'target_lang': 'tl_Latn',
            'session_id': session_id
        }
        self.socket.send_json(request)
        first_response = self.socket.recv_json()
        
        # Second translation (should be cached)
        self.socket.send_json(request)
        second_response = self.socket.recv_json()
        
        if first_response['status'] == 'success' and second_response['status'] == 'success':
            self.assertEqual(first_response['translated_text'], second_response['translated_text'])
            self.assertTrue(second_response['cache_hit'])
        
    def test_06_error_handling(self):
        """Test error handling."""
        # Test invalid language
        request = {
            'action': 'translate',
            'text': 'Hello',
            'source_lang': 'invalid',
            'target_lang': 'tl_Latn',
            'session_id': 'test_session_5'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertEqual(response['status'], 'error')
        self.assertIn('message', response)
        
    def test_07_monitoring_stats(self):
        """Test monitoring statistics."""
        request = {
            'action': 'get_stats'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertIn('status', response)
        if response['status'] == 'success':
            self.assertIn('stats', response)
            stats = response['stats']
            self.assertIn('performance', stats)
            self.assertIn('engine_usage', stats)
            self.assertIn('resource_usage', stats)
        
    def test_08_capabilities(self):
        """Test capabilities endpoint."""
        request = {
            'action': 'get_capabilities'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertIn('status', response)
        if response['status'] == 'success':
            self.assertIn('capabilities', response)
            capabilities = response['capabilities']
            self.assertIn('languages', capabilities)
            self.assertIn('engines', capabilities)
            self.assertIn('features', capabilities)
        
    def test_09_quality_metrics(self):
        """Test translation quality metrics."""
        request = {
            'action': 'translate',
            'text': 'This is a test for quality metrics',
            'source_lang': 'en_Latn',
            'target_lang': 'tl_Latn',
            'session_id': 'test_session_6'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertIn('status', response)
        if response['status'] == 'success':
            self.assertIn('quality_score', response)
            self.assertGreaterEqual(response['quality_score'], 0.0)
            self.assertLessEqual(response['quality_score'], 1.0)
        
    def test_10_concurrent_requests(self):
        """Test handling of concurrent requests."""
        def make_request(text, session_id):
            request = {
                'action': 'translate',
                'text': text,
                'source_lang': 'en_Latn',
                'target_lang': 'tl_Latn',
                'session_id': session_id
            }
            socket = self.context.socket(zmq.REQ)
            socket.connect(f"tcp://localhost:{self.config['zmq_port']}")
            socket.send_json(request)
            response = socket.recv_json()
            socket.close()
            return response
            
        # Create multiple threads for concurrent requests
        threads = []
        texts = [
            'First concurrent request',
            'Second concurrent request',
            'Third concurrent request'
        ]
        
        for i, text in enumerate(texts):
            thread = threading.Thread(
                target=make_request,
                args=(text, f'test_session_7_{i}')
            )
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Verify server is still responsive
        request = {
            'action': 'health_check'
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        self.assertEqual(response['status'], 'healthy')

def run_tests():
    """Run all tests and print results."""
    print("Starting Consolidated Translator Tests...")
    print("-" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConsolidatedTranslator)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\nTest Summary:")
    print("-" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.2f}%")
    
    return len(result.failures) + len(result.errors) == 0

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1) 