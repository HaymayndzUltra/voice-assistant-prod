import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import unittest
import zmq
import time
from main_pc_code.FORMAINPC.consolidated_translator import TranslationPipeline

class TestConsolidatedTranslator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Test configuration
        cls.config = {
            'cache': {
                'max_size': 1000,
                'ttl': 3600
            },
            'session': {
                'max_history': 10,
                'timeout': 300
            },
            'engines': {
                'nllb': {
                    'enabled': True,
                    'timeout': 5,
                    'port': 5581
                },
                'phi': {
                    'enabled': True,
                    'timeout': 3,
                    'port': 11434,
                    'host': 'localhost',
                    'model': 'phi3'
                },
                'google': {
                    'enabled': True,
                    'timeout': 2,
                    'port': 5557
                },
                'dictionary': {
                    'enabled': True
                }
            }
        }
        
        # Initialize ZMQ context
        cls.context = zmq.Context()
        
        # Initialize pipeline
        cls.pipeline = TranslationPipeline(cls.config)
        
    @classmethod
    def tearDownClass(cls):
        """Clean up resources"""
        if hasattr(cls, 'pipeline'):
            # Close all ZMQ sockets in the pipeline
            if hasattr(cls.pipeline, 'nllb_client'):
                cls.pipeline.nllb_client.close()
            if hasattr(cls.pipeline, 'phi_client'):
                cls.pipeline.phi_client.close()
            if hasattr(cls.pipeline, 'google_client'):
                cls.pipeline.google_client.close()
        
        # Terminate ZMQ context
        if hasattr(cls, 'context'):
            cls.context.term()
        
    def test_cache_operations(self):
        """Test translation cache functionality"""
        # Test cache hit
        text = "hello world"
        source_lang = "eng_Latn"
        target_lang = "tgl_Latn"
        
        # First translation (cache miss)
        result1 = self.pipeline.translate(text, source_lang, target_lang)
        self.assertEqual(result1['cache_hit'], False)
        
        # Second translation (cache hit)
        result2 = self.pipeline.translate(text, source_lang, target_lang)
        self.assertEqual(result2['cache_hit'], True)
        self.assertEqual(result1['translated_text'], result2['translated_text'])
        
    def test_session_management(self):
        """Test session history tracking"""
        session_id = "test_session_123"
        text = "how are you"
        source_lang = "eng_Latn"
        target_lang = "tgl_Latn"
        
        # First translation
        result1 = self.pipeline.translate(text, source_lang, target_lang, session_id)
        self.assertIsNotNone(result1['session_id'])
        
        # Get session history
        history = self.pipeline.session_manager.get_history(session_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['text'], text)
        
    def test_dictionary_translation(self):
        """Test dictionary/pattern matching translations"""
        # Test complete sentence
        text = "hello"
        result = self.pipeline.translate(text, "eng_Latn", "tgl_Latn")
        self.assertEqual(result['engine_used'], 'dictionary')
        self.assertEqual(result['translated_text'], 'kamusta')
        
    def test_engine_fallbacks(self):
        """Test translation engine fallback behavior"""
        text = "The quick brown fox jumps over the lazy dog"
        result = self.pipeline.translate(text, "eng_Latn", "tgl_Latn")
        self.assertIn(result['engine_used'], ['nllb', 'phi', 'google'])
        
    def test_health_check(self):
        """Test health check functionality"""
        health = self.pipeline.health_check()
        self.assertIn('status', health)
        self.assertIn('engines', health)
        
    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test empty text
        result = self.pipeline.translate("", "eng_Latn", "tgl_Latn")
        self.assertEqual(result['status'], 'error')
        
        # Test invalid language codes
        result = self.pipeline.translate("hello", "invalid", "tgl_Latn")
        self.assertEqual(result['status'], 'error')
        
    def test_concurrent_requests(self):
        """Test handling of concurrent translation requests"""
        text = "hello world"
        source_lang = "eng_Latn"
        target_lang = "tgl_Latn"
        
        # Make multiple concurrent requests
        results = []
        for _ in range(5):
            result = self.pipeline.translate(text, source_lang, target_lang)
            results.append(result)
            
        # Verify all requests completed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result['status'], 'success')
            
    def test_cache_eviction(self):
        """Test cache eviction when max size is reached"""
        # Fill cache with unique translations
        for i in range(1001):  # One more than max_size
            text = f"test text {i}"
            self.pipeline.translate(text, "eng_Latn", "tgl_Latn")
            
        # Verify cache size is maintained
        cache_stats = self.pipeline.cache.get_stats()
        self.assertLessEqual(cache_stats['size'], 1000)
        
    def test_session_timeout(self):
        """Test session timeout behavior"""
        session_id = "test_session_timeout"
        text = "hello world"
        
        # Add translation to session
        self.pipeline.translate(text, "eng_Latn", "tgl_Latn", session_id)
        
        # Simulate timeout
        self.pipeline.session_manager.sessions[session_id]['last_activity'] = time.time() - 400  # 400 seconds ago
        
        # Clean up expired sessions
        self.pipeline.session_manager._cleanup_expired_sessions()
        
        # Verify session was removed
        self.assertNotIn(session_id, self.pipeline.session_manager.sessions)
        
    def test_language_validation(self):
        """Test language code validation"""
        # Test invalid source language
        result = self.pipeline.translate("hello", "invalid", "tgl_Latn")
        self.assertEqual(result['status'], 'error')
        
        # Test invalid target language
        result = self.pipeline.translate("hello", "eng_Latn", "invalid")
        self.assertEqual(result['status'], 'error')
        
    def test_request_options(self):
        """Test translation request options"""
        # Clear cache first
        self.pipeline.cache.cache.clear()
        self.pipeline.cache.access_times.clear()
        
        text = "hello world"
        result = self.pipeline.translate(
            text,
            "eng_Latn",
            "tgl_Latn",
            session_id="test_session",
            use_cache=False,
            timeout=10
        )
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['cache_hit'], False)
        
    def test_response_format(self):
        """Test response format consistency"""
        text = "hello world"
        result = self.pipeline.translate(text, "eng_Latn", "tgl_Latn")
        
        # Check required fields
        required_fields = [
            'status',
            'translated_text',
            'cache_hit',
            'engine_used',
            'confidence',
            'session_id',
            'processing_time_ms',
            'original_text'
        ]
        
        for field in required_fields:
            self.assertIn(field, result)
            
    def test_timeout_handling(self):
        """Test timeout handling for each engine"""
        # Test with very long text to trigger timeout
        long_text = "hello " * 1000
        result = self.pipeline.translate(long_text, "eng_Latn", "tgl_Latn")
        self.assertEqual(result['status'], 'success')  # Should fall back to another engine

if __name__ == '__main__':
    unittest.main() 