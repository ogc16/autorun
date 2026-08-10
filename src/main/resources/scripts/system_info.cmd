@echo off
REM AutoRun sample: cross-platform system info (works on Windows + Linux via bash).
echo [system_info] Host: %COMPUTERNAME%
echo [system_info] User: %USERNAME%
echo [system_info] OS: %OS% (arch %PROCESSOR_ARCHITECTURE%)
echo [system_info] Date: %DATE% %TIME%
echo [system_info] Done.
