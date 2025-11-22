@echo off
cls

set INPUT_UI_FILE=ui\main.ui
set OUTPUT_PY_FILE=scripts\ui\mainUI.py

echo Activating Python Virtual Environment...

call ..\Scripts\activate.bat

echo.
echo Converting %INPUT_UI_FILE% to %OUTPUT_PY_FILE%

:: Ensure pyuic5 is available in the virtual environment's PATH
pyside6-uic "%INPUT_UI_FILE%" -o "%OUTPUT_PY_FILE%"
pyside6-rcc scripts\ui\icons_resource.qrc -o scripts\ui\icons_resource_rc.py
echo.
echo Deactivating Virtual Environment...
:: Deactivate the environment after the conversion is done
deactivate

echo.
echo Conversion process finished.
pause
