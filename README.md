# Receipt Data Scraper

This repository contains a Python script designed to automate the download of payment receipts from the [monitoring.e-kassa.gov.az](https://monitoring.e-kassa.gov.az) website, identified by unique fiscal IDs. The script is resilient against network issues and server-side rate limiting, incorporating retry mechanisms and handling CSRF tokens where possible.

> ⚠️ **Disclaimer**: Ensure that your use of this script complies with the website's terms of service and any applicable laws in your jurisdiction. Scraping government websites, especially those involving sensitive financial data, may have legal implications. Official API or export options should be preferred where available.

---

## 📑 Table of Contents

- [Features](#features)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Important Considerations](#important-considerations)
- [License](#license)

---

## ✅ Features

- **Automated Receipt Download**: Retrieves JPEG images of receipts by fiscal ID.
- **Robust Error Handling**: Gracefully handles network, HTTP, and timeout issues.
- **Retry Mechanism**: Implements exponential backoff for recoverable errors (timeouts, 429, 5xx).
- **CSRF Token Handling**: Simulates browser behavior by acquiring a CSRF token.
- **Session Reuse**: Utilizes `requests.Session` for efficient HTTP management.
- **Politeness Delay**: Configurable delay between requests to reduce server load.
- **Auto Directory Management**: Creates an output directory for saved receipts.

---

## 📁 Repository Structure

```

.
├── LICENSE
├── README.md
├── fiscal\_ids.txt
├── scraper.py
├── receipts/
└── requirements.txt

````

- **`LICENSE`**: License for this repository.
- **`README.md`**: This documentation file.
- **`fiscal_ids.txt`**: List of fiscal IDs (one per line) to fetch receipts.
- **`scraper.py`**: Main script to download receipts.
- **`receipts/`**: Output directory (auto-created).
- **`requirements.txt`**: Python dependencies.

---

## ⚙️ Prerequisites

- Python 3.7 or higher
- pip package manager

Required libraries:
- `requests`
- `beautifulsoup4`
- `urllib3` (dependency of requests)

---

## 🔧 Installation

1. **Clone the Repository**:

```bash
git clone https://github.com/Ismat-Samadov/receipt_data.git
cd receipt_data
````

2. **Create and Activate a Virtual Environment** *(Optional but recommended)*:

```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**:

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, generate it with:

```bash
pip install requests beautifulsoup4 urllib3
pip freeze > requirements.txt
```

---

## 🚀 Usage

1. **Prepare Your Fiscal IDs**:

Create a `fiscal_ids.txt` file and populate it with one fiscal ID per line.

Example:

```
Es6HZUh8kGx5
3G9bAk8wGhGF
AnotherFiscalID123
```

2. **Run the Script**:

```bash
python scraper.py
```

3. **View the Output**:

Downloaded receipts will appear in the `receipts/` directory, named after their fiscal ID (e.g., `Es6HZUh8kGx5.jpeg`).

---

## ⚙️ Configuration

Edit these variables in `scraper.py` to adjust functionality:

```python
BASE_URL = "https://monitoring.e-kassa.gov.az/pks-monitoring/2.0.0/documents/"
FISCAL_IDS_FILE = "fiscal_ids.txt"
OUTPUT_DIR = "receipts"
REQUEST_DELAY_SECONDS = 2.0  # Adjust to 5.0 or 10.0 if rate-limited
```

* **BASE\_URL**: Endpoint for receipt retrieval.
* **FISCAL\_IDS\_FILE**: Input text file of fiscal IDs.
* **OUTPUT\_DIR**: Output folder for JPEGs.
* **REQUEST\_DELAY\_SECONDS**: Fixed delay between requests.

---

## 🛠️ Troubleshooting

If errors persist, here are some suggestions:

### 🔁 Retry / Rate Limit Errors (429, 504, timeouts):

* Increase `REQUEST_DELAY_SECONDS` to 5 or 10 seconds.
* Run the script during off-peak hours.

### 🌐 Network Connectivity Issues:

* **Firewall**: Ensure port 443 is open.
* **Proxy**: Confirm proxy settings if using one.
* **DNS**: Try flushing cache:

```bash
# Windows
ipconfig /flushdns

# Linux
sudo systemd-resolve --flush-caches
```

### 🌍 Regional Blocks or IP Throttling:

* Use an external website checker (e.g., [Uptrends](https://www.uptrends.com/tools/uptime)) to test access.
* Consider temporary VPN usage for diagnostics (ensure legality).

### 🔐 CSRF Token Not Found:

* The page layout may have changed — inspect the HTML to confirm CSRF input still exists.
* Ensure cookies and headers are being handled properly via the session object.

---

## ⚖️ Important Considerations

* **Legal Compliance**: This script is intended for educational or personal archival purposes. Mass scraping of government portals is discouraged and may be legally restricted.
* **Respect `robots.txt`**: Always review and comply with scraping permissions if the file is present.
* **API Alternatives**: Prefer official APIs or data exports if your use case permits.
* **Site Changes**: This script may break if the HTML structure or endpoints of the website are modified.

---

## 📝 License

This project is distributed under the terms specified in the [LICENSE](./LICENSE) file.

---

## 🤝 Contributions

Contributions are welcome via pull requests or issue submissions. Please ensure changes are tested and follow Python best practices.