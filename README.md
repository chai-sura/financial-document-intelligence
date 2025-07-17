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

4.**Convert HTML to Plain Text**

Bulk convert:

```sh
python scripts/parse_html_to_text.py --raw_dir data/raw/10k_filings --text_dir data/processed/10k_text
```
Single file:


```sh
python scripts/parse_html_to_text.py --file <input.html> --out <output.txt>
```

5.**Chunk Plain Text for RAG**

```sh
python scripts/chunk_10k_sections.py --txt_dir data/processed/10k_text --out_dir data/chunks/10k_chunks
```


6.**Build Embedding Index**

```sh
python scripts/embed_chunks.py
```
This produces faiss_index.bin and chunk_metadata.pkl for semantic search.


7.**Retrieval-Augmented Q&A (CLI Version)**

```sh
python scripts/retrieve_and_answer.py
```

8.**Launch Streamlit UI**
```sh
streamlit run scripts/app.py
```