@echo off
chcp 65001 >nul
title Calculate Age - by birth and death year
echo.
echo ========================================
echo          Calculate Age Tool
echo   Enter Ctrl+C to exit when done
echo ========================================
echo.

:loop
call :calculate
echo.
goto loop

:calculate
set "birth_year="
set "death_year="
set /p birth_year=Enter birth year: 
if "%birth_year%"=="" (
    echo Birth year cannot be empty!
    goto :eof
)

set /p death_year=Enter death year: 
if "%death_year%"=="" (
    echo Death year cannot be empty!
    goto :eof
)

echo %birth_year%|findstr /r "^[0-9]*$" >nul
if errorlevel 1 (
    echo.
    echo Error: Birth year must be a number!
    goto :eof
)

echo %death_year%|findstr /r "^[0-9]*$" >nul
if errorlevel 1 (
    echo.
    echo Error: Death year must be a number!
    goto :eof
)

if %birth_year% gtr %death_year% (
    echo.
    echo Error: Birth year cannot be greater than death year!
    goto :eof
)

set /a age = %death_year% - %birth_year%

echo.
echo ========================================
echo Result:
echo Birth year: %birth_year%
echo Death year: %death_year%
echo Age: %age% years old
echo ========================================
goto :eof
