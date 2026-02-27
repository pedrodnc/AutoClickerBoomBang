@echo off
echo ========================================
echo  Compilando AutoClicker BoomBang (.NET)
echo ========================================
echo.

where dotnet >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: No tienes .NET SDK instalado.
    echo.
    echo Descargalo aqui:
    echo https://dotnet.microsoft.com/download/dotnet/7.0
    echo.
    echo Instala el ".NET 7.0 SDK" (no el Runtime)
    echo Luego vuelve a ejecutar este .bat
    echo.
    pause
    exit /b 1
)

echo Restaurando paquetes...
dotnet restore
echo.
echo Compilando...
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true
echo.
echo ========================================
echo  LISTO! El .exe esta en:
echo  bin\Release\net7.0-windows\win-x64\publish\
echo ========================================
pause
