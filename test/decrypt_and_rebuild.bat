@echo off
setlocal

REM ===== 설정 =====
set KEYSTORE=test.keystore
set KEYALIAS=testkey
set STOREPASS=pgsHZz
set KEYPASS=pgsHZz

REM ===== APK 추출 =====
copy sample.apk sample.zip

powershell -Command "Expand-Archive -Force sample.zip -DestinationPath sample_unzip"

java -jar apktool_2.12.1.jar d sample_unzip\assets\pgsHZz.apk -o pgsHZz_re

copy sample_unzip\assets\pgsHZz.apk pgsHZz.zip

powershell -Command "Expand-Archive -Force pgsHZz.zip -DestinationPath pgsHZz_unzip"

REM ===== DEX 복호화 =====
python decrypt_dex.py

REM ===== smali 변환 =====
java -jar baksmali-3.0.9-fat-release.jar d pgsHZz_unzip\kill-classes-decrypted.dex -o pgsHZz_re\smali
java -jar baksmali-3.0.9-fat-release.jar d pgsHZz_unzip\kill-classes2-decrypted.dex -o pgsHZz_re\smali_classes2

REM ===== APK 빌드 =====
java -jar apktool_2.12.1.jar b pgsHZz_re -o pgsHZz_re-unsigned.apk

REM ===== keystore 생성 (없을 때만) =====
if not exist %KEYSTORE% (
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

REM ===== APK 서명 =====
apksigner sign ^
 --ks %KEYSTORE% ^
 --ks-key-alias %KEYALIAS% ^
 --ks-pass pass:%STOREPASS% ^
 --key-pass pass:%KEYPASS% ^
 --out pgsHZz_re.apk ^
 pgsHZz_re-unsigned.apk
