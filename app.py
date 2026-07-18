import sys
import importlib
import importlib.util
from pathlib import Path
import streamlit as st

# Add candidate source roots to sys.path for local/cloud compatibility.
current_dir = Path(__file__).resolve().parent
candidate_src_dirs = [
    current_dir,
    current_dir / "src",
    current_dir.parent / "src",
]
for src_dir in candidate_src_dirs:
    if src_dir.is_dir() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

def _load_symbol_from_file(module_name: str, module_path: Path, symbol_name: str):
    """Load a symbol from an explicit local module path."""
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, symbol_name):
        raise AttributeError(f"{module_path} has no attribute '{symbol_name}'")
    return getattr(module, symbol_name)


def _import_backend_functions():
    """Import backend functions using local files first, then package imports."""
    retrieval_files = [
        current_dir / "retrieval.py",
        current_dir / "src" / "retrieval.py",
        current_dir.parent / "src" / "retrieval.py",
    ]
    generate_files = [
        current_dir / "generate.py",
        current_dir / "src" / "generate.py",
        current_dir.parent / "src" / "generate.py",
    ]

    for retrieval_path, generate_path in zip(retrieval_files, generate_files):
        if retrieval_path.exists() and generate_path.exists():
            retrieve_fn = _load_symbol_from_file("local_retrieval", retrieval_path, "retrieve_passages")
            generate_fn = _load_symbol_from_file("local_generate", generate_path, "generate_answer")
            return retrieve_fn, generate_fn

    retrieval_module = importlib.import_module("src.retrieval")
    generate_module = importlib.import_module("src.generate")
    if not hasattr(retrieval_module, "retrieve_passages"):
        raise AttributeError("Module 'src.retrieval' does not define 'retrieve_passages'.")
    if not hasattr(generate_module, "generate_answer"):
        raise AttributeError("Module 'src.generate' does not define 'generate_answer'.")
    return retrieval_module.retrieve_passages, generate_module.generate_answer


retrieve_passages, generate_answer = _import_backend_functions()

# Page Configuration
st.set_page_config(page_title="Mutual Fund FAQ Assistant", page_icon="📈", layout="centered")

# Custom CSS for Phase 5 UI matching screen.png
st.markdown("""
    <style>
    .title-text {
        color: #00D09C;
        font-size: 26px;
        font-weight: bold;
        margin-bottom: 20px;
        margin-top: -20px;
    }
    .welcome-title {
        text-align: center;
        font-size: 36px;
        font-weight: bold;
        margin-top: 40px;
    }
    .welcome-subtitle {
        text-align: center;
        color: #b0b0b5;
        font-size: 16px;
        margin-bottom: 40px;
        line-height: 1.5;
    }
    .terminal-header {
        display: flex;
        align-items: center;
        border-bottom: 1px solid #333;
        padding-bottom: 10px;
        margin-bottom: 10px;
        color: #888;
        font-size: 12px;
        font-family: monospace;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .dots {
        display: flex;
        gap: 6px;
        margin-right: 15px;
    }
    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .dot.red { background-color: #ff5f56; }
    .dot.yellow { background-color: #ffbd2e; }
    .dot.green { background-color: #27c93f; }
    .terminal-empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        color: #00D09C;
        font-family: monospace;
        font-size: 14px;
    }
    .footer-container {
        text-align: center;
        color: #666;
        font-size: 11px;
        padding-top: 20px;
        border-top: 1px solid #222;
        margin-top: 60px;
        margin-bottom: 20px;
    }
    .footer-links a {
        color: #666;
        text-decoration: none;
        margin: 0 10px;
    }
    .footer-links a:hover {
        color: #00D09C;
    }
    div.stButton > button {
        border-radius: 20px;
        border: 1px solid #333;
        background-color: #1a1a1d;
        color: #e5e1e4;
        font-size: 12px;
        min-height: 60px;
        width: 100%;
        white-space: normal;
        word-wrap: break-word;
    }
    div.stButton > button:hover {
        border-color: #00D09C;
        color: #00D09C;
    }
    </style>
""", unsafe_allow_html=True)

# Top Header & Warning
st.markdown('<div class="title-text">Mutual Fund FAQ Assistant</div>', unsafe_allow_html=True)
st.warning("⚠️ **Facts-only. No investment advice.**")

# Welcome Section
st.markdown('<div class="welcome-title">Welcome!</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="welcome-subtitle">Ask me objective, verifiable questions about your mutual fund schemes. '
    'I provide data<br>directly from regulatory sources.</div>', 
    unsafe_allow_html=True
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Example Queries
col1, col2, col3 = st.columns(3)
preset_prompt = None

with col1:
    if st.button("What is the expense ratio and exit load of HDFC Mid Cap?"):
        preset_prompt = "What is the expense ratio and exit load of HDFC Mid Cap?"
with col2:
    if st.button("Who is the fund manager for HDFC Defence Fund?"):
        preset_prompt = "Who is the fund manager for HDFC Defence Fund?"
with col3:
    if st.button("What is the benchmark index for HDFC Small Cap?"):
        preset_prompt = "What is the benchmark index for HDFC Small Cap?"

st.markdown("<br>", unsafe_allow_html=True)

# Chat Input
user_input = st.chat_input("Type your question (e.g., 'What is NAV?')")
prompt = preset_prompt or user_input

# Terminal UI Container
terminal_container = st.container(border=True)

with terminal_container:
    st.markdown('''
        <div class="terminal-header">
            <div class="dots">
                <div class="dot red"></div>
                <div class="dot yellow"></div>
                <div class="dot green"></div>
            </div>
            TERMINAL OUTPUT
        </div>
    ''', unsafe_allow_html=True)

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    if not st.session_state.messages:
        st.markdown('''
            <div class="terminal-empty">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#00D09C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 10px;">
                    <polyline points="4 17 10 11 4 5"></polyline>
                    <line x1="12" y1="19" x2="20" y2="19"></line>
                </svg>
                Awaiting your query...|
            </div>
        ''', unsafe_allow_html=True)
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt:
            with st.chat_message("assistant"):
                with st.spinner("Searching official sources..."):
                    passages = retrieve_passages(prompt)
                    response = generate_answer(prompt, passages)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})

# Footer
st.markdown('''
    <div class="footer-container">
        <p style="margin-bottom: 8px;">Compliance & Disclaimer: Mutual Fund investments are subject to market risks. Read all scheme related documents carefully before investing. Sensitivity data is redacted via Privacy Guardrail.</p>
        <div class="footer-links">
            <a href="#">Terms of Service</a>
            <a href="#">Privacy Policy</a>
        </div>
    </div>
''', unsafe_allow_html=True)
