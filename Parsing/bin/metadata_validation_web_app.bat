@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%metadata_validation_web_app.py" %*

endlocal
