@echo off
REM Daily Fund Calculations - Entry Point
REM Scheduled via Windows Task Scheduler for 6:00 AM weekdays

SET PYTHON_PATH=python
SET SCRIPT_DIR=%~dp0

cd /d %SCRIPT_DIR%

REM Activate virtual environment if using one
REM call venv\Scripts\activate.bat

REM Run main pipeline (must use -m to run as module for correct imports)
%PYTHON_PATH% -m orchestration.main_pipeline --date=today

REM Capture exit code
SET EXIT_CODE=%ERRORLEVEL%

REM Log completion
echo [%DATE% %TIME%] Daily calculation completed with exit code: %EXIT_CODE% >> logs\scheduler.log

exit /b %EXIT_CODE%
