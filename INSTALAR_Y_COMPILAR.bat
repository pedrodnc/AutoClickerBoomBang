@echo off
echo ============================================
echo  AutoClicker BoomBang - Instalacion completa
echo ============================================
echo.
echo [1/3] Instalando Python...
winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
echo.
echo Actualizando PATH...
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
echo.
echo [2/3] Instalando dependencias...
pip install pyautogui opencv-python numpy pillow mss pyinstaller
echo.
echo [3/3] Compilando .exe...
pyinstaller --onefile --noconsole --name AutoClickerBoomBang autoclicker.py
echo.
echo ============================================
echo.
echo  LISTO! Tu .exe esta en:
echo  dist\AutoClickerBoomBang.exe
echo.
echo  Copia ese archivo donde quieras y ejecutalo.
echo.
echo ============================================
pause
