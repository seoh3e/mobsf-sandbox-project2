import json
from pathlib import Path
import csv

REPORTS_DIR = Path("reports")
OUTPUTS_DIR = Path("outputs")
OUT_CSV = OUTPUTS_DIR / "summary.csv"
OUT_JSON = OUTPUTS_DIR / "summary.json"

def extract_summary(report: dict) -> dict:
    appsec = report.get("appsec", {}) or {}
    return {
        "file_name": report.get("file_name"),
        "md5": report.get("md5"),
        "package_name": report.get("package_name"),
        "main_activity": report.get("main_activity"),
        "version_name": report.get("version_name"),
        "version_code": str(report.get("version_code") or ""),
        "target_sdk": str(report.get("target_sdk") or ""),
        "min_sdk": str(report.get("min_sdk") or ""),
        "max_sdk": str(report.get("max_sdk") or ""),
        "security_score": appsec.get("security_score"),
        "trackers": appsec.get("trackers"),
        "total_trackers": appsec.get("total_trackers"),
    }

def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for p in sorted(REPORTS_DIR.glob("*_report.json")):
        with p.open("r", encoding="utf-8") as f:
            report = json.load(f)
        rows.append(extract_summary(report))

    if not rows:
        print("[ERROR] reports/에 *_report.json 이 없습니다.")
        return

    # JSON
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV
    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"[OK] Saved: {OUT_JSON}")
    print(f"[OK] Saved: {OUT_CSV}")

if __name__ == "__main__":
    main()
