@echo off
echo ============================================================
echo   Build: Sistema de Gestao de Documentos DNE / MIREME 2026
echo ============================================================

set PYEXE=C:\Users\Admin\anaconda3\python.exe
set PYINSTALLER=C:\Users\Admin\anaconda3\Scripts\pyinstaller.exe

echo Verificando Python...
"%PYEXE%" --version
if errorlevel 1 (
    echo ERRO: Python nao encontrado em %PYEXE%
    pause & exit /b 1
)

echo Instalando/verificando PyInstaller...
"%PYEXE%" -m pip install pyinstaller --quiet

echo Compilando...
"%PYEXE%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --icon=assets\icon.ico ^
    --name="GestaoDocumentos_DNE" ^
    --add-data="assets;assets" ^
    --hidden-import=customtkinter ^
    --hidden-import=openpyxl ^
    --hidden-import=matplotlib ^
    --hidden-import=PIL ^
    --collect-all=customtkinter ^
    main.py

if errorlevel 1 (
    echo ERRO: Falha na compilacao!
    pause & exit /b 1
)

echo.
echo ============================================================
echo   Build concluido!
echo   Ficheiro: dist\GestaoDocumentos_DNE.exe
echo ============================================================
pause
