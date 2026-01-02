#!/bin/bash
set -e

# ================= 설정 =================
KEYSTORE="test.keystore"
KEYALIAS="testkey"
STOREPASS="pgsHZz"
KEYPASS="pgsHZz"

SAMPLE_APK="sample.apk"
INNER_APK="pgsHZz.apk"

# ================= sample.apk 압축 해제 =================
echo "[*] Unzip sample.apk"
rm -rf sample_unzip
mkdir sample_unzip

cd sample_unzip
jar xf "../${SAMPLE_APK}"
cd ..

# ================= 내부 APK 압축 해제 =================
echo "[*] Unzip inner apk"
rm -rf pgsHZz_unzip
mkdir pgsHZz_unzip

cd pgsHZz_unzip
jar xf "../sample_unzip/assets/${INNER_APK}"
cd ..

# ================= DEX 복호화 =================
echo "[*] Decrypt dex"
python3 decrypt_dex.py

# ================= 내부 APK 재압축 =================
echo "[*] Repack inner apk"
rm -f pgsHZz_re-unsigned.apk

cd pgsHZz_unzip
jar cf ../pgsHZz_re-unsigned.apk *
cd ..

# ================= keystore 생성 =================
if [ ! -f "${KEYSTORE}" ]; then
    echo "[*] Generate keystore"
    keytool -genkey -v \
     -keystore "${KEYSTORE}" \
     -alias "${KEYALIAS}" \
     -keyalg RSA \
     -keysize 2048 \
     -validity 10000 \
     -storepass "${STOREPASS}" \
     -keypass "${KEYPASS}" \
     -dname "CN=pgsHZz, OU=pgsHZz, O=pgsHZz, L=Seoul, S=Seoul, C=KR"
fi

# ================= 내부 APK 서명 =================
echo "[*] Sign inner apk"
apksigner sign \
 --ks "${KEYSTORE}" \
 --ks-key-alias "${KEYALIAS}" \
 --ks-pass pass:"${STOREPASS}" \
 --key-pass pass:"${KEYPASS}" \
 --out pgsHZz_re.apk \
 pgsHZz_re-unsigned.apk

# ================= 내부 APK 교체 =================
echo "[*] Replace inner apk"
rm -f "sample_unzip/assets/${INNER_APK}"
cp pgsHZz_re.apk "sample_unzip/assets/${INNER_APK}"

# ================= sample.apk 재압축 =================
echo "[*] Repack sample apk"
rm -f sample_re.apk

cd sample_unzip
jar cf ../sample_re.apk *
cd ..

# ================= sample.apk 서명 =================
echo "[*] Sign sample apk"
apksigner sign \
 --ks "${KEYSTORE}" \
 --ks-key-alias "${KEYALIAS}" \
 --ks-pass pass:"${STOREPASS}" \
 --key-pass pass:"${KEYPASS}" \
 --out sample_re_signed.apk \
 sample_re.apk

# ================= 중간 파일 정리 =================
echo "[*] Clean up temporary files"
rm -rf pgsHZz_unzip
rm -rf sample_unzip

rm -f inner.zip
rm -f pgsHZz_re.apk.idsig
rm -f pgsHZz_re-unsigned.apk
rm -f sample.zip
rm -f sample_re.apk
rm -f sample_re_signed.apk.idsig
rm -f test.keystore

echo
echo "=================================="
echo "  DONE : sample_re_signed.apk"
echo "=================================="

read -p "Press Enter to exit..."
