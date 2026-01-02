@echo off
setlocal

REM ===== 설정값  =====
set MOBSF_URL=http://127.0.0.1:8000
set APIKEY=06b05afc0ddec72b9f9a3867d5fa0283a90717a87a0cb74fb14cc8e2a9d18164
set APK_PATH=C:\Users\coron\Desktop\sample.apk
set OUT_PDF=C:\Users\coron\Desktop\report.pdf

REM ===== 1) APK 업로드 -> JSON 응답 저장 =====
curl -s -X POST "%MOBSF_URL%/api/v1/upload" ^
  -H "X-Mobsf-Api-Key: %APIKEY%" ^
  -F "file=@%APK_PATH%" > upload.json

REM ===== 2) hash 뽑기 (PowerShell로 JSON 파싱) =====
for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-Content upload.json | ConvertFrom-Json).hash"') do set HASH=%%H

echo [INFO] HASH=%HASH%

REM ===== 3) 스캔 실행 =====
curl -s -X POST "%MOBSF_URL%/api/v1/scan" ^
  -H "X-Mobsf-Api-Key: %APIKEY%" ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  --data "scan_type=apk&file_name=sample.apk&hash=%HASH%" > scan.json

REM ===== 4) PDF 다운로드 =====
curl -s -L -X POST "%MOBSF_URL%/api/v1/download_pdf" ^
  -H "X-Mobsf-Api-Key: %APIKEY%" ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  --data "hash=%HASH%&scan_type=apk" ^
  --output "%OUT_PDF%"

echo [OK] Saved: %OUT_PDF%
start "" "%OUT_PDF%"

endlocal
