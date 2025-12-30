import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

MOBSF_URL = os.getenv("MOBSF_URL", "http://localhost").rstrip("/")
API_KEY = os.getenv("MOBSF_API_KEY")

if not API_KEY:
    raise SystemExit("❌ MOBSF_API_KEY가 비어있습니다. .env를 확인하세요.")

HEADERS = {"Authorization": API_KEY}


def api_post(path: str, **kwargs):
    url = f"{MOBSF_URL}{path}"
    r = requests.post(url, headers=HEADERS, timeout=120, **kwargs)
    r.raise_for_status()
    return r


def api_get(path: str, **kwargs):
    url = f"{MOBSF_URL}{path}"
    r = requests.get(url, headers=HEADERS, timeout=120, **kwargs)
    r.raise_for_status()
    return r


def upload_apk(apk_path: Path):
    with apk_path.open("rb") as f:
        files = {"file": (apk_path.name, f, "application/vnd.android.package-archive")}
        r = api_post("/api/v1/upload", files=files)
    return r.json()


def scan_apk(hash_value: str):
    # 업로드 결과의 hash를 넣어 스캔 트리거
    data = {"hash": hash_value}
    r = api_post("/api/v1/scan", data=data)
    return r.json()


def download_json_report(hash_value: str, out_path: Path):
    # JSON 리포트
    data = {"hash": hash_value}
    r = api_post("/api/v1/report_json", data=data)
    out_path.write_bytes(r.content)


def main():
    apk = Path("samples/sample.apk")  # 너가 넣을 APK 위치
    if not apk.exists():
        raise SystemExit(f"❌ APK 파일이 없습니다: {apk}\n   samples/sample.apk로 넣어주세요.")

    print(f"[1] Upload: {apk}")
    up = upload_apk(apk)
    # MobSF 업로드 응답은 버전에 따라 key명이 달라질 수 있어 안전 처리
    hash_value = up.get("hash") or up.get("md5") or up.get("scan_hash") or up.get("file_hash")
    if not hash_value:
        raise SystemExit(f"❌ 업로드 응답에서 hash를 못 찾음: {up}")

    print(f"    -> hash = {hash_value}")

    print("[2] Scan trigger")
    sc = scan_apk(hash_value)
    print(f"    -> scan response: {sc}")

    # 스캔이 비동기일 수 있어 잠깐 대기(환경에 따라 조정)
    print("[3] Wait 10s")
    time.sleep(10)

    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    out_json = out_dir / f"{apk.stem}_{hash_value}_report.json"

    print("[4] Download JSON report")
    download_json_report(hash_value, out_json)
    print(f"✅ Saved: {out_json}")


if __name__ == "__main__":
    main()

