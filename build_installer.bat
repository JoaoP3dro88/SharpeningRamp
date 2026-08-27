@echo off
echo ===================================================
echo [Titan Scheduler Compilation Engine]
echo ===================================================
rmdir /s /q build dist
pyinstaller --noconsole --name="SharpeningScheduler" ^
            --add-data "schema.sql;." ^
            src/main.py
echo Executable compilation finished. Packaging output at /dist.
pause
