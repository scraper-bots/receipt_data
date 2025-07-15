import requests
import os
import time
from bs4 import BeautifulSoup # Import BeautifulSoup for HTML parsing

# --- Configuration ---
# Base URL for the receipts
BASE_URL = "https://monitoring.e-kassa.gov.az/pks-monitoring/2.0.0/documents/"

# Input file containing fiscal IDs (one ID per line)
FISCAL_IDS_FILE = "fiscal_ids.txt"

# Output directory to save the downloaded receipts
OUTPUT_DIR = "receipts"

# Delay in seconds between each request to avoid rate limiting
# Increased this value significantly to reduce load on the server and prevent timeouts
REQUEST_DELAY_SECONDS = 2.0 # Adjust this value if you encounter issues (e.g., 0.5 or 1.0)

# Headers to mimic a browser request
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Host": "monitoring.e-kassa.gov.az",
    "Referer": "https://monitoring.e-kassa.gov.az/", # Important: Mimic the referrer
    "Sec-Ch-Ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "User-Lang": "az",
    "User-Time-Zone": "Asia/Baku",
    "X-Csrf-Token": "", # This will be dynamically updated
}

# --- Script Logic ---

def create_output_directory(directory):
    """Creates the output directory if it doesn't exist."""
    os.makedirs(directory, exist_ok=True)
    print(f"Ensured output directory '{directory}' exists.")

def get_csrf_token(main_url, headers):
    """
    Attempts to fetch the CSRF token from the main website.
    This simulates visiting the page to get a valid token.
    """
    print(f"Attempting to fetch CSRF token from: {main_url}")
    try:
        # Make a GET request to the main page to get the HTML content
        response = requests.get(main_url, headers=headers, timeout=15)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for a meta tag or input field that might contain the CSRF token
        # Common patterns: <meta name="csrf-token" content="..."> or <input type="hidden" name="_csrf" value="...">
        csrf_meta = soup.find('meta', attrs={'name': 'csrf-token'})
        if csrf_meta and 'content' in csrf_meta.attrs:
            token = csrf_meta['content']
            print(f"Found CSRF token from meta tag: {token[:10]}...") # Print first 10 chars for brevity
            return token

        csrf_input = soup.find('input', attrs={'name': '_csrf'})
        if csrf_input and 'value' in csrf_input.attrs:
            token = csrf_input['value']
            print(f"Found CSRF token from input field: {token[:10]}...")
            return token

        print("CSRF token not found on the main page. Proceeding without it.")
        return "" # Return empty if not found
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CSRF token from {main_url}: {e}")
        return "" # Return empty on error

def read_fiscal_ids(file_path):
    """Reads fiscal IDs from a text file, one per line."""
    fiscal_ids = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                fiscal_ids.append(line.strip())
        print(f"Successfully read {len(fiscal_ids)} fiscal IDs from '{file_path}'.")
    except FileNotFoundError:
        print(f"Error: Fiscal IDs file '{file_path}' not found. Please create it.")
        exit()
    return fiscal_ids

def download_receipt(fiscal_id, output_dir, headers, delay):
    """Downloads a single receipt and saves it to the specified directory."""
    url = f"{BASE_URL}{fiscal_id}"
    file_path = os.path.join(output_dir, f"{fiscal_id}.jpeg")

    if os.path.exists(file_path):
        print(f"Skipping {fiscal_id}: File already exists at '{file_path}'.")
        return True # Consider it successful if already downloaded

    try:
        print(f"Attempting to download: {url}")
        # Increased timeout to 30 seconds to give the server more time to respond
        response = requests.get(url, headers=headers, stream=True, timeout=30)

        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Successfully downloaded: {fiscal_id} to '{file_path}'")
            return True
        else:
            print(f"Failed to download {fiscal_id}: Status Code {response.status_code}, URL: {url}")
            return False
    except requests.exceptions.Timeout:
        print(f"Timeout occurred while downloading {fiscal_id} from {url}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading {fiscal_id} from {url}: {e}")
        return False
    finally:
        # Always add a delay, even if there was an error, to prevent rapid retries
        time.sleep(delay)

def main():
    create_output_directory(OUTPUT_DIR)

    # Get CSRF token before starting downloads
    csrf_token = get_csrf_token(HEADERS["Referer"], HEADERS)
    if csrf_token:
        HEADERS["X-Csrf-Token"] = csrf_token
    else:
        print("Warning: Could not obtain CSRF token. Downloads might still fail.")

    fiscal_ids = read_fiscal_ids(FISCAL_IDS_FILE)

    if not fiscal_ids:
        print("No fiscal IDs found to process. Exiting.")
        return

    successful_downloads = 0
    failed_downloads = 0

    for i, fiscal_id in enumerate(fiscal_ids):
        print(f"\nProcessing {i+1}/{len(fiscal_ids)}: {fiscal_id}")
        if download_receipt(fiscal_id, OUTPUT_DIR, HEADERS, REQUEST_DELAY_SECONDS):
            successful_downloads += 1
        else:
            failed_downloads += 1

    print("\n--- Download Summary ---")
    print(f"Total IDs processed: {len(fiscal_ids)}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")
    print(f"Receipts saved to: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    main()