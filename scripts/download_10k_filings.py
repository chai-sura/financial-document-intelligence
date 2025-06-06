import os
import requests
from tqdm import tqdm
from datetime import datetime

# ----------------- CONFIG -----------------
TICKERS = ['AAPL', 'MSFT', 'TSLA']
YEARS = ['2019', '2020', '2021', '2022', '2023']
BASE_DIR = 'data/raw/10k_filings'
SEC_API = 'https://data.sec.gov'
HEADERS = {'User-Agent': 'Chaitanya Sura chaitanyasura1980@gmail.com'}

def ensure_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    for ticker in TICKERS:
        os.makedirs(os.path.join(BASE_DIR, ticker), exist_ok=True)

def get_cik(ticker):
    """Fetch CIK mapping using SEC's JSON endpoint"""
    res = requests.get('https://www.sec.gov/files/company_tickers.json', headers=HEADERS)
    data = res.json()
    for item in data.values():
        if item['ticker'].lower() == ticker.lower():
            return str(item['cik_str']).zfill(10)
    return None

def get_10k_urls(cik):
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
            cik_stripped = str(int(cik))
            file_url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{accession}/{primary_doc}"
            if primary_doc.endswith(('.htm', '.html')):
                urls.append((accession, file_url))

    return urls



def download_filing(ticker, cik, accession, url):
    if not url.endswith(('.htm', '.html')):  # Ensure only HTML-based documents
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

def main():
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

if __name__ == '__main__':
    main()
