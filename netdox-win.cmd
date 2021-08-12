@echo off
setlocal
set APPDIR=%~dp0
cd "%APPDIR%/netdox"
GOTO :argparse

:: Print usage help
:help
echo Methods
echo init:                              Initialises the environment and generates a new cryptographic key.
echo serve:                             Starts a Gunicorn web server listening for webhooks from the configured PageSeeder.
echo refresh:                           Generates a new set of PSML documents and uploads them to PageSeeder.
echo encrypt ^<infile^> [outfile]:      Encrypts a file using the internal cryptography from infile to outfile.
echo decrypt ^<infile^> [outfile]:      Decrypts a file using the internal cryptography from infile to outfile.
EXIT /B 0

:: Initialise container with provided config to allow other processes to run
:init
if not exist "src/config.bin" (
    echo "[WARNING][netdox] Primary configuration file missing. Please place config.bin in src/"
    EXIT /B 1
)
python "init.py"
if %ERRORLEVEL% equ 0 (
    echo "[INFO][netdox] Initialisation successful."
) else (
    echo "[ERROR][netdox] Initialisation unsuccessful. Please try again."
    EXIT /B 1
)
EXIT /B 0

:: Refresh dataset and upload to PageSeeder
:refresh
python "refresh.py"
EXIT /B 0

:: Serve webhook listener
:serve
gunicorn --reload -b '0.0.0.0:8080' -t 900 serve:app
EXIT /B 0

:: Encrypt a file to a Fernet token
:encrypt
python "crypto.py" "encrypt" %2 %3
EXIT /B 0

:: Decrypt a file from a Fernet token
:decrypt
python "crypto.py" "decrypt" %2 %3
EXIT /B 0


:argparse
set CALLED=0
for %%m in ("help" "init" "refresh" "serve" "encrypt" "decrypt") do (
    if "%%~m"=="%1" (
        set CALLED=1
        @REM call :%1
        set FUNCSTATUS=%ERRORLEVEL%
    )
)
if %CALLED%==0 call :help
EXIT /B %FUNCSTATUS%