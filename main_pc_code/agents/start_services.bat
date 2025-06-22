@echo off
cd /d "%~dp0"
echo Starting Voice Assistant Services...

start "Audio Capture" cmd /k "python modular_system/core_agents/streaming_audio_capture.py"
timeout /t 2 /nobreak > nul

start "Speech Recognition" cmd /k "python modular_system/core_agents/streaming_speech_recognition.py"
timeout /t 2 /nobreak > nul

start "Language Analyzer" cmd /k "python modular_system/core_agents/streaming_language_analyzer.py"
timeout /t 2 /nobreak > nul

start "Translation" cmd /k "python modular_system/core_agents/streaming_language_to_llm.py"
timeout /t 2 /nobreak > nul

start "Text Processor" cmd /k "python modular_system/core_agents/streaming_text_processor.py"
timeout /t 2 /nobreak > nul

echo All services started. Press any key to run the end-to-end test...
pause > nul

start "End-to-End Test" cmd /k "python end_to_end_pipeline_test.py" 