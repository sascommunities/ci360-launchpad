@echo off
setlocal

REM Set environment variables
set FLASK_APP=BulkCustomTaskDataExportApplication.py
set FLASK_ENV=development
set FLASK_RUN_HOST=0.0.0.0
set FLASK_RUN_PORT=5000
set REQUEST_DATA_FOLDER=%cd%\request_data
set DATA_FOLDER=%cd%\data

REM Run the Flask application
python -m flask run --host=%FLASK_RUN_HOST% --port=%FLASK_RUN_PORT%

endlocal