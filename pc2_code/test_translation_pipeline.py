import zmq
import json
import time
import logging
from typing import Dict, Any
from common.env_helpers import get_env
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TranslationPipelineTester")

class TranslationPipelineTester:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5563")  # Consolidated Translator port
        
    def test_translation(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Test translation with the consolidated translator"""
        try:
            request = {
                "action": "translate",
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "session_id": f"test_{int(time.time()}"
            }
            
            self.socket.send_json(request)
            response = self.socket.recv_json()
            
            return {
                "status": response.get("status"),
                "translated_text": response.get("translated_text"),
                "engine_used": response.get("engine_used"),
                "cache_hit": response.get("cache_hit", False)
            }
        except Exception as e:
            logger.error(f"Translation test failed: {str(e)}")
            return {"status": "error", "message": str(e)}

def main():
    tester = TranslationPipelineTester()
    
    # Test cases
    test_cases = [
        {
            "text": "Kumusta ka?",
            "source_lang": "tgl_Latn",
            "target_lang": "eng_Latn",
            "description": "Basic Tagalog greeting"
        },
        {
            "text": "I need to check the status of my application.",
            "source_lang": "eng_Latn",
            "target_lang": "tgl_Latn",
            "description": "English to Tagalog technical phrase"
        },
        {
            "text": "Maganda ang weather today, perfect for a walk.",
            "source_lang": "tgl_Latn",
            "target_lang": "eng_Latn",
            "description": "Taglish mixed language"
        },
        {
            "text": "Gusto ko magluto ng adobo at sinigang.",
            "source_lang": "tgl_Latn",
            "target_lang": "eng_Latn",
            "description": "Tagalog with food terms"
        }
    ]
    
    # Run tests
    results = []
    for i, test in enumerate(test_cases, 1):
        logger.info(f"\nTest {i}: {test['description']}")
        logger.info(f"Input: {test['text']}")
        
        result = tester.test_translation(
            test['text'],
            test['source_lang'],
            test['target_lang']
        )
        
        results.append({
            "test_id": i,
            "description": test['description'],
            "input": test['text'],
            "result": result
        })
        
        logger.info(f"Result: {json.dumps(result, indent=2)}")
        time.sleep(1)  # Rate limiting
    
    # Save results
    with open("translation_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("\nTest results saved to translation_test_results.json")

if __name__ == "__main__":
    main() 