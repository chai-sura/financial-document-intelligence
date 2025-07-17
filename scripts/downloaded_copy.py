import os
import requests

TICKERS = ['AAPL', 'MSFT', 'TSLA']
YEARS = ['2019', '2020', '2021', '2022', '2023']
BASE_DIR = 'data/raw/10k_filings_pdf'
os.makedirs(BASE_DIR, exist_ok=True)
SEC_API_KEY = "b5eb7fb66d68f6440f847cf2c664957af37141e6daa6aa937f9d662b22811335"  # <-- Put your SEC-API key here

SEC_HEADERS = {'User-Agent': 'Your Name your@email.com'}  # SEC.gov requires this!

def get_cik(ticker):
    """Get the CIK for a given ticker symbol."""
    r = requests.get('https://www.sec.gov/files/company_tickers.json', headers=SEC_HEADERS)
    tickers = r.json()
    for info in tickers.values():
        if info['ticker'].lower() == ticker.lower():
            return str(info['cik_str']).zfill(10)
    return None

def get_10k_html_url(cik, year):
    """Get the HTML filing URL for a 10-K of a given CIK and year."""
    filings_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    r = requests.get(filings_url, headers=SEC_HEADERS)
    if r.status_code != 200:
        return None
    data = r.json()
    filings = data.get('filings', {}).get('recent', {})
    for i, form in enumerate(filings.get('form', [])):
        if form == '10-K':
            filing_year = filings['filingDate'][i][:4]
            if filing_year == str(year):
                accession = filings['accessionNumber'][i].replace('-', '')
                primary_doc = filings['primaryDocument'][i]
                cik_stripped = str(int(cik))
                url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{accession}/{primary_doc}"
                if url.endswith('.htm') or url.endswith('.html'):
                    return url
    return None

def download_10k_pdf_via_secapi(ticker, year):
    cik = get_cik(ticker)
    if not cik:
        print(f"CIK not found for ticker {ticker}")
        return
    html_url = get_10k_html_url(cik, year)
    if not html_url:
        print(f"No 10-K HTML URL found for {ticker} in {year}")
        return
    # Download PDF via SEC-API using this HTML URL
    api_url = (
        f"https://api.sec-api.io/filing-reader?token={SEC_API_KEY}&url={html_url}&output=pdf"
    )
    response = requests.get(api_url, stream=True)
    if response.status_code == 200 and response.headers.get("Content-Type") == "application/pdf":
        company_dir = os.path.join(BASE_DIR, ticker)
        os.makedirs(company_dir, exist_ok=True)
        file_path = os.path.join(company_dir, f"{ticker}_{year}_10K.pdf")
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Downloaded PDF: {file_path}")
    else:
        print(f"Failed to download PDF for {ticker} {year} - Status {response.status_code}: {response.text[:200]}")

def main():
    for ticker in TICKERS:
        for year in YEARS:
            download_10k_pdf_via_secapi(ticker, year)

if __name__ == "__main__":
    main()
