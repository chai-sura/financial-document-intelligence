import os
import requests
from tqdm import tqdm
from datetime import datetime

# ----------------- CONFIGURATION -----------------
TICKERS = ['AAPL', 'MSFT', 'TSLA']  # List of company tickers to fetch filings for
YEARS = ['2019', '2020', '2021', '2022', '2023']  # Target filing years
BASE_DIR = 'data/raw/10k_filings'  # Directory to save the downloaded files
SEC_API = 'https://data.sec.gov'  # Base SEC API URL
HEADERS = {'User-Agent': 'Chaitanya Sura chaitanyasura1980@gmail.com'}  # Required for SEC API access

# ----------------- UTILITY FUNCTIONS -----------------

def ensure_dirs():
    """Create base and per-ticker directories if they don't already exist."""
    os.makedirs(BASE_DIR, exist_ok=True)
    for ticker in TICKERS:
        os.makedirs(os.path.join(BASE_DIR, ticker), exist_ok=True)

def get_cik(ticker):
    """
    Fetch Central Index Key (CIK) for a given ticker.
    Returns a zero-padded 10-digit CIK string.
    """
    res = requests.get('https://www.sec.gov/files/company_tickers.json', headers=HEADERS)
    data = res.json()
    for item in data.values():
        if item['ticker'].lower() == ticker.lower():
            return str(item['cik_str']).zfill(10)
    return None

def get_10k_urls(cik):
    """
    For a given CIK, fetch the list of 10-K filing document URLs from SEC.
    Filters only 10-K forms from the specified YEARS.
    """
    url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []

    filings = res.json().get('filings', {}).get('recent', {})
    forms = filings.get('form', [])
    accession_numbers = filings.get('accessionNumber', [])
    primary_docs = filings.get('primaryDocument', [])
    filing_dates = filings.get('filingDate', [])

    urls = []
    for i, form in enumerate(forms):
        if form == '10-K':
            year = filing_dates[i][:4]
            if year not in YEARS:
                continue
            accession = accession_numbers[i].replace('-', '')
            primary_doc = primary_docs[i]
            cik_stripped = str(int(cik))  # Remove leading zeros
            file_url = f"{SEC_API}/Archives/edgar/data/{cik_stripped}/{accession}/{primary_doc}"
            if primary_doc.endswith(('.htm', '.html')):  # Only include HTML-based documents
                urls.append((accession, file_url))

    return urls

def download_filing(ticker, cik, accession, url):
    """
    Download the 10-K filing HTML document from the given URL
    and save it to the appropriate ticker folder.
    """
    if not url.endswith(('.htm', '.html')):
        print(f"Skipped (not .htm or .html): {url}")
        return

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            ext = '.html' if url.endswith('.html') else '.htm'
            filename = f"{BASE_DIR}/{ticker}/{accession}{ext}"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(res.text)
            print(f" Saved: {filename}")
        else:
            print(f" Failed ({res.status_code}) for {ticker}: {url}")
    except Exception as e:
        print(f" Exception for {ticker} at {url}: {e}")

# ----------------- MAIN LOGIC -----------------

def main():
    """Main function to download 10-K filings for all specified tickers."""
    ensure_dirs()
    for ticker in TICKERS:
        print(f"\nFetching 10-Ks for {ticker}")
        cik = get_cik(ticker)
        if not cik:
            print(f"Ticker not found: {ticker}")
            continue
        print(f"CIK for {ticker}: {cik}")
        urls = get_10k_urls(cik)
        print(f"Found {len(urls)} 10-K URLs")
        for accession, url in tqdm(urls, desc=f" Downloading {ticker}"):
            download_filing(ticker, cik, accession, url)

# ----------------- RUN -----------------

if __name__ == '__main__':
    main()