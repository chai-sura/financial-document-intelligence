# financial-document-intelligence
## Financial Document Intelligence

## Financial Q&A Agent
A pipeline and AI agent for automated question answering and analytics on financial documents (such as SEC 10-K filings).

1.**Clone the Repo**

```sh
git clone https://github.com/chai-sura/financial-document-intelligence.git
cd financial-document-intelligence
```


2.**Setup Python Environment**

```sh
python -m venv venv_fdi
source venv_fdi/bin/activate  # On Windows: venv_fdi\Scripts\activate
pip install -r requirements.txt
```


3.**Download 10-K Filings**
Edit the list of companies (TICKERS) and years (YEARS) in scripts/download_10k_filings.py.

```sh
python scripts/download_10k_filings.py
```

3.**Convert HTML to Plain Text**

Bulk convert:

```sh
python scripts/parse_html_to_text.py --raw_dir data/raw/10k_filings --text_dir data/processed/10k_text
```
Single file:


```sh
python scripts/parse_html_to_text.py --file <input.html> --out <output.txt>
```

Troubleshooting

Check that your folder structure matches the project structure.

If TOC or duplicate headers appear, update to the latest cleaning script.

For new tickers, edit and rerun the scripts.