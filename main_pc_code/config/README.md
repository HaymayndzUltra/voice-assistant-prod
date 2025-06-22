# Configuration Directory

This directory contains configuration files for the Voice Assistant system.

## API Keys

For security reasons, API keys are not stored in the repository. Instead, you should:

1. Copy `api_keys.json.template` to `api_keys.json`
2. Fill in your actual API keys in the `api_keys.json` file

```bash
cp api_keys.json.template api_keys.json
# Then edit api_keys.json with your actual keys
```

Alternatively, you can set these keys as environment variables:

- `PORCUPINE_ACCESS_KEY` - For wake word detection
- `OPENAI_API_KEY` - For OpenAI services
- `ELEVENLABS_API_KEY` - For ElevenLabs TTS
- `GOOGLE_CLOUD_API_KEY` - For Google Cloud services

The system will check environment variables first, then fall back to the config file.

## Security Note

Never commit your actual API keys to version control. The `.gitignore` file should include `api_keys.json` to prevent accidental commits.
