@echo off

copy sample.apk sample.zip

powershell -Command "Expand-Archive -Force sample.zip -DestinationPath sample_unzip"

java -jar apktool_2.12.1.jar d sample_unzip\assets\pgsHZz.apk -o pgsHZz_re

copy sample_unzip\assets\pgsHZz.apk pgsHZz.zip

powershell -Command "Expand-Archive -Force pgsHZz.zip -DestinationPath pgsHZz_unzip"

python decrypt_dex.py

java -jar baksmali-3.0.9-fat-release.jar d pgsHZz_unzip\kill-classes-decrypted.dex -o pgsHZz_re\smali_kill-classes
java -jar baksmali-3.0.9-fat-release.jar d pgsHZz_unzip\kill-classes2-decrypted.dex -o pgsHZz_re\smali_kill-classes2

java -jar apktool_2.12.1.jar b pgsHZz_re -o pgsHZz_re.apk

if exist sample.zip del /f /q sample.zip
if exist pgsHZz.zip del /f /q pgsHZz.zip

if exist sample_unzip rmdir /s /q sample_unzip
if exist pgsHZz_unzip rmdir /s /q pgsHZz_unzip
if exist pgsHZz_re rmdir /s /q pgsHZz_re
