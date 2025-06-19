"""
Simple NLLB Translation Test
"""
import zmq
import json
import time
import sys

# Default server settings
SERVER = "localhost"
PORT = 5581

# Test phrases covering different categories
TEST_PHRASES = [
    "Magandang umaga",                 # Basic greeting
    "Kumusta ka?",                     # Simple question
    "Buksan mo ang bintana",           # Command
    "Salamat sa tulong mo",            # Gratitude
    "Masarap ang pagkain",             # Statement
    "Na-check mo na ba yung files?",   # Taglish
    "I-download mo muna yung app",     # Technical instruction
    "Bahala na si Batman",             # Idiomatic
    "Anong oras na?",                  # Time question
    "Mahal kita"                       # Emotional
]

def translate_phrase(socket, phrase):
    """Send translation request and receive response"""
    # Prepare request
    request = {
        "action": "translate",
        "text": phrase,
        "src_lang": "tl",
        "tgt_lang": "en"
    }
    
    # Send request
    print(f"Sending: {phrase}")
    start_time = time.time()
    socket.send_json(request)
    
    # Receive response
    response = socket.recv_json()
    elapsed = time.time() - start_time
    
    # Process response
    if response.get("status") == "success":
        translated = response.get("translated_text", "")
        print(f"Original:   '{phrase}'")
        print(f"Translated: '{translated}'")
        print(f"Time:       {elapsed:.2f} seconds")
        print("-" * 50)
        return translated, elapsed
    else:
        error = response.get("message", "Unknown error")
        print(f"Error: {error}")
        print("-" * 50)
        return None, elapsed

def main():
    """Main test function"""
    # Create ZMQ socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    try:
        # Connect to the translation service
        print(f"Connecting to translation service at {SERVER}:{PORT}...")
        socket.connect(f"tcp://{SERVER}:{PORT}")
        print("Connected successfully")
        print("-" * 50)
        
        total_time = 0
        successful = 0
        
        # Test each phrase
        for i, phrase in enumerate(TEST_PHRASES, 1):
            print(f"\nTest {i}/{len(TEST_PHRASES)}")
            result, elapsed = translate_phrase(socket, phrase)
            if result:
                successful += 1
                total_time += elapsed
            
            # Small delay between requests
            if i < len(TEST_PHRASES):
                time.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 50)
        print("NLLB Translation Test Summary")
        print("=" * 50)
        print(f"Total phrases tested: {len(TEST_PHRASES)}")
        print(f"Successful translations: {successful}/{len(TEST_PHRASES)}")
        
        if successful > 0:
            avg_time = total_time / successful
            print(f"Average translation time: {avg_time:.2f} seconds")
        
        success_rate = (successful / len(TEST_PHRASES)) * 100
        print(f"Success rate: {success_rate:.1f}%")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        socket.close()
        context.term()
        print("\nTest completed")

if __name__ == "__main__":
    main()
