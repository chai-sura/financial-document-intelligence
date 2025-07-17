import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle

# Path to directory with JSON chunk files (one subfolder per company)
CHUNKS_DIR = "data/chunks/10k_chunks"
INDEX_PATH = "faiss_index.bin"
META_PATH = "chunk_metadata.pkl"

texts = []
metadata = []

for company in os.listdir(CHUNKS_DIR):
    company_dir = os.path.join(CHUNKS_DIR, company)
    if not os.path.isdir(company_dir):
        continue
    for fname in os.listdir(company_dir):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(company_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
            for chunk in chunks:
                 if chunk.get("type") != "info" and len(chunk['text'].split()) >= 8:
                    texts.append(chunk['text'])
                    meta = chunk.copy()
                    meta['company'] = company
                    meta['filename'] = fname
                    metadata.append(meta)

print(f"Loaded {len(texts)} chunks.")

# Load MiniLM model from sentence-transformers
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

# Create FAISS index
d = embeddings.shape[1]
index = faiss.IndexFlatL2(d)
index.add(embeddings)
faiss.write_index(index, INDEX_PATH)

# Save metadata
with open(META_PATH, 'wb') as meta_file:
    pickle.dump(metadata, meta_file)

print(f"FAISS index and metadata saved. Indexed {len(texts)} chunks.")
