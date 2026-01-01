@echo off
setlocal EnableDelayedExpansion

REM ================= 설정 =================
set KEYSTORE=test.keystore
set KEYALIAS=testkey
set STOREPASS=pgsHZz
set KEYPASS=pgsHZz

set SAMPLE_APK=sample.apk
set INNER_APK=pgsHZz.apk

REM ================= sample.apk 압축 해제 =================
echo [*] Unzip sample.apk
copy %SAMPLE_APK% sample.zip >nul
powershell -Command "Expand-Archive -Force sample.zip sample_unzip"

REM ================= 내부 APK 압축 해제 =================
echo [*] Unzip inner apk
copy sample_unzip\assets\%INNER_APK% inner.zip >nul
powershell -Command "Expand-Archive -Force inner.zip pgsHZz_unzip"

REM ================= DEX 복호화 =================
echo [*] Decrypt dex
python decrypt_dex.py

REM ================= 내부 APK 재압축 =================
echo [*] Repack inner apk
if exist pgsHZz_re-unsigned.apk del pgsHZz_re-unsigned.apk

cd pgsHZz_unzip
jar cf ..\pgsHZz_re-unsigned.apk *
cd ..

REM ================= keystore 생성 =================
if not exist %KEYSTORE% (
    echo [*] Generate keystore
    keytool -genkey -v ^
     -keystore %KEYSTORE% ^
     -alias %KEYALIAS% ^
     -keyalg RSA ^
     -keysize 2048 ^
     -validity 10000 ^
     -storepass %STOREPASS% ^
     -keypass %KEYPASS% ^
     -dname "CN=pgsHZz, OU=pgsHZz, O=pgsHZz, L=Seoul, S=Seoul, C=KR"
)

REM ================= 내부 APK 서명 =================
echo [*] Sign inner apk
call apksigner sign ^
 --ks %KEYSTORE% ^
 --ks-key-alias %KEYALIAS% ^
 --ks-pass pass:%STOREPASS% ^
 --key-pass pass:%KEYPASS% ^
 --out pgsHZz_re.apk ^
 pgsHZz_re-unsigned.apk

REM ================= 내부 APK 교체 =================
echo [*] Replace inner apk
del sample_unzip\assets\%INNER_APK%
copy pgsHZz_re.apk sample_unzip\assets\%INNER_APK% >nul

REM ================= sample.apk 재압축 =================
echo [*] Repack sample apk
if exist sample_re.apk del sample_re.apk

cd sample_unzip
jar cf ..\sample_re.apk *
cd ..

REM ================= sample.apk 서명 =================
echo [*] Sign sample apk
call apksigner sign ^
 --ks %KEYSTORE% ^
 --ks-key-alias %KEYALIAS% ^
 --ks-pass pass:%STOREPASS% ^
 --key-pass pass:%KEYPASS% ^
 --out sample_re_signed.apk ^
 sample_re.apk

REM ================= 중간 파일 정리 =================
echo [*] Clean up temporary files
rmdir /s /q pgsHZz_unzip
rmdir /s /q sample_unzip

del /q inner.zip 2>nul
del /q pgsHZz_re.apk.idsig 2>nul
del /q pgsHZz_re-unsigned.apk 2>nul
del /q sample.zip 2>nul
del /q sample_re.apk 2>nul
del /q sample_re_signed.apk.idsig 2>nul
del /q test.keystore 2>nul

echo.
echo ==================================
echo   DONE : sample_re_signed.apk
echo ==================================
pause


