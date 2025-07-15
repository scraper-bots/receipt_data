import requests
import os
from tqdm import tqdm

# Constants
BASE_URL = "https://monitoring.e-kassa.gov.az/pks-monitoring/2.0.0/documents/"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "connection": "keep-alive",
    "host": "monitoring.e-kassa.gov.az",
    "referer": "https://monitoring.e-kassa.gov.az/",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "user-lang": "az",
    "user-time-zone": "Asia/Baku"
}

# Optional: Add CSRF token if required
# HEADERS['x-csrf-token'] = "your_token_here"

# Read fiscal IDs
with open("fiscal_ids.txt", "r") as file:
    fiscal_ids = [line.strip() for line in file.readlines() if line.strip()]

# Ensure output directory exists
output_dir = "receipts"
os.makedirs(output_dir, exist_ok=True)

# Download loop
for fid in tqdm(fiscal_ids, desc="Downloading Receipts"):
    try:
        url = BASE_URL + fid
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 200 and response.headers["content-type"] == "image/jpeg":
            with open(os.path.join(output_dir, f"{fid}.jpg"), "wb") as f:
                f.write(response.content)
        else:
            print(f"⚠️ Failed for {fid}: Status {response.status_code}, Content-Type {response.headers.get('content-type')}")

    except Exception as e:
        print(f"❌ Error fetching {fid}: {str(e)}")
