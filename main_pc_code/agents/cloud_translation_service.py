from common.core.base_agent import BaseAgent
from common.hybrid_api_manager import HybridAPIManager
from common.pools.zmq_pool import get_rep_socket
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Optional, List, Any
import os
import psutil
from pathlib import Path

"""
Cloud Translation Service - Pure Cloud Provider Router
Intelligent multi-provider translation with fallbacks:
1. Primary: Google Translate (fast, good quality)
2. Secondary: Azure Translator (enterprise-grade)
3. Tertiary: AWS Translate (reliable)
4. Emergency: OpenAI GPT-4o (best quality, expensive)

Features:
- Smart provider selection based on language pairs
- Performance monitoring and caching
- Intelligent fallback routing
- Cost optimization
- Language detection and validation
"""

# Configure logging using canonical approach
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

# Translation cache for frequent requests
class TranslationCache:
    """Thread-safe cache for translations with TTL."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = threading.Lock()
        
    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key from translation parameters."""
        return f"{source_lang}:{target_lang}:{hash(text)}"
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation if not expired."""
        key = self._generate_key(text, source_lang, target_lang)
        
        with self.lock:
            if key in self.cache:
                timestamp = self.timestamps.get(key, 0)
                if time.time() - timestamp < self.ttl:
                    return self.cache[key]
                else:
                    # Expired - remove from cache
                    del self.cache[key]
                    del self.timestamps[key]
        return None
    
    def set(self, text: str, source_lang: str, target_lang: str, translation: str):
        """Set translation in cache with timestamp."""
        key = self._generate_key(text, source_lang, target_lang)
        
        with self.lock:
            # Check cache size limit
            if len(self.cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = translation
            self.timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cached translations."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": getattr(self, '_hit_rate', 0.0),
                "total_requests": getattr(self, '_total_requests', 0),
                "cache_hits": getattr(self, '_cache_hits', 0)
            }


class PerformanceMetrics:
    """Track performance metrics for translation providers."""
    
    def __init__(self):
        self.provider_stats = defaultdict(lambda: {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "total_latency": 0.0,
            "avg_latency": 0.0,
            "last_used": None,
            "error_rate": 0.0
        })
        self.lock = threading.Lock()
    
    def record_request(self, provider: str, success: bool, latency: float):
        """Record a translation request result."""
        with self.lock:
            stats = self.provider_stats[provider]
            stats["requests"] += 1
            stats["last_used"] = datetime.now().isoformat()
            
            if success:
                stats["successes"] += 1
                stats["total_latency"] += latency
                stats["avg_latency"] = stats["total_latency"] / stats["successes"]
            else:
                stats["failures"] += 1
            
            stats["error_rate"] = stats["failures"] / stats["requests"]
    
    def get_best_provider(self, exclude: List[str] = None) -> Optional[str]:
        """Get the best performing provider based on error rate and latency."""
        exclude = exclude or []
        
        with self.lock:
            available_providers = [
                (provider, stats) for provider, stats in self.provider_stats.items()
                if provider not in exclude and stats["requests"] > 0
            ]
            
            if not available_providers:
                return None
            
            # Score providers based on error rate (lower is better) and latency
            def score_provider(provider_stats):
                provider, stats = provider_stats
                error_penalty = stats["error_rate"] * 100  # Heavy penalty for errors
                latency_penalty = stats["avg_latency"] if stats["avg_latency"] > 0 else 10
                return error_penalty + latency_penalty
            
            best_provider = min(available_providers, key=score_provider)
            return best_provider[0]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics."""
        with self.lock:
            return dict(self.provider_stats)


