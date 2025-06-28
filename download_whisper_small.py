from transformers import pipeline

# Download and cache the 'openai/whisper-small' model
pipe = pipeline("automatic-speech-recognition", model="openai/whisper-small")
print("Model downloaded and cached successfully.")
