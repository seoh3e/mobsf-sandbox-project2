#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MobSF 자동화: APK 업로드 → 스캔 → PDF 리포트 다운로드 (Windows/맥/리눅스)

사전조건
- MobSF 서버 실행 중 (기본: http://127.0.0.1:8000)
- PDF 생성용 wkhtmltopdf 설치 + PATH 등록 (MobSF가 실행되는 환경에서 인식되어야 함)
- Python 패키지: requests
  python -m pip install requests

사용 예시 (Windows CMD)
  set "MOBSF_APIKEY=여기에_APIKEY(공백/괄호 없이)"
  python mobsf_auto_pdf.py "%USERPROFILE%\\Desktop\\sample.apk" --out "%USERPROFILE%\\Desktop\\sample_report.pdf"

참고
- 헤더는 기본적으로 X-Mobsf-Api-Key 를 사용합니다.
  (필요 시 --header-mode auth 로 Authorization 헤더로 전환 가능)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, Tuple

import requests


def sanitize_apikey(raw: str) -> str:
    """
    Windows 콘솔/복사-붙여넣기 과정에서 '키:', '<>', 공백 등이 섞여 401/Unicode 문제가 나는 케이스 방지.
    MobSF API key는 보통 hex 문자열이므로 hex만 남깁니다.
    """
    if raw is None:
        return ""
    raw = raw.strip()
    # '<...>' 형태로 붙여넣은 경우 제거
    raw = raw.strip("<>").strip()
    # hex만 유지
    cleaned = re.sub(r"[^0-9a-fA-F]", "", raw)
    return cleaned.strip()


def build_headers(apikey: str, header_mode: str) -> Dict[str, str]:
    """
    header_mode:
      - "x"   : X-Mobsf-Api-Key (권장)
      - "auth": Authorization
    """
    if header_mode == "auth":
        return {"Authorization": apikey}
    # default
    return {"X-Mobsf-Api-Key": apikey}


def api_post(
    url: str,
    headers: Dict[str, str],
    *,
    data=None,
    files=None,
    stream: bool = False,
    timeout: int = 600,
) -> requests.Response:
    # requests가 헤더를 latin-1로 인코딩하려고 해서, 혹시 모를 Unicode 섞임 방지
    safe_headers = {k: v.encode("ascii", "ignore").decode("ascii") for k, v in headers.items()}
    return requests.post(url, headers=safe_headers, data=data, files=files, stream=stream, timeout=timeout)


def upload(server: str, apikey: str, apk_path: Path, header_mode: str) -> Dict:
    url = f"{server}/api/v1/upload"
    headers = build_headers(apikey, header_mode)

    with apk_path.open("rb") as f:
        files = {"file": (apk_path.name, f, "application/vnd.android.package-archive")}
        r = api_post(url, headers, files=files, timeout=300)

    if r.status_code != 200:
        raise RuntimeError(f"upload failed: HTTP {r.status_code} / {r.text[:300]}")
    return r.json()


def scan(server: str, apikey: str, scan_type: str, file_name: str, scan_hash: str, header_mode: str) -> Dict:
    url = f"{server}/api/v1/scan"
    headers = build_headers(apikey, header_mode)
    data = {"scan_type": scan_type, "file_name": file_name, "hash": scan_hash}
    r = api_post(url, headers, data=data, timeout=900)

    if r.status_code != 200:
        raise RuntimeError(f"scan failed: HTTP {r.status_code} / {r.text[:300]}")
    # scan API는 json을 주는 경우가 대부분
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}


def download_pdf(server: str, apikey: str, scan_type: str, scan_hash: str, out_pdf: Path, header_mode: str) -> Tuple[int, int]:
    """
    Returns (http_status, bytes_written)
    """
    url = f"{server}/api/v1/download_pdf"
    headers = build_headers(apikey, header_mode)
    data = {"hash": scan_hash, "scan_type": scan_type}

    r = api_post(url, headers, data=data, stream=True, timeout=900)

    if r.status_code != 200:
        # MobSF는 에러를 JSON으로 주는 경우가 있음
        raise RuntimeError(f"download_pdf failed: HTTP {r.status_code} / {r.text[:500]}")

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_pdf.open("wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 128):
            if chunk:
                f.write(chunk)
                written += len(chunk)
    return (r.status_code, written)


def run_once(server: str, apikey: str, apk_path: Path, out_pdf: Path, header_mode: str) -> None:
    print(f"[1/3] Upload: {apk_path}")
    up = upload(server, apikey, apk_path, header_mode)

    scan_hash = up.get("hash") or up.get("scan_hash")
    scan_type = up.get("scan_type") or "apk"
    file_name = up.get("file_name") or apk_path.name

    if not scan_hash:
        raise RuntimeError(f"upload 응답에서 hash를 찾지 못했습니다: {up}")

    print(f"[2/3] Scan : type={scan_type} file={file_name} hash={scan_hash}")
    _ = scan(server, apikey, scan_type, file_name, scan_hash, header_mode)

    print(f"[3/3] PDF  : {out_pdf}")
    status, size = download_pdf(server, apikey, scan_type, scan_hash, out_pdf, header_mode)
    print(f"[DONE] HTTP={status} bytes={size}  ->  {out_pdf}")


def main() -> None:
    p = argparse.ArgumentParser(description="MobSF APK -> PDF 자동화")
    p.add_argument("apk", help="분석할 APK 경로")
    p.add_argument("--server", default="http://127.0.0.1:8000", help="MobSF 서버 주소 (기본: http://127.0.0.1:8000)")
    p.add_argument("--apikey", default="", help="MobSF REST API Key (미지정 시 환경변수 MOBSF_APIKEY 사용)")
    p.add_argument("--out", default="", help="저장할 PDF 경로 (미지정 시 <apk이름>_report.pdf)")
    p.add_argument("--header-mode", choices=["x", "auth"], default="x", help="API Key 헤더 방식 (기본: x)")
    p.add_argument("--retry-auth", action="store_true", help="401이면 Authorization 헤더로 자동 재시도")

    args = p.parse_args()

    apk_path = Path(args.apk).expanduser().resolve()
    if not apk_path.exists():
        raise SystemExit(f"APK 파일이 없습니다: {apk_path}")

    apikey_raw = args.apikey.strip() or os.environ.get("MOBSF_APIKEY", "")
    apikey = sanitize_apikey(apikey_raw)
    if not apikey:
        raise SystemExit('APIKEY가 비었습니다. --apikey 를 주거나 환경변수 MOBSF_APIKEY 를 설정하세요.')

    out_pdf = Path(args.out).expanduser().resolve() if args.out else apk_path.with_name(f"{apk_path.stem}_report.pdf")

    # 1차 시도
    try:
        run_once(args.server.rstrip("/"), apikey, apk_path, out_pdf, args.header_mode)
        return
    except RuntimeError as e:
        msg = str(e)
        if args.retry_auth and "HTTP 401" in msg and args.header_mode != "auth":
            print("[WARN] 401 발생. Authorization 헤더로 재시도합니다.")
            run_once(args.server.rstrip("/"), apikey, apk_path, out_pdf, "auth")
            return
        raise


if __name__ == "__main__":
    main()
