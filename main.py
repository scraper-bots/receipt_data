#!/usr/bin/env python3
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Configuration ---
BASE_URL             = "https://monitoring.e-kassa.gov.az/pks-monitoring/2.0.0/documents/"
FISCAL_IDS_FILE      = "fiscal_ids.txt"
OUTPUT_DIR           = "receipts"
REQUEST_DELAY_SECONDS= 2.0     # pause between requests
TIMEOUT              = (5, 30) # (connect timeout, read timeout)
MAX_RETRIES          = 3       # total attempts (incl. first try + retries)
BACKOFF_FACTOR       = 0.5     # exponential backoff factor for retries

HEADERS = {
    "Accept":             "image/jpeg,image/png,*/*",
    "Accept-Encoding":    "gzip, deflate, br",
    "Accept-Language":    "en-US,en;q=0.9",
    "Connection":         "keep-alive",
    "Host":               "monitoring.e-kassa.gov.az",
    "Referer":            "https://monitoring.e-kassa.gov.az/",
    "Sec-Fetch-Dest":     "image",
    "Sec-Fetch-Mode":     "cors",
    "Sec-Fetch-Site":     "same-origin",
    "User-Agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                          " AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/137.0.0.0 Safari/537.36",
    "User-Lang":          "az",
    "User-Time-Zone":     "Asia/Baku",
}

# --- Helpers ---
def ensure_output_dir(path):
    os.makedirs(path, exist_ok=True)
    print(f"✔️  Ensured output directory: {path}")

def load_fiscal_ids(path):
    try:
        with open(path, "r") as f:
            ids = [line.strip() for line in f if line.strip()]
        print(f"✔️  Loaded {len(ids)} fiscal IDs from `{path}`")
        return ids
    except FileNotFoundError:
        print(f"❌  File not found: `{path}`")
        exit(1)

def create_session():
    """Return a `requests.Session` with retry/backoff configured."""
    session = requests.Session()
    retries = Retry(
        total=MAX_RETRIES - 1,               # retries _after_ first attempt
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session

def download_receipt(session, fid):
    url = f"{BASE_URL}{fid}"
    out_path = os.path.join(OUTPUT_DIR, f"{fid}.jpeg")

    if os.path.exists(out_path):
        print(f"→ Skipping {fid}: already exists")
        return True

    try:
        resp = session.get(url, timeout=TIMEOUT, stream=True)
        status = resp.status_code

        if status == 200:
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            print(f"✅ [{status}] Downloaded `{fid}.jpeg`")
            return True

        # non-recoverable errors
        print(f"❌ [{status}] Failed for {fid} (no retry)")
        return False

    except requests.exceptions.ConnectTimeout:
        print(f"⚠️  [ConnectTimeout] {fid}")
    except requests.exceptions.ReadTimeout:
        print(f"⚠️  [ReadTimeout] {fid}")
    except requests.exceptions.RequestException as e:
        print(f"❌ [Error] {fid}: {e}")

    return False

def main():
    ensure_output_dir(OUTPUT_DIR)
    fiscal_ids = load_fiscal_ids(FISCAL_IDS_FILE)
    session = create_session()

    total = len(fiscal_ids)
    succ = fail = 0

    for idx, fid in enumerate(fiscal_ids, start=1):
        print(f"\n[{idx}/{total}] Processing: {fid}")
        if download_receipt(session, fid):
            succ += 1
        else:
            fail += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    # Summary
    print("\n--- Download Summary ---")
    print(f"Total IDs: {total}")
    print(f"Successful: {succ}")
    print(f"Failed: {fail}")
    print(f"Receipts directory: {os.path.abspath(OUTPUT_DIR)}\n")

if __name__ == "__main__":
    main(