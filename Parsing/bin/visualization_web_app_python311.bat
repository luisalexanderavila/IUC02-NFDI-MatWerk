@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
conda run -n python311 python "%SCRIPT_DIR%visualization_web_app.py" %*

endlocal
