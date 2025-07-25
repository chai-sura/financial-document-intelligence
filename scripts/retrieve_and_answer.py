import faiss
import pickle
from sentence_transformers import SentenceTransformer
from transformers import pipeline

INDEX_PATH = "faiss_index.bin"
META_PATH = "chunk_metadata.pkl"

# Load index and metadata
index = faiss.read_index(INDEX_PATH)
with open(META_PATH, 'rb') as f:
    metadata = pickle.load(f)

embedder = SentenceTransformer('all-MiniLM-L6-v2')
summarizer = pipeline('summarization', model='facebook/bart-large-cnn')

def search_chunks(question, top_k=3, company=None):
    q_emb = embedder.encode([question])
    D, I = index.search(q_emb, 15)
    results = []
    count = 0
    for idx in I[0]:
        meta = metadata[idx]
        if company and meta['company'].lower() != company.lower():
            continue
        if len(meta['text'].split()) < 10:
            continue
        text = meta['text']
        results.append({'text': text, 'meta': meta})
        count += 1
        if count >= top_k:
            break
    return results

def answer_question(question, company=None):
    # Retrieve top relevant chunks
    chunks = search_chunks(question, top_k=3, company=company)
    if not chunks:
        return None, []
    # Concatenate context from all retrieved chunks
    context = "\n\n".join(chunk['text'] for chunk in chunks)
    # BART has a max token limit; trim if needed (usually ~3500 chars is safe)
    context = context[:3500]
    prompt = f"Question: {question}\nContext: {context}"
    summary = summarizer(prompt, max_length=200, min_length=50, do_sample=False)[0]['summary_text']
    return summary, chunks

if __name__ == "__main__":
    print("Loaded index with {} chunks.".format(len(metadata)))
    company = input("Enter company ticker (e.g., AAPL), or leave blank for all: ").strip().upper()
    if company == "":
        company = None

    while True:
        q = input("\nAsk a financial question (or type 'exit'): ")
        if q.lower() == 'exit':
            break
        answer, used_chunks = answer_question(q, company=company)
        if not answer:
            print("No relevant chunks found for this query. Try another question or company.")
            continue
        # Display a preview of the most relevant chunk for context info
        best_chunk = used_chunks[0]['meta'] if used_chunks else {}
        print(f"\nGenerated Answer: {answer}\n")
        if used_chunks:
            print(f"Top Context Section: {best_chunk.get('section')} | Subheading: {best_chunk.get('subheading')}")
            print(f"File: {best_chunk.get('company')} {best_chunk.get('year')} - {best_chunk.get('filename')}\n")
