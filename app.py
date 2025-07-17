import streamlit as st
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from transformers import pipeline

st.set_page_config(page_title="SEC 10-K Q&A Agent", layout="wide")
st.title("Financial file Q&A ")
st.text("Ask any financial or business question about your chosen company!")

# --- Load Models & Index ---
@st.cache_resource
def load_assets():
    index = faiss.read_index("faiss_index.bin")
    with open("chunk_metadata.pkl", "rb") as f:
        metadata = pickle.load(f)
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    qa = pipeline('question-answering', model='distilbert-base-cased-distilled-squad')
    return index, metadata, embedder, qa

index, metadata, embedder, qa = load_assets()
companies = sorted(list(set(m['company'] for m in metadata)))

# --- Session state for chat ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "selected_company" not in st.session_state:
    st.session_state.selected_company = "All"

# --- Sidebar for Company Selection and Session Controls ---
with st.sidebar:
    st.header("Settings")
    company = st.selectbox("Select Company", ["All"] + companies, index=(["All"] + companies).index(st.session_state.selected_company))
    if st.button("Restart Session (Clear Chat)"):
        st.session_state.chat_history = []
    st.session_state.selected_company = company

# --- Chat Interface (streamlit 1.23+ supports st.chat_message and st.chat_input) ---
for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(message)

user_input = st.chat_input("Ask a financial question...")

def search_chunks(question, top_k=5, company=None):
    q_emb = embedder.encode([question])
    D, I = index.search(q_emb, 20)
    results = []
    count = 0
    for idx in I[0]:
        meta = metadata[idx]
        if company and meta['company'].lower() != company.lower():
            continue
        if meta.get('type') == 'table':
            continue
        if len(meta['text'].split()) < 10:
            continue
        results.append({'text': meta['text'], 'meta': meta})
        count += 1
        if count >= top_k:
            break
    return results

def answer_question(question, company=None):
    chunks = search_chunks(question, top_k=5, company=company)
    if not chunks:
        return "No relevant information found."
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
    best = answers[0]
    meta = best['meta']
    result = f"**Answer:** {best['answer']}  (score: {best['score']:.3f})\n\n" \
             f"**Section:** {meta.get('section')} | **Subheading:** {meta.get('subheading')}\n\n" \
             f"**Source:** {meta['company']} {meta['year']} | *File: {meta['filename']}*"
    with st.expander("Show Context"):
        st.markdown(best['context'][:700] + "...")
    return result

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.chat_history.append(("user", user_input))

    # Get answer
    selected_company = None if st.session_state.selected_company == "All" else st.session_state.selected_company
    with st.spinner("Searching and answering..."):
        answer = answer_question(user_input, company=selected_company)
    with st.chat_message("assistant"):
        st.markdown(answer)
    st.session_state.chat_history.append(("assistant", answer))
