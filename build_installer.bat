@echo off
echo ===================================================
echo [Sharpening ramp]
echo ===================================================
rmdir /s /q build dist
pyinstaller --noconsole --name="Rampa de afiacao" ^
            --icon="icon.ico" ^
            --contents-directory "." ^
            --add-data "schema.sql;." ^
            --add-data "config.ini;." ^
            src/main.py
echo Executable compilation finished. Packaging output at /dist.
pause