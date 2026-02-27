@echo off
echo ========================================
echo  Compilando AutoClicker BoomBang (.NET)
echo ========================================
echo.
echo Necesitas .NET 8 SDK instalado
echo https://dotnet.microsoft.com/download/dotnet/8.0
echo.
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true
echo.
echo ========================================
echo  LISTO! El .exe esta en:
echo  bin\Release\net8.0-windows\win-x64\publish\
echo ========================================
pause
