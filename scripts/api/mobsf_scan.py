# scripts/api/mobsf_scan.py
from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv


def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}. Check your .env")
    return v


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def mobsf_headers(api_key: str) -> Dict[str, str]:
    # MobSF REST API uses "Authorization" header
    return {"Authorization": api_key}


def upload_file(mobsf_url: str, api_key: str, apk_path: Path) -> Dict[str, Any]:
    url = mobsf_url.rstrip("/") + "/api/v1/upload"
    with apk_path.open("rb") as f:
        files = {"file": (apk_path.name, f, "application/vnd.android.package-archive")}
        r = requests.post(url, headers=mobsf_headers(api_key), files=files, timeout=120)
    r.raise_for_status()
    return r.json()


def scan_file(mobsf_url: str, api_key: str, file_name: str, scan_type: str = "apk") -> Dict[str, Any]:
    url = mobsf_url.rstrip("/") + "/api/v1/scan"
    data = {"scan_type": scan_type, "file_name": file_name}
    r = requests.post(url, headers=mobsf_headers(api_key), data=data, timeout=120)
    r.raise_for_status()
    return r.json()


def get_json_report(mobsf_url: str, api_key: str, hash_: str, report_type: str = "apk") -> Dict[str, Any]:
    url = mobsf_url.rstrip("/") + "/api/v1/report_json"
    data = {"hash": hash_, "type": report_type}
    r = requests.post(url, headers=mobsf_headers(api_key), data=data, timeout=120)
    r.raise_for_status()
    return r.json()


def download_pdf_report(mobsf_url: str, api_key: str, hash_: str, report_type: str = "apk") -> bytes:
    url = mobsf_url.rstrip("/") + "/api/v1/download_pdf"
    data = {"hash": hash_, "type": report_type}
    r = requests.post(url, headers=mobsf_headers(api_key), data=data, timeout=300)
    r.raise_for_status()
    return r.content


def main() -> None:
    # Load .env from project root (works even when executed from elsewhere)
    project_root = Path(__file__).resolve().parents[2]  # .../mobsf-sandbox-project2
    load_dotenv(project_root / ".env")

    mobsf_url = require_env("MOBSF_URL")
    api_key = require_env("MOBSF_API_KEY")

    # Default: samples/sample.apk (you can pass another path via CLI later if you want)
    apk_path = project_root / "samples" / "sample.apk"
    if not apk_path.exists():
        raise FileNotFoundError(
            f"APK not found: {apk_path}\n"
            f"Put your APK at that path, or edit apk_path in this script."
        )

    out_dir = project_root / "outputs" / f"{apk_path.stem}_{int(time.time())}"
    ensure_dir(out_dir)

    print(f"[1/4] Uploading: {apk_path}")
    up = upload_file(mobsf_url, api_key, apk_path)
    # Expected keys: file_name, hash, scan_type (varies by build)
    file_name = up.get("file_name") or up.get("filename") or apk_path.name
    hash_ = up.get("hash") or up.get("md5")  # MobSF usually returns "hash" = md5
    if not hash_:
        raise RuntimeError(f"Upload response missing hash/md5: {up}")

    print(f"      file_name={file_name}")
    print(f"      hash(md5)={hash_}")

    print("[2/4] Triggering scan...")
    scan = scan_file(mobsf_url, api_key, file_name=file_name, scan_type="apk")
    # scan response often includes: scan_type, hash, file_name
    print("      scan triggered OK")

    print("[3/4] Fetching JSON report...")
    report = get_json_report(mobsf_url, api_key, hash_=hash_, report_type="apk")
    json_path = out_dir / "report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      saved: {json_path}")

    print("[4/4] Downloading PDF report...")
    pdf_bytes = download_pdf_report(mobsf_url, api_key, hash_=hash_, report_type="apk")
    pdf_path = out_dir / "report.pdf"
    pdf_path.write_bytes(pdf_bytes)
    print(f"      saved: {pdf_path}")

    print("\nDONE.")
    print(f"Outputs: {out_dir}")


if __name__ == "__main__":
    main()
