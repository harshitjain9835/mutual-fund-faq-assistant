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

allowed_module_roots = [
    p.resolve() for p in [current_dir, current_dir / "src", current_dir.parent, current_dir.parent / "src"] if p.exists()
]

def _load_module_from_file(module_name: str, module_path: Path):
    """Load a module object from an explicit local module path."""
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _first_available_symbol(module, candidates: list[str]):
    """Return the first callable symbol found in a module from the given candidate names."""
    for symbol_name in candidates:
        value = getattr(module, symbol_name, None)
        if callable(value):
            return value
    return None


def _is_project_module(module) -> bool:
    """Return True when an imported module originates from project paths."""
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return False
    module_path = Path(module_file).resolve()
    return any(root == module_path or root in module_path.parents for root in allowed_module_roots)


def _resolve_backend_module(file_candidates: list[Path], import_candidates: list[str], local_name: str):
    """Resolve a backend module from local files first, then safe package imports."""
    errors = []

    for module_path in file_candidates:
        if not module_path.exists():
            continue
        try:
            return _load_module_from_file(local_name, module_path), errors
        except Exception as e:
            errors.append(f"file:{module_path} -> {e}")

    for module_name in import_candidates:
        try:
            imported = importlib.import_module(module_name)
            if _is_project_module(imported):
                return imported, errors
            imported_file = getattr(imported, "__file__", "<unknown>")
            errors.append(f"import:{module_name} ignored (non-project module at {imported_file})")
        except Exception as e:
            errors.append(f"import:{module_name} -> {e}")

    return None, errors


def _import_backend_functions():
    """Import backend functions using local files first, then package imports."""
    retrieve_candidates = ["retrieve_passages", "retrieve", "search_passages"]
    generate_candidates = ["generate_answer", "generate", "answer_question"]

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

    retrieval_module, retrieval_errors = _resolve_backend_module(
        retrieval_files,
        ["src.retrieval", "retrieval"],
        "local_retrieval",
    )
    generate_module, generate_errors = _resolve_backend_module(
        generate_files,
        ["src.generate", "generate"],
        "local_generate",
    )

    retrieve_fn = _first_available_symbol(retrieval_module, retrieve_candidates) if retrieval_module else None
    generate_fn = _first_available_symbol(generate_module, generate_candidates) if generate_module else None

    if retrieve_fn and generate_fn:
        return retrieve_fn, generate_fn

    retrieval_available = [
        name for name in retrieve_candidates if retrieval_module and callable(getattr(retrieval_module, name, None))
    ]
    generate_available = [
        name for name in generate_candidates if generate_module and callable(getattr(generate_module, name, None))
    ]
    raise ImportError(
        "Could not resolve backend functions. "
        f"retrieval candidates={retrieve_candidates}, found={retrieval_available}; "
        f"generate candidates={generate_candidates}, found={generate_available}. "
        f"retrieval resolution errors={retrieval_errors}; "
        f"generate resolution errors={generate_errors}."
    )


def _build_backend_fallback(reason: str):
    """Create fallback backend functions so the app can boot with a visible error."""
    def retrieve_fallback(query: str, top_k: int = 3):
        return [{"error": "backend_unavailable", "message": f"Backend import failed: {reason}"}]

    def generate_fallback(query: str, passages):
        if passages and isinstance(passages, list) and isinstance(passages[0], dict):
            return passages[0].get("message", "Backend is unavailable.")
        return f"Backend is unavailable: {reason}"

    return retrieve_fallback, generate_fallback


try:
    retrieve_passages, generate_answer = _import_backend_functions()
    backend_init_error = None
except Exception as e:
    backend_init_error = str(e)
    retrieve_passages, generate_answer = _build_backend_fallback(backend_init_error)

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
if backend_init_error:
    st.error("Backend modules could not be loaded. Check deployment paths/dependencies. Details: " + backend_init_error)

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
