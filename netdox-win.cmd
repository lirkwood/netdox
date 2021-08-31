@echo off
setlocal
set APPDIR=%~dp0
GOTO :argparse

:: Print usage help
:help
echo Methods
echo init:                              Initialises the environment and generates a new cryptographic key.
echo config ^<file^>:                     Encrypts the file and moves it to the config location (src\config.bin). Will also test the connection to PageSeeder.
echo serve:                             Starts a Gunicorn web server listening for webhooks from the configured PageSeeder.
echo refresh:                           Generates a new set of PSML documents and uploads them to PageSeeder.
echo encrypt ^<infile^> [outfile]:        Encrypts a file using the internal cryptography from infile to outfile.
echo decrypt ^<infile^> [outfile]:        Decrypts a file using the internal cryptography from infile to outfile.
EXIT /B 0

:: Initialise container and generate a new crypto key
:init
if exist "%APPDIR%\netdox\src\config.bin" (
    echo [WARNING][netdox] This will generate a new cryptographic key, and your current configuration will be lost. Remove the config file to confirm this action.
    EXIT /B 1
)
python -m netdox.init
if %ERRORLEVEL% equ 0 (
    echo [INFO][netdox] Initialisation successful. Please load a config file.
) else (
    echo [ERROR][netdox] Initialisation unsuccessful. Please try again.
    EXIT /B 1
)
EXIT /B 0

:: Refresh dataset and upload to PageSeeder
:refresh
python -m netdox.refresh
EXIT /B 0

:: Serve webhook listener
:serve
gunicorn --reload -b '0.0.0.0:8080' -t 900 serve:app
EXIT /B 0

:: Load a file as config.bin
:config
if exist %1 (
    call :encrypt %1 "%APPDIR%\netdox\src\config.bin"
    python -m netdox.pageseeder
    if %ERRORLEVEL% equ 0 (
        del /q %1
        echo [INFO][netdox] Success: configuration is valid.
        EXIT /B 0
    ) else (
        echo [ERROR][netdox] Unable to contact or authenticate with the configured PageSeeder instance. Please check your configuration and try again.
        EXIT /B 1
    )
) else (
    echo [ERROR][netdox] Unable to find or parse config file at: "%~1"
    EXIT /B 1
)

:: Encrypt a file to a Fernet token
:encrypt
python -m netdox.crypto "encrypt" %1 %2
EXIT /B 0

:: Decrypt a file from a Fernet token
:decrypt
python -m netdox.crypto "decrypt" %1 %2
EXIT /B 0


:argparse
set CALLED=0
for %%m in ("init" "config" "refresh" "serve" "encrypt" "decrypt") do (
    if "%%~m"=="%1" (
        set CALLED=1
        call :%1 %2 %3
        set FUNCSTATUS=%ERRORLEVEL%
    )
)
if %CALLED%==0 call :help
EXIT /B %FUNCSTATUS%