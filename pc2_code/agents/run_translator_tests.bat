@echo off
echo Starting Consolidated Translator Tests...
echo.

:: Set Python path
set PYTHONPATH=%CD%

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Run tests and save output to log file
python test_translator.py > logs\translator_tests.log 2>&1

:: Check if tests passed
if %ERRORLEVEL% EQU 0 (
    echo.
    echo All tests passed successfully!
    echo Test results have been saved to logs\translator_tests.log
) else (
    echo.
    echo Some tests failed. Please check logs\translator_tests.log for details.
)

echo.
pause 