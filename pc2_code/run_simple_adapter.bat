@echo off
echo === Starting Simple Translation Adapter (FALLBACK) ===
echo This adapter does NOT require Ollama
echo It uses a simple dictionary for basic Tagalog-English translations
echo.

cd %~dp0
python simple_translation_adapter.py --port=5581
pause
