#!/usr/bin/env python3
"""
Pull every applicant for each job ID in JOB_IDS from JazzHR and save:
  • all_applicants.json  – the raw array returned by the API
  • all_applicants.csv   – a flat table with one row per applicant
"""
import csv, json, os, time, requests
from typing import List

API_KEY   = "WiLMftah0GxVrO3PAo4DJEqGCyXcRksr"          # export JAZZHR_API_KEY=xxxx
BASE_URL  = "https://api.resumatorapi.com/v1"
# JOB_IDS   = ["112233", "556677", "998877"]       # ← put your job IDs here
PAGE_WAIT = 0.25                                 # seconds between API calls

# ---- read IDs from an external file --------------------
with open("elevated_job_ids.txt", encoding="utf-8") as f:
    JOB_IDS = [line.strip() for line in f if line.strip()]
# --------------------------------------------------------


def fetch_job_applicants(job_id: str) -> List[dict]:
    """Return a list of every applicant for one job_id, paging as needed."""
    rows, page = [], 1
    headers = {"X-Api-Key": API_KEY}

    while True:
        url = f"{BASE_URL}/applicants?job_id={job_id}/page/{page}"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        batch = resp.json()          # [] when no more pages

        if not batch:
            break

        for rec in batch:
            rec["job_id"] = job_id   # keep the source job
        rows.extend(batch)

        page += 1
        time.sleep(PAGE_WAIT)

    return rows


def main() -> None:
    if not API_KEY:
        raise SystemExit("❌  Set JAZZHR_API_KEY in your environment first.")

    merged: List[dict] = []
    for jid in JOB_IDS:
        print(f"↳ fetching job {jid}")
        merged.extend(fetch_job_applicants(jid))

    # ---------- JSON -------------------------------------------------------
    json_path = "all_applicants.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    print(f"✅  {len(merged):,} applicants → {json_path}")

    # ---------- CSV --------------------------------------------------------
    if merged:
        # a superset of every key that appears in any record
        fieldnames = sorted({k for rec in merged for k in rec})
        csv_path = "all_applicants.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(merged)

        print(f"✅  same data (tabular)  → {csv_path}")


if __name__ == "__main__":
    main()