class CloudTranslationService(BaseAgent):
    """Cloud-only translation service with intelligent provider routing."""
    
    def __init__(self, port: int = 5584, **kwargs):
        health_check_port = kwargs.get('health_check_port', 6584)
        super().__init__(port=port, name="CloudTranslationService", health_check_port=health_check_port)
        
        # Initialize hybrid API manager for cloud providers
        self.hybrid_api = HybridAPIManager()
        
        # Initialize components
        self.cache = TranslationCache()
        self.metrics = PerformanceMetrics()
        
        # Provider configuration from environment
        self.primary_provider = os.getenv('TRANSLATE_PRIMARY_PROVIDER', 'google')
        self.fallback_provider = os.getenv('TRANSLATE_FALLBACK_PROVIDER', 'azure')
        
        # Provider priority order
        self.provider_priority = [
            self.primary_provider,
            self.fallback_provider,
            'aws',
            'openai'  # Most expensive, last resort
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        self.provider_priority = [p for p in self.provider_priority if not (p in seen or seen.add(p))]
        
        # Language code mapping for different providers
        self.language_mappings = {
            'google': {
                'filipino': 'tl', 'tagalog': 'tl', 'tgl': 'tl',
                'english': 'en', 'eng': 'en',
                'spanish': 'es', 'spa': 'es',
                'japanese': 'ja', 'jpn': 'ja',
                'korean': 'ko', 'kor': 'ko',
                'chinese': 'zh', 'zho': 'zh'
            },
            'azure': {
                'filipino': 'fil', 'tagalog': 'fil', 'tgl': 'fil',
                'english': 'en', 'eng': 'en',
                'spanish': 'es', 'spa': 'es',
                'japanese': 'ja', 'jpn': 'ja',
                'korean': 'ko', 'kor': 'ko',
                'chinese': 'zh-Hans', 'zho': 'zh-Hans'
            },
            'aws': {
                'filipino': 'tl', 'tagalog': 'tl', 'tgl': 'tl',
                'english': 'en', 'eng': 'en',
                'spanish': 'es', 'spa': 'es',
                'japanese': 'ja', 'jpn': 'ja',
                'korean': 'ko', 'kor': 'ko',
                'chinese': 'zh', 'zho': 'zh'
            }
        }
        
        # Request processing
        self.running = False
        
        logger.info(f"CloudTranslationService initialized with providers: {self.provider_priority}")
    
    def normalize_language_code(self, lang_code: str, provider: str) -> str:
        """Normalize language code for specific provider."""
        lang_code = lang_code.lower().strip()
        
        # Get provider-specific mapping
        provider_mapping = self.language_mappings.get(provider, {})
        
        # Try direct mapping first
        if lang_code in provider_mapping:
            return provider_mapping[lang_code]
        
        # Common mappings
        common_mappings = {
            'fil': 'filipino', 'tl': 'filipino', 'tgl': 'filipino',
            'en': 'english', 'eng': 'english',
            'es': 'spanish', 'spa': 'spanish',
            'ja': 'japanese', 'jpn': 'japanese',
            'ko': 'korean', 'kor': 'korean',
            'zh': 'chinese', 'zho': 'chinese'
        }
        
        base_lang = common_mappings.get(lang_code, lang_code)
        return provider_mapping.get(base_lang, lang_code)
    
    def detect_language(self, text: str) -> str:
        """Detect language of input text."""
        try:
            # Use hybrid API manager for language detection
            result = self.hybrid_api.detect_language(text)
            if result.get('success'):
                return result.get('language', 'auto')
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
        
        # Fallback: Simple heuristics
        filipino_indicators = ['ang', 'ng', 'sa', 'mga', 'ako', 'ikaw', 'siya', 'kami', 'tayo', 'kayo', 'sila']
        text_lower = text.lower()
        
        filipino_count = sum(1 for word in filipino_indicators if word in text_lower)
        if filipino_count >= 2:
            return 'filipino'
        
        return 'auto'
    
    def translate_with_provider(self, text: str, source_lang: str, target_lang: str, provider: str) -> Dict[str, Any]:
        """Translate text using specific provider."""
        start_time = time.time()
        
        try:
            # Normalize language codes for provider
            norm_source = self.normalize_language_code(source_lang, provider)
            norm_target = self.normalize_language_code(target_lang, provider)
            
            logger.info(f"Translating with {provider}: {norm_source} -> {norm_target}")
            
            # Use hybrid API manager
            result = self.hybrid_api.translate(
                text=text,
                source_language=norm_source,
                target_language=norm_target,
                provider=provider
            )
            
            latency = time.time() - start_time
            
            if result.get('success'):
                self.metrics.record_request(provider, True, latency)
                return {
                    'success': True,
                    'translated_text': result.get('translated_text', ''),
                    'provider': provider,
                    'latency': latency,
                    'source_lang': norm_source,
                    'target_lang': norm_target
                }
            else:
                self.metrics.record_request(provider, False, latency)
                return {
                    'success': False,
                    'error': result.get('error', 'Translation failed'),
                    'provider': provider,
                    'latency': latency
                }
                
        except Exception as e:
            latency = time.time() - start_time
            self.metrics.record_request(provider, False, latency)
            logger.error(f"Translation error with {provider}: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': provider,
                'latency': latency
            }
    
    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'english') -> Dict[str, Any]:
        """Translate text with intelligent provider fallback."""
        if not text or not text.strip():
            return {
                'success': False,
                'error': 'Empty text provided'
            }
        
        # Auto-detect source language if needed
        if source_lang == 'auto':
            source_lang = self.detect_language(text)
        
        # Check cache first
        cached_translation = self.cache.get(text, source_lang, target_lang)
        if cached_translation:
            return {
                'success': True,
                'translated_text': cached_translation,
                'provider': 'cache',
                'latency': 0.0,
                'cached': True
            }
        
        # Try each provider in priority order
        failed_providers = []
        
        for provider in self.provider_priority:
            logger.info(f"Attempting translation with {provider}")
            
            result = self.translate_with_provider(text, source_lang, target_lang, provider)
            
            if result['success']:
                # Cache successful translation
                self.cache.set(text, source_lang, target_lang, result['translated_text'])
                
                result['failed_providers'] = failed_providers
                return result
            else:
                failed_providers.append({
                    'provider': provider,
                    'error': result.get('error', 'Unknown error')
                })
                logger.warning(f"Provider {provider} failed: {result.get('error')}")
        
        # All providers failed
        return {
            'success': False,
            'error': 'All translation providers failed',
            'failed_providers': failed_providers
        }
    
    def handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming translation request."""
        try:
            action = message.get('action', 'translate')
            
            if action == 'translate':
                text = message.get('text', '')
                source_lang = message.get('source_lang', 'auto')
                target_lang = message.get('target_lang', 'english')
                
                result = self.translate(text, source_lang, target_lang)
                
                if result['success']:
                    return {
                        'status': 'success',
                        'translated_text': result['translated_text'],
                        'provider': result['provider'],
                        'latency_ms': int(result.get('latency', 0) * 1000),
                        'cached': result.get('cached', False)
                    }
                else:
                    return {
                        'status': 'error',
                        'message': result['error'],
                        'failed_providers': result.get('failed_providers', [])
                    }
            
            elif action == 'health':
                return self._get_health_status()
            
            elif action == 'metrics':
                return {
                    'status': 'success',
                    'metrics': self.metrics.get_metrics(),
                    'cache_stats': self.cache.get_stats()
                }
            
            elif action == 'clear_cache':
                self.cache.clear()
                return {
                    'status': 'success',
                    'message': 'Cache cleared'
                }
            
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown action: {action}'
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                'status': 'error',
                'message': f'Internal error: {str(e)}'
            }
    
    def run(self):
        """Main service loop."""
        self.running = True
        logger.info("CloudTranslationService started")
        
        try:
            while self.running:
                try:
                    # Wait for incoming requests
                    message = self.socket.recv_json(zmq.NOBLOCK)
                    
                    # Process request
                    response = self.handle_request(message)
                    
                    # Send response
                    self.socket.send_json(response)
                    
                except zmq.Again:
                    # No message available, continue
                    time.sleep(0.01)
                    continue
                    
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': 'Internal server error'
                        })
                    except Exception:
                        pass
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        base_status = super()._get_health_status()
        
        try:
            # Test each provider
            provider_health = {}
            test_text = "Hello"
            
            for provider in self.provider_priority:
                try:
                    result = self.translate_with_provider(test_text, 'english', 'spanish', provider)
                    provider_health[provider] = {
                        'status': 'healthy' if result['success'] else 'unhealthy',
                        'latency_ms': int(result.get('latency', 0) * 1000),
                        'error': result.get('error')
                    }
                except Exception as e:
                    provider_health[provider] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            
            # Overall health based on provider availability
            healthy_providers = [p for p, status in provider_health.items() if status['status'] == 'healthy']
            
            base_status.update({
                'providers': provider_health,
                'healthy_providers': healthy_providers,
                'provider_priority': self.provider_priority,
                'cache_stats': self.cache.get_stats(),
                'performance_metrics': self.metrics.get_metrics(),
                'status': 'healthy' if healthy_providers else 'degraded'
            })
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            base_status.update({
                'status': 'warning',
                'error': str(e)
            })
        
        return base_status
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up CloudTranslationService")
        self.running = False
        
        # Clear cache
        if hasattr(self, 'cache'):
            self.cache.clear()
        
        # Call parent cleanup
        super().cleanup()


if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = CloudTranslationService()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()
