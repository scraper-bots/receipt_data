Receipt Data Scraper
This repository contains a Python script designed to automate the download of payment receipts from the monitoring.e-kassa.gov.az website, identified by unique fiscal IDs. The script is built to be resilient against network issues and server-side rate limiting, incorporating retry mechanisms and attempting to handle CSRF tokens.
Disclaimer: Please ensure that your use of this script complies with the website's terms of service and any applicable laws and regulations in your jurisdiction. Scraping government websites, especially those handling sensitive financial data, may have legal implications. It is highly recommended to explore official API access or data export options if available.
Table of Contents
Features
Repository Structure
Prerequisites
Installation
Usage
Configuration
Troubleshooting
Important Considerations
License
Features
Automated Receipt Download: Downloads JPEG images of receipts using provided fiscal IDs.
Robust Error Handling: Implements try-except blocks for network and HTTP errors.
Automatic Retries with Exponential Backoff: Automatically retries failed requests (timeouts, connection errors, server errors like 5xx, and Too Many Requests 429) with increasing delays to avoid overwhelming the server.
CSRF Token Handling: Attempts to fetch a CSRF token from the main website to simulate a more legitimate browser session.
Session Management: Uses requests.Session for efficient connection pooling and consistent header management.
Configurable Delays: Allows adjustment of delays between requests to manage server load.
Output Directory Management: Automatically creates a directory to save downloaded receipts.
Repository Structure
.
├── LICENSE
├── README.md
├── fiscal_ids.txt
├── main.py
├── receipts/
└── requirements.txt


LICENSE: The license file for the project.
README.md: This documentation file.
fiscal_ids.txt: A text file where you list all the fiscal IDs, one per line, that you want to scrape.
main.py: The main Python script for scraping receipts.
receipts/: The directory where all downloaded JPEG receipts will be saved. This directory will be created automatically if it doesn't exist.
requirements.txt: Lists the Python dependencies required to run the script.
Prerequisites
Before running the script, ensure you have the following installed:
Python 3.x
requests library: For making HTTP requests.
beautifulsoup4 library: For parsing HTML to extract the CSRF token.
urllib3: This is usually installed as a dependency of requests, but ensure it's up-to-date.
Installation
Clone the repository:
git clone https://github.com/Ismat-Samadov/receipt_data.git
cd receipt_data


Install dependencies:
It's recommended to use a virtual environment.
python -m venv venv
source venv/bin/activate  # On Windows: `venv\Scripts\activate`
pip install -r requirements.txt

If requirements.txt is not present, you can create it:
pip install requests beautifulsoup4 urllib3
pip freeze > requirements.txt


Usage
Prepare fiscal_ids.txt:
Create a file named fiscal_ids.txt in the root directory of the repository. Populate this file with the fiscal IDs you wish to download, with each ID on a new line.
Example fiscal_ids.txt:
Es6HZUh8kGx5
3G9bAk8wGhGF
AnotherFiscalID123
...


Run the script:
Execute the main.py script from your terminal:
python main.py


Monitor Output:
The script will print its progress to the console, including attempts to fetch the CSRF token, download attempts for each fiscal ID, and a summary of successful and failed downloads.
Access Downloaded Receipts:
Successfully downloaded JPEG receipts will be saved in the receipts/ directory, named after their respective fiscal IDs (e.g., Es6HZUh8kGx5.jpeg).
Configuration
You can customize the script's behavior by modifying the following variables at the top of main.py:
BASE_URL: The base URL for accessing receipts.
Default: "https://monitoring.e-kassa.gov.az/pks-monitoring/2.0.0/documents/"
FISCAL_IDS_FILE: The name of the file containing your fiscal IDs.
Default: "fiscal_ids.txt"
OUTPUT_DIR: The directory where downloaded receipts will be saved.
Default: "receipts"
REQUEST_DELAY_SECONDS: The delay in seconds between each request to the server. This is a "politeness" delay to avoid overwhelming the server.
Default: 2.0 (seconds).
Note: This delay is separate from the exponential backoff used during retries for failed requests. If you encounter frequent timeouts or blocks, consider increasing this value.
Troubleshooting
If you encounter issues such as Timeout occurred or Connection error, consider the following:
Increase REQUEST_DELAY_SECONDS: A higher delay (e.g., 5.0 or 10.0 seconds) can reduce the load on the server and make your requests less suspicious.
Check Network Connectivity:
Firewall: Ensure your local firewall (Windows Defender Firewall, iptables on Linux) is not blocking outbound connections to monitoring.e-kassa.gov.az on port 443.
Proxy: Verify if you are behind a proxy server. If so, ensure it's configured correctly for HTTPS traffic, or configure your script to use it. You might also need to explicitly bypass a local proxy if it's interfering.
DNS Resolution: Flush your DNS cache (ipconfig /flushdns on Windows, sudo systemd-resolve --flush-caches on Linux) and verify that monitoring.e-kassa.gov.az resolves to an IP address (nslookup monitoring.e-kassa.gov.az).
ISP/Regional Blocks: Use online tools (e.g., onlineornot.com, uptrends.com) to check if monitoring.e-kassa.gov.az is accessible from different geographical locations. If it's blocked only from your region, a VPN might help for diagnostic purposes.
CSRF Token: The script attempts to fetch a CSRF token. If it consistently fails to find one, the website's structure might have changed, or it might require a more complex authentication flow (e.g., a full login) to establish a valid session.
Server-Side Blocking: Government websites often employ sophisticated anti-scraping measures. Persistent issues may indicate that your IP address or request pattern is being actively blocked.
For a more in-depth guide on diagnosing network issues, please refer to the "Comprehensive Report on Resolving Connection Timeouts" document.
Important Considerations
Legality and Ethics: Always respect the website's robots.txt file (if present) and its terms of service. Scraping data from government portals, especially sensitive financial information, without explicit permission or official API access, can have legal consequences. It is strongly advised to seek official channels for data acquisition if you intend to process a large volume of receipts for business or analytical purposes.
Website Changes: Websites can change their structure, headers, or security measures at any time. This script may require updates if monitoring.e-kassa.gov.az undergoes significant changes.
Scalability: While the script includes retry logic, scraping 100,000 receipts is a large-scale operation. Be prepared for it to take a significant amount of time, even with optimized delays. Consider running it on a stable internet connection and a reliable machine.
License
This project is licensed under the LICENSE file.
