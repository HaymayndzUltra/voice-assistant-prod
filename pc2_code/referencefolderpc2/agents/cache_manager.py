import redis
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import hashlib

class CacheManager:
    def __init__(self, redis_host='localhost', redis_port=6379, db=0):
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=db)
        self.cache_config = {
            'nlu_results': timedelta(minutes=5),
            'model_decisions': timedelta(minutes=10),
            'context_summaries': timedelta(hours=1),
            'tool_responses': timedelta(minutes=15)
        }

    def _generate_cache_key(self, cache_type: str, data: Any) -> str:
        """Generate a unique cache key based on data and type"""
        key_data = json.dumps({
            'type': cache_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }, sort_keys=True)
        return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"

    def cache_nlu_result(self, user_input: str, intent: str, entities: Dict[str, Any]) -> None:
        """Cache NLU processing results"""
        cache_key = self._generate_cache_key('nlu_results', user_input)
        cache_data = {
            'intent': intent,
            'entities': entities,
            'timestamp': datetime.now().isoformat()
        }
        self.redis.setex(
            cache_key,
            self.cache_config['nlu_results'],
            json.dumps(cache_data)
        )

    def get_cached_nlu_result(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Get cached NLU results"""
        cache_key = self._generate_cache_key('nlu_results', user_input)
        cached_data = self.redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        return None

    def cache_model_decision(self, task_type: str, model_id: str) -> None:
        """Cache model router decisions"""
        cache_key = self._generate_cache_key('model_decisions', task_type)
        cache_data = {
            'model_id': model_id,
            'timestamp': datetime.now().isoformat()
        }
        self.redis.setex(
            cache_key,
            self.cache_config['model_decisions'],
            json.dumps(cache_data)
        )

    def get_cached_model_decision(self, task_type: str) -> Optional[str]:
        """Get cached model decision"""
        cache_key = self._generate_cache_key('model_decisions', task_type)
        cached_data = self.redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)['model_id']
        return None

    def cache_context_summary(self, session_id: str, summary: str) -> None:
        """Cache context summaries"""
        cache_key = self._generate_cache_key('context_summaries', session_id)
        cache_data = {
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        self.redis.setex(
            cache_key,
            self.cache_config['context_summaries'],
            json.dumps(cache_data)
        )

    def get_cached_context_summary(self, session_id: str) -> Optional[str]:
        """Get cached context summary"""
        cache_key = self._generate_cache_key('context_summaries', session_id)
        cached_data = self.redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)['summary']
        return None

    def cache_tool_response(self, tool_name: str, response: Any) -> None:
        """Cache tool responses"""
        cache_key = self._generate_cache_key('tool_responses', tool_name)
        cache_data = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        self.redis.setex(
            cache_key,
            self.cache_config['tool_responses'],
            json.dumps(cache_data)
        )

    def get_cached_tool_response(self, tool_name: str) -> Optional[Any]:
        """Get cached tool response"""
        cache_key = self._generate_cache_key('tool_responses', tool_name)
        cached_data = self.redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)['response']
        return None

    def invalidate_cache(self, cache_type: str, data: Any) -> None:
        """Invalidate specific cache entry"""
        cache_key = self._generate_cache_key(cache_type, data)
        self.redis.delete(cache_key)

    def clear_all_cache(self) -> None:
        """Clear all cache entries"""
        self.redis.flushdb()

    def run_cleanup(self):
        """Run background cleanup for expired cache entries"""
        while True:
            try:
                # Redis handles expiration automatically, but we can do additional cleanup if needed
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                break

def main():
    cache_manager = CacheManager()
    cache_manager.run_cleanup()

if __name__ == "__main__":
    main()
