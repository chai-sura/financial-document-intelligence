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
qa = pipeline('question-answering', model='distilbert-base-cased-distilled-squad')

def search_chunks(question, top_k=5, company=None):
    q_emb = embedder.encode([question])
    D, I = index.search(q_emb, 20)
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
    chunks = search_chunks(question, top_k=5, company=company)
    if not chunks:
        return None, []
    answers = []
    for chunk in chunks:
        ans = qa({'question': question, 'context': chunk['text']})
        answers.append({
            'answer': ans['answer'],
            'score': ans['score'],
            'context': chunk['text'],
            'meta': chunk['meta']
        })
    answers = sorted(answers, key=lambda x: x['score'], reverse=True)
    return answers[0], answers

if __name__ == "__main__":
    print("Loaded index with {} chunks.".format(len(metadata)))
    company = input("Enter company ticker (e.g., AAPL), or leave blank for all: ").strip().upper()
    if company == "":
        company = None

    while True:
        q = input("\nAsk a financial question (or type 'exit'): ")
        if q.lower() == 'exit':
            break
        best, all_answers = answer_question(q, company=company)
        if not best:
            print("No relevant chunks found for this query. Try another question or company.")
            continue
        meta = best['meta']
        print(f"\nBest Answer: {best['answer']} (score: {best['score']:.3f})")
        print(f"Section: {meta.get('section')} | Subheading: {meta.get('subheading')}")
        print(f"Context: {best['context'][:200].replace('\n', ' ')}...")
        print(f"Source: {meta['company']} {meta['year']} File: {meta['filename']}\n")
