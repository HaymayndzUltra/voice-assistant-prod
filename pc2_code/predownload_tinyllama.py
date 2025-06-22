"""
Pre-download and cache TinyLlama model to avoid download delays during testing
"""
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
print(f"Attempting to download/cache {model_name}...")

# Download and cache the tokenizer
print("Downloading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
print("Tokenizer cached successfully")

# Download and cache the model
print("Downloading model (this might take a few minutes)...")
model = AutoModelForCausalLM.from_pretrained(model_name, ignore_mismatched_sizes=True)
print("Model cached successfully")

print(f"Model {model_name} has been cached and is ready for use by tinyllama_service.py")
