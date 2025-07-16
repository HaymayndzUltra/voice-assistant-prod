@echo off
echo Stopping all Voice Assistant Services...

taskkill /F /FI "WINDOWTITLE eq Audio Capture*" /T
taskkill /F /FI "WINDOWTITLE eq Speech Recognition*" /T
taskkill /F /FI "WINDOWTITLE eq Language Analyzer*" /T
taskkill /F /FI "WINDOWTITLE eq Translation*" /T
taskkill /F /FI "WINDOWTITLE eq Text Processor*" /T
taskkill /F /FI "WINDOWTITLE eq End-to-End Test*" /T

echo All services stopped.
pause 