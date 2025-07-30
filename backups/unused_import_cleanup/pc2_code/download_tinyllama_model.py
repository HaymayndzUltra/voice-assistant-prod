import transformers

try:
    model = transformers.AutoModelForCausalLM.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0')
    print('Model downloaded and cached successfully.')
except Exception as e:
    print(f'Error downloading model: {e}')
