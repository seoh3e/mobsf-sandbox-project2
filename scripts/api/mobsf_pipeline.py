import os
import time
import json
import csv
from pathlib import Path

import requests
from dotenv import load_dotenv

# -----------------------------
# Env
# -----------------------------
load_dotenv()

MOBSF_URL = os.getenv("MOBSF_URL", "http://localhost").rstrip("/")
API_KEY = os.getenv("MOBSF_API_KEY")

if not API_KEY:
    raise SystemExit("❌ MOBSF_API_KEY가 비어있습니다. .env를 확인하세요.")

HEADERS = {"Authorization": API_KEY}

# -----------------------------
# Paths
# -----------------------------
SAMPLES_DIR = Path("samples")
REPORTS_DIR = Path("reports")
OUTPUTS_DIR = Path("outputs")

# -----------------------------
# HTTP helpers
# -----------------------------
def api_post(path: str, **kwargs):
    url = f"{MOBSF_URL}{path}"
    r = requests.post(url, headers=HEADERS, timeout=180, **kwargs)
    r.raise_for_status()
    return r


def api_get(path: str, **kwargs):
    url = f"{MOBSF_URL}{path}"
    r = requests.get(url, headers=HEADERS, timeout=180, **kwargs)
    r.raise_for_status()
    return r


# -----------------------------
# MobSF API
# -----------------------------
def upload_apk(apk_path: Path) -> dict:
    with apk_path.open("rb") as f:
        files = {"file": (apk_path.name, f, "application/vnd.android.package-archive")}
        r = api_post("/api/v1/upload", files=files)
    return r.json()


def scan_apk(hash_value: str, file_name: str, scan_type: str = "apk") -> dict:
    """
    MobSF /api/v1/scan 은 환경/버전에 따라 요구 파라미터가 달라질 수 있어
    hash + scan_type + file_name 을 함께 보내도록 구성.
    """
    data = {
        "hash": hash_value,
        "scan_type": scan_type,
        "file_name": file_name,
    }
    r = api_post("/api/v1/scan", data=data)
    return r.json()


def download_json_report(hash_value: str, out_path: Path) -> None:
    data = {"hash": hash_value}
    r = api_post("/api/v1/report_json", data=data)
    out_path.write_bytes(r.content)


# -----------------------------
# Report summarize
# -----------------------------
def safe_str(v) -> str:
    return "" if v is None else str(v)


def extract_summary(report: dict) -> dict:
    appsec = report.get("appsec", {}) or {}
    return {
        "file_name": report.get("file_name"),
        "md5": report.get("md5"),
        "package_name": report.get("package_name"),
        "main_activity": report.get("main_activity"),
        "version_name": report.get("version_name"),
        "version_code": safe_str(report.get("version_code")),
        "target_sdk": safe_str(report.get("target_sdk")),
        "min_sdk": safe_str(report.get("min_sdk")),
        "max_sdk": safe_str(report.get("max_sdk")),
        "security_score": appsec.get("security_score"),
        "trackers": appsec.get("trackers"),
        "total_trackers": appsec.get("total_trackers"),
    }


def write_summaries(rows: list[dict]) -> None:
    OUTPUTS_DIR.mkdir(exist_ok=True)

    out_json = OUTPUTS_DIR / "summary.json"
    out_csv = OUTPUTS_DIR / "summary.csv"

    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = list(rows[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"✅ Saved: {out_json}")
    print(f"✅ Saved: {out_csv}")


# -----------------------------
# Pipeline
# -----------------------------
def pick_hash(upload_resp: dict) -> str | None:
    return (
        upload_resp.get("hash")
        or upload_resp.get("md5")
        or upload_resp.get("scan_hash")
        or upload_resp.get("file_hash")
    )


def run_one(apk: Path, wait_seconds: int = 10) -> Path:
    print(f"[1] Upload: {apk}")
    up = upload_apk(apk)

    hash_value = pick_hash(up)
    if not hash_value:
        raise SystemExit(f"❌ 업로드 응답에서 hash를 못 찾음: {up}")

    print(f"    -> hash = {hash_value}")

    print("[2] Scan trigger")
    sc = scan_apk(hash_value, file_name=apk.name, scan_type="apk")
    print(f"    -> scan response: {sc}")

    print(f"[3] Wait {wait_seconds}s")
    time.sleep(wait_seconds)

    REPORTS_DIR.mkdir(exist_ok=True)
    out_json = REPORTS_DIR / f"{apk.stem}_{hash_value}_report.json"

    print("[4] Download JSON report")
    download_json_report(hash_value, out_json)
    print(f"✅ Saved: {out_json}")

    return out_json


def iter_apks() -> list[Path]:
    if not SAMPLES_DIR.exists():
        return []
    return sorted(SAMPLES_DIR.glob("*.apk"))


def main():
    # 0) Inputs
    apks = iter_apks()
    if not apks:
        raise SystemExit(
            "❌ samples/ 폴더에 *.apk가 없습니다.\n"
            "   예) samples/sample.apk 로 넣고 다시 실행하세요."
        )

    # 1) Run pipeline for all APKs
    report_paths: list[Path] = []
    for apk in apks:
        print("\n" + "=" * 60)
        try:
            rp = run_one(apk, wait_seconds=10)
            report_paths.append(rp)
        except requests.HTTPError as e:
            # 서버 응답 바디가 있으면 같이 출력
            body = ""
            try:
                body = e.response.text if e.response is not None else ""
            except Exception:
                body = ""
            print(f"❌ HTTPError on {apk.name}: {e}")
            if body:
                print(f"    response: {body[:500]}")
        except Exception as e:
            print(f"❌ Failed on {apk.name}: {e}")

    if not report_paths:
        raise SystemExit("❌ 생성된 report가 없습니다. 위 에러 로그를 확인하세요.")

    # 2) Summarize
    rows: list[dict] = []
    for rp in report_paths:
        try:
            report = json.loads(rp.read_text(encoding="utf-8"))
            rows.append(extract_summary(report))
        except Exception as e:
            print(f"⚠️  요약 실패: {rp.name} ({e})")

    if not rows:
        raise SystemExit("❌ 요약할 데이터가 없습니다. reports/*.json 내용을 확인하세요.")

    write_summaries(rows)
    print("\n✅ DONE: scan reports + outputs summary generated.")


if __name__ == "__main__":
    main()
