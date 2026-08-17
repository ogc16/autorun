@echo off
REM ============================================================
REM Windows Patch Script
REM Checks for, downloads, and installs Windows Updates.
REM
REM Parameters:
REM   auto_reboot  - Automatically reboot after install (default: false)
REM   kb_filter    - Comma-separated KB numbers to install (default: all)
REM   dry_run      - Only check, do not install (default: false)
REM ============================================================
setlocal EnableDelayedExpansion

set AUTO_REBOOT=false
set DRY_RUN=false
set KB_FILTER=
set LOG_DIR=%TEMP%\autorun-patches
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set LOG_FILE=%LOG_DIR%\windows-patch-%DATE:~-4%%DATE:~4,2%%DATE:~7,2%.log

REM Parse arguments
for %%a in (%*) do (
    echo %%a | findstr /B "auto_reboot=" >nul && set AUTO_REBOOT=%%a
    echo %%a | findstr /B "dry_run=" >nul && set DRY_RUN=%%a
    echo %%a | findstr /B "kb_filter=" >nul && set KB_FILTER=%%a
)

echo [%DATE% %TIME%] Windows Patch Script Started > "%LOG_FILE%"
echo [%DATE% %TIME%] auto_reboot=%AUTO_REBOOT% dry_run=%DRY_RUN% >> "%LOG_FILE%"

REM Ensure PSWindowsUpdate module is installed
echo [%DATE% %TIME%] Checking PSWindowsUpdate module... >> "%LOG_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "if (-not (Get-Module -ListAvailable -Name PSWindowsUpdate)) { ^
        Write-Host 'Installing PSWindowsUpdate module...'; ^
        Install-Module PSWindowsUpdate -Force -AcceptGallery -Scope CurrentUser ^
    } else { ^
        Write-Host 'PSWindowsUpdate module already installed.' ^
    }" >> "%LOG_FILE%" 2>&1

REM Check for available updates
echo [%DATE% %TIME%] Checking for available updates... >> "%LOG_FILE%"
if "%DRY_RUN%"=="true" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Import-Module PSWindowsUpdate; ^
         $updates = Get-WindowsUpdate -AcceptAll; ^
         if ($updates.Count -eq 0) { ^
             Write-Host 'No updates available.'; ^
             exit 0 ^
         }; ^
         Write-Host \"Found $($updates.Count) update(s):\"; ^
         $updates | ForEach-Object { ^
             Write-Host \"  - $($_.KBArticleIDs) | $($_.Title) | $($_.Size) bytes\" ^
         }; ^
         exit 0" >> "%LOG_FILE%" 2>&1
    echo [%DATE% %TIME%] Dry run complete. No changes made. >> "%LOG_FILE%"
    type "%LOG_FILE%"
    exit /b 0
)

REM Install updates
echo [%DATE% %TIME%] Installing updates... >> "%LOG_FILE%"
if "%AUTO_REBOOT%"=="true" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Import-Module PSWindowsUpdate; ^
         Get-WindowsUpdate -AcceptAll -Install -AutoReboot" >> "%LOG_FILE%" 2>&1
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Import-Module PSWindowsUpdate; ^
         Get-WindowsUpdate -AcceptAll -Install -IgnoreReboot" >> "%LOG_FILE%" 2>&1
)

set INSTALL_EXIT=%ERRORLEVEL%

REM Get installed updates for report
echo [%DATE% %TIME%] Recent installed updates: >> "%LOG_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Import-Module PSWindowsUpdate; ^
     Get-WindowsUpdate -Installed | Select-Object -First 10 | ^
     ForEach-Object { Write-Host \"  $($_.KBArticleIDs) | $($_.Title) | Installed: $($_.LastDeploymentChangeTime)\" }" >> "%LOG_FILE%" 2>&1

echo [%DATE% %TIME%] Patch script completed with exit code %INSTALL_EXIT% >> "%LOG_FILE%"
type "%LOG_FILE%"
exit /b %INSTALL_EXIT%
