import importlib
import importlib.util
import sys
from pathlib import Path

import streamlit as st

# Add candidate source roots to sys.path for local/cloud compatibility.
CURRENT_DIR = Path(__file__).resolve().parent
CANDIDATE_SRC_DIRS = [
    CURRENT_DIR,
    CURRENT_DIR / "src",
    CURRENT_DIR.parent / "src",
]
for src_dir in CANDIDATE_SRC_DIRS:
    if src_dir.is_dir() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

ALLOWED_MODULE_ROOTS = [
    p.resolve()
    for p in [
        CURRENT_DIR,
        CURRENT_DIR / "src",
        CURRENT_DIR.parent,
        CURRENT_DIR.parent / "src",
    ]
    if p.exists()
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
    """Return the first callable symbol found in a module from candidate names."""
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
    return any(root == module_path or root in module_path.parents for root in ALLOWED_MODULE_ROOTS)


def _resolve_backend_module(
    file_candidates: list[Path],
    import_candidates: list[str],
    local_name: str,
    required_symbols: list[str],
):
    """Resolve a backend module that defines at least one required callable symbol."""
    errors = []

    for module_path in file_candidates:
        if not module_path.exists():
            continue
        try:
            module = _load_module_from_file(local_name, module_path)
            if _first_available_symbol(module, required_symbols):
                return module, errors
            errors.append(f"file:{module_path} missing callable symbols from {required_symbols}")
        except Exception as exc:
            errors.append(f"file:{module_path} -> {exc}")

    for module_name in import_candidates:
        try:
            imported = importlib.import_module(module_name)
            if not _is_project_module(imported):
                imported_file = getattr(imported, "__file__", "<unknown>")
                errors.append(f"import:{module_name} ignored (non-project module at {imported_file})")
                continue
            if _first_available_symbol(imported, required_symbols):
                return imported, errors
            imported_file = getattr(imported, "__file__", "<unknown>")
            errors.append(
                f"import:{module_name} at {imported_file} missing callable symbols from {required_symbols}"
            )
        except Exception as exc:
            errors.append(f"import:{module_name} -> {exc}")

    return None, errors


def _import_backend_functions():
    """Import backend functions using local files first, then package imports."""
    retrieve_candidates = ["retrieve_passages", "retrieve", "search_passages"]
    generate_candidates = ["generate_answer", "generate", "answer_question"]

    retrieval_files = [
        CURRENT_DIR / "retrieval.py",
        CURRENT_DIR / "src" / "retrieval.py",
        CURRENT_DIR.parent / "src" / "retrieval.py",
    ]
    generate_files = [
        CURRENT_DIR / "generate.py",
        CURRENT_DIR / "src" / "generate.py",
        CURRENT_DIR.parent / "src" / "generate.py",
    ]

    retrieval_module, retrieval_errors = _resolve_backend_module(
        retrieval_files,
        ["src.retrieval", "retrieval"],
        "local_retrieval",
        retrieve_candidates,
    )
    generate_module, generate_errors = _resolve_backend_module(
        generate_files,
        ["src.generate", "generate"],
        "local_generate",
        generate_candidates,
    )

    retrieve_fn = _first_available_symbol(retrieval_module, retrieve_candidates) if retrieval_module else None
    generate_fn = _first_available_symbol(generate_module, generate_candidates) if generate_module else None

    if retrieve_fn and generate_fn:
        return retrieve_fn, generate_fn

    retrieval_available = [
        name
        for name in retrieve_candidates
        if retrieval_module and callable(getattr(retrieval_module, name, None))
    ]
    generate_available = [
        name
        for name in generate_candidates
        if generate_module and callable(getattr(generate_module, name, None))
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


def _process_prompt(prompt: str) -> None:
    """Resolve answer for a factual prompt and save it to session state."""
    passages = retrieve_passages(prompt)
    response = generate_answer(prompt, passages)
    st.session_state.last_query = prompt
    st.session_state.last_response = response


try:
    retrieve_passages, generate_answer = _import_backend_functions()
    backend_init_error = None
except Exception as exc:
    backend_init_error = str(exc)
    retrieve_passages, generate_answer = _build_backend_fallback(backend_init_error)

st.set_page_config(page_title="Mutual Fund FAQ Assistant", page_icon="📈", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg: #131315;
        --surface-0: #0e0e10;
        --surface-1: #1b1b1d;
        --surface-2: #201f21;
        --surface-3: #2a2a2c;
        --outline: #3c4a43;
        --text: #e5e1e4;
        --text-muted: #bacac1;
        --primary: #44edb7;
        --primary-strong: #00d09c;
        --warning: #ffcb76;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 20% -20%, #1f2a26 0%, transparent 45%),
                    radial-gradient(circle at 90% -10%, #243235 0%, transparent 42%),
                    var(--bg);
        color: var(--text);
    }

    header[data-testid="stHeader"] { visibility: hidden; height: 0; }
    .block-container {
        max-width: 1100px;
        padding-top: 0.8rem;
        padding-bottom: 1rem;
    }

    .topbar {
        position: sticky;
        top: 0;
        z-index: 20;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 62px;
        padding: 0 8px;
        border-bottom: 1px solid var(--outline);
        background: rgba(19, 19, 21, 0.96);
        backdrop-filter: blur(6px);
    }

    .brand {
        font-size: 1.9rem;
        line-height: 1;
        font-weight: 700;
        color: var(--primary);
        letter-spacing: -0.01em;
    }

    .icon-row {
        display: flex;
        gap: 12px;
        color: var(--text-muted);
        font-size: 1.1rem;
    }

    .warn {
        margin: 18px 0 30px;
        border: 1px solid rgba(255, 203, 118, 0.35);
        border-radius: 12px;
        background: rgba(255, 203, 118, 0.09);
        color: var(--warning);
        padding: 12px 16px;
        font-size: 0.82rem;
        font-weight: 500;
    }

    .hero {
        text-align: center;
        margin: 10px 0 16px;
    }

    .hero h1 {
        font-size: 3rem;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .hero p {
        margin: 12px auto 0;
        color: var(--text-muted);
        max-width: 700px;
        font-size: 1.2rem;
        line-height: 1.45;
    }

    .chip-row-note {
        text-align: center;
        color: transparent;
        margin-bottom: 0.35rem;
    }

    .stButton > button {
        border-radius: 999px;
        border: 1px solid var(--outline);
        background: var(--surface-3);
        color: var(--text);
        min-height: 2.5rem;
        font-size: 0.82rem;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        border-color: var(--primary);
        color: var(--primary);
    }

    .query-shell {
        margin-top: 12px;
    }

    div[data-testid="stForm"] {
        border: 1px solid var(--outline);
        border-radius: 12px;
        background: var(--surface-2);
        padding: 12px 12px 2px;
    }

    div[data-testid="stTextInput"] input {
        border: 0;
        outline: none;
        box-shadow: none;
        background: transparent;
        color: var(--text);
        font-size: 0.98rem;
    }

    div[data-testid="stTextInput"] input::placeholder {
        color: #8f9792;
    }

    .query-shell .stFormSubmitButton > button {
        width: 48px;
        min-width: 48px;
        height: 42px;
        border-radius: 10px;
        background: var(--primary-strong);
        color: #003828;
        border: none;
        font-size: 1.05rem;
        margin-top: 1px;
    }

    .query-shell .stFormSubmitButton > button:hover {
        background: #34e2b1;
        color: #003828;
    }

    .terminal {
        margin-top: 12px;
        border: 1px solid var(--outline);
        border-radius: 12px;
        background: #141416;
        min-height: 320px;
        padding: 14px;
        animation: rise 320ms ease-out;
    }

    .terminal-head {
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid #31373a;
        padding-bottom: 10px;
        margin-bottom: 14px;
    }

    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }

    .dot.red { background: #bf6e77; }
    .dot.amber { background: #b4965c; }
    .dot.green { background: #2f9f8e; }

    .terminal-title {
        margin-left: 8px;
        color: #a5ada9;
        letter-spacing: 0.08em;
        font-size: 0.72rem;
        font-weight: 600;
    }

    .awaiting {
        min-height: 230px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        color: var(--text-muted);
        gap: 8px;
    }

    .awaiting-icon {
        color: var(--primary);
        font-size: 1.6rem;
        border: 2px solid var(--primary);
        border-radius: 5px;
        line-height: 1;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .terminal-answer {
        background: var(--surface-1);
        border: 1px solid var(--outline);
        border-left: 4px solid var(--primary);
        border-radius: 10px;
        padding: 12px;
        color: var(--text);
        line-height: 1.5;
    }

    .footer {
        margin-top: 22px;
        border-top: 1px solid #2f3336;
        text-align: center;
        padding-top: 18px;
        color: #9aa09d;
        font-size: 0.72rem;
    }

    .footer-links {
        margin-top: 8px;
        display: flex;
        justify-content: center;
        gap: 26px;
    }

    .footer-links a {
        color: #9aa09d;
        text-decoration: none;
    }

    .footer-links a:hover {
        color: var(--primary);
    }

    @keyframes rise {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 900px) {
        .brand { font-size: 1.5rem; }
        .hero h1 { font-size: 2.4rem; }
        .hero p { font-size: 1.02rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="topbar">
        <div class="brand">Mutual Fund FAQ Assistant</div>
        <div class="icon-row"><span>?</span><span>i</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="warn">⚠ Facts-only. No investment advice.</div>', unsafe_allow_html=True)
if backend_init_error:
    st.error("Backend modules could not be loaded. Details: " + backend_init_error)

st.markdown(
    """
    <section class="hero">
        <h1>Welcome!</h1>
        <p>
            Ask me objective, verifiable questions about your mutual fund schemes.
            I provide data directly from regulatory sources.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "last_response" not in st.session_state:
    st.session_state.last_response = ""

example_queries = [
    "What is the expense ratio and exit load of HDFC Mid Cap?",
    "Who is the fund manager for HDFC Defence Fund?",
    "What is the benchmark index for HDFC Small Cap?",
]

pill_cols = st.columns(3)
for idx, col in enumerate(pill_cols):
    with col:
        if st.button(example_queries[idx], key=f"pill_{idx}", use_container_width=True):
            _process_prompt(example_queries[idx])

st.markdown('<div class="chip-row-note">&nbsp;</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="query-shell">', unsafe_allow_html=True)
    with st.form("query_form", clear_on_submit=True):
        input_col, send_col = st.columns([12, 1])
        with input_col:
            typed_prompt = st.text_input(
                "Ask a facts-only mutual fund question",
                value="",
                placeholder="Type your question (e.g., 'What is NAV?')",
                label_visibility="collapsed",
            )
        with send_col:
            submitted = st.form_submit_button("➤")
    st.markdown('</div>', unsafe_allow_html=True)

if submitted and typed_prompt.strip():
    _process_prompt(typed_prompt.strip())

st.markdown(
    """
    <div class="terminal">
        <div class="terminal-head">
            <span class="dot red"></span>
            <span class="dot amber"></span>
            <span class="dot green"></span>
            <span class="terminal-title">TERMINAL OUTPUT</span>
        </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.last_response:
    st.markdown(
        """
        <div class="awaiting">
            <div class="awaiting-icon">&gt;_</div>
            <div>Awaiting your query...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="terminal-answer">', unsafe_allow_html=True)
    st.markdown(st.session_state.last_response)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="footer">
        Compliance & Disclaimer: Mutual Fund investments are subject to market risks.
        Read all scheme related documents carefully before investing. Sensitivity data
        is redacted via Privacy Guardrail.
        <div class="footer-links">
            <a href="#">Terms of Service</a>
            <a href="#">Privacy Policy</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
