@echo off
title Animal AI Dashboard
set TF_ENABLE_ONEDNN_OPTS=0
set TF_CPP_MIN_LOG_LEVEL=3
set MPLCONFIGDIR=%TEMP%\mpl_cache
set PYTHONWARNINGS=ignore

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe app.py
) else (
    python app.py
)

pause

