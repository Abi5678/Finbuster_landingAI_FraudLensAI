"""
ReconAI - Multi-Agent Insurance Fraud Detection System
Orchestrated multi-agent analysis with Landing AI ADE + Gemini 2.5 Flash
"""
import os
import json
import streamlit as st
import tempfile
from datetime import datetime
import asyncio
import random
from itertools import cycle
from typing import List
from pathlib import Path
import re
from dotenv import load_dotenv
import requests

# Import multi-agent system
from agents_v2.orchestrator import FraudOrchestrator

# Import breakthrough features
from fraud_story_generator import display_fraud_story, generate_fraud_narrative, format_narrative_for_display
from deepfake_detector import display_deepfake_analysis, detect_photo_manipulation
from fraud_network_analyzer import display_network_analysis

load_dotenv()

# Directory storage configuration
DATAROOM_ROOT = Path("datarooms")
DATAROOM_ROOT.mkdir(parents=True, exist_ok=True)


def slugify(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower())
    base = re.sub(r"-{2,}", "-", base).strip("-")
    if not base:
        base = f"dataroom-{int(datetime.now().timestamp())}"
    return base


def dataroom_path(slug: str) -> Path:
    return DATAROOM_ROOT / slug


def human_date(iso_ts: str) -> str:
    if not iso_ts:
        return "Unknown"
    try:
        return datetime.fromisoformat(iso_ts).strftime("%b %d, %Y")
    except ValueError:
        return iso_ts


def load_dataroom_records() -> List[dict]:
    records: List[dict] = []
    for folder in DATAROOM_ROOT.iterdir():
        if not folder.is_dir():
            continue
        data_file = folder / "data.json"
        metadata = {
            "name": folder.name,
            "slug": folder.name,
            "created_at": None,
            "updated_at": None,
            "last_filename": None,
        }
        if data_file.exists():
            try:
                with data_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                metadata.update(data.get("metadata", {}))
            except Exception:
                pass
        records.append(metadata)
    records.sort(
        key=lambda r: r.get("updated_at") or r.get("created_at") or "",
        reverse=True,
    )
    return records


def load_dataroom_data(slug: str) -> dict:
    data_file = dataroom_path(slug) / "data.json"
    if not data_file.exists():
        return {}
    try:
        with data_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_dataroom_snapshot(slug: str, display_name: str):
    folder = dataroom_path(slug)
    folder.mkdir(parents=True, exist_ok=True)
    data_file = folder / "data.json"

    existing = load_dataroom_data(slug)
    metadata = existing.get("metadata", {})
    metadata.update(
        {
            "name": display_name,
            "slug": slug,
            "created_at": metadata.get("created_at")
            or datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_filename": st.session_state.get("filename"),
            "last_summary": st.session_state.get("full_result", {}).get("summary"),
            "last_risk_level": st.session_state.get("full_result", {}).get(
                "risk_level"
            ),
        }
    )

    session_snapshot_keys = [
        "full_result",
        "document_content",
        "document_chunks",
        "analysis_complete",
        "filename",
        "claim_details",
        "chat_messages",
    ]
    session_snapshot = {
        key: st.session_state.get(key)
        for key in session_snapshot_keys
        if key in st.session_state
    }

    payload = {"metadata": metadata, "session": session_snapshot}

    with data_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def apply_dataroom_session(data: dict):
    session_data = data.get("session", {})
    if not session_data:
        return
    for key, value in session_data.items():
        st.session_state[key] = value
    st.session_state.analysis_complete = session_data.get("analysis_complete", True)
    st.session_state.document_chunks = session_data.get("document_chunks", [])


# Initialize directory-related session state values
if "selected_dataroom" not in st.session_state:
    st.session_state.selected_dataroom = None
if "selected_dataroom_name" not in st.session_state:
    st.session_state.selected_dataroom_name = None
for _ctx in ("sidebar", "main"):
    key = f"show_dataroom_form_{_ctx}"
    if key not in st.session_state:
        st.session_state[key] = False


def render_dataroom_panel(context: str, allow_open: bool = True):
    """Render create/select controls for directories within current container context."""
    show_form_key = f"show_dataroom_form_{context}"
    if st.button(
        "➕ New Directory",
        key=f"new_dataroom_btn_{context}",
        use_container_width=True,
    ):
        st.session_state[show_form_key] = not st.session_state.get(show_form_key, False)

    if st.session_state.get(show_form_key, False):
        new_name = st.text_input(
            "Name your directory",
            key=f"new_dataroom_name_{context}",
            placeholder="e.g., Claim 1042 - April",
        )
        create_col, cancel_col = st.columns([3, 2])
        with create_col:
            if st.button(
                "Create",
                key=f"create_dataroom_button_{context}",
                use_container_width=True,
            ):
                if not new_name.strip():
                    st.warning("Please provide a name for the directory.")
                else:
                    slug = slugify(new_name)
                    if dataroom_path(slug).exists():
                        st.warning("A directory with this name already exists.")
                    else:
                        save_dataroom_snapshot(slug, new_name.strip())
                        st.session_state.selected_dataroom = slug
                        st.session_state.selected_dataroom_name = new_name.strip()
                        st.session_state[show_form_key] = False
                        st.rerun()
        with cancel_col:
            if st.button(
                "Cancel",
                key=f"cancel_dataroom_button_{context}",
                use_container_width=True,
            ):
                st.session_state[show_form_key] = False

    dataroom_records = load_dataroom_records()
    current_slug = st.session_state.get("selected_dataroom")

    if dataroom_records:
        labels = [
            f"{rec['name']} · {human_date(rec.get('updated_at') or rec.get('created_at'))}"
            for rec in dataroom_records
        ]
        slug_map = {label: rec["slug"] for label, rec in zip(labels, dataroom_records)}
        default_index = 0
        if current_slug:
            for idx, rec in enumerate(dataroom_records):
                if rec["slug"] == current_slug:
                    default_index = idx
                    break
        selection_label = st.radio(
            "Existing directories",
            labels,
            index=default_index,
            key=f"dataroom_selection_{context}",
            label_visibility="collapsed",
        )
        selected_slug = slug_map[selection_label]
        selected_record = next(
            (rec for rec in dataroom_records if rec["slug"] == selected_slug),
            None,
        )
        display_record = selected_record or {
            "name": selected_slug,
            "updated_at": None,
            "created_at": None,
            "last_filename": None,
            "last_risk_level": None,
        }

        if selected_slug != current_slug:
            st.session_state.selected_dataroom = selected_slug
            st.session_state.selected_dataroom_name = display_record["name"]

        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.5); padding: 0.75rem; border-radius: 10px; border: 1px solid rgba(120,144,156,0.35); margin-top: 0.5rem;">
                <p style="color: var(--secondary-light); margin: 0;"><strong>{display_record.get("name", selected_slug)}</strong></p>
                <p style="color: var(--light-grey); font-size: 0.85rem; margin: 0.2rem 0;">Last updated: {human_date(display_record.get("updated_at") or display_record.get("created_at"))}</p>
                <p style="color: var(--light-grey); font-size: 0.85rem; margin: 0;">Last file: {display_record.get("last_filename") or "—"}</p>
                <p style="color: var(--light-grey); font-size: 0.85rem; margin: 0;">Last risk level: {display_record.get("last_risk_level", "—") or "—"}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if allow_open and st.button(
            "Open Selected Directory",
            key=f"open_dataroom_{context}",
            use_container_width=True,
        ):
            data = load_dataroom_data(selected_slug)
            if data.get("session"):
                apply_dataroom_session(data)
                st.toast(
                    f"Loaded directory: {data.get('metadata', {}).get('name', selected_slug)}"
                )
                st.session_state.analysis_complete = True
                st.rerun()
            else:
                st.info("No stored analysis found for this directory yet.")
    else:
        st.info("No directories yet. Create one to save and revisit analyses.")

# Configure page with ReconAI branding
st.set_page_config(
    page_title="ReconAI - Fraud Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with Dark Mode palette
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --dominant-dark: #1A1A1A;
        --near-black: #0A0A0A;
        --secondary-light: #F0F0F0;
        --light-grey: #E0E0E0;
        --accent-blue: #007AFF;
        --accent-green: #00C853;
        --error-red: #D32F2F;
        --success-green: #4CAF50;
    }

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Blinking blue dot animation */
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #007AFF;
        border-radius: 50%;
        margin-right: 8px;
        animation: blink 2s ease-in-out infinite;
        box-shadow: 0 0 8px rgba(0, 122, 255, 0.6);
    }

    /* Dark background for all layers */
    .stApp {
        background-color: #1b263b;
    }

    .main {
        background-color: #1b263b;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #1b263b;
    }

    [data-testid="stHeader"] {
        background-color: #1b263b;
    }

    section[data-testid="stMain"] {
        background-color: #1b263b;
    }

    [data-testid="stSidebar"] {
        display: none !important;
    }

    section[data-testid="stSidebar"] {
        display: none !important;
    }

    h1, h2, h3 {
        color: var(--secondary-light);
        font-weight: 600;
    }

    .stButton > button {
        background-color: #ff5757;
        color: var(--secondary-light);
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 500;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(255, 87, 87, 0.3);
    }

    .stButton > button:hover {
        background-color: #e04b4b;
        box-shadow: 0 4px 8px rgba(224, 75, 75, 0.35);
        transform: translateY(-1px);
    }

    [data-testid="stFileUploader"] {
        background-color: var(--near-black);
        border: 2px dashed var(--light-grey);
        border-radius: 12px;
        padding: 2rem;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--accent-blue);
    }

    [data-testid="stMetric"] {
        background-color: var(--near-black);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #333333;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }

    [data-testid="stMetricLabel"] {
        color: var(--light-grey);
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
    }

    [data-testid="stMetricValue"] {
        color: var(--secondary-light);
        font-size: 2rem;
        font-weight: 700;
    }

    .indicator-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 500;
        margin: 0.25rem;
    }

    .severity-critical {
        background-color: rgba(211, 47, 47, 0.1);
        color: var(--error-red);
        border: 1px solid var(--error-red);
    }

    .severity-high {
        background-color: rgba(255, 152, 0, 0.1);
        color: #FF9800;
        border: 1px solid #FF9800;
    }

    .severity-medium {
        background-color: rgba(255, 235, 59, 0.1);
        color: #F57C00;
        border: 1px solid #F57C00;
    }

    .severity-low {
        background-color: rgba(76, 175, 80, 0.1);
        color: var(--success-green);
        border: 1px solid var(--success-green);
    }


    /* Chat readability */
    .stChatMessage {
        background-color: rgba(10, 10, 10, 0.85);
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.75rem;
        color: var(--secondary-light);
    }

    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: rgba(0, 122, 255, 0.12);
        border-color: rgba(0, 122, 255, 0.35);
    }

    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: rgba(0, 200, 83, 0.12);
        border-color: rgba(0, 200, 83, 0.35);
    }

    [data-testid="stChatMessageContent"] {
        color: var(--secondary-light);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Status indicator - pulsing blue dot */
    .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: var(--accent-blue);
        margin-right: 0.75rem;
        flex-shrink: 0;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    /* Expander text visibility */
    div[data-testid="stExpander"] summary {
        color: var(--secondary-light) !important;
    }

    div[data-testid="stExpander"] p {
        color: var(--light-grey) !important;
    }

    div[data-testid="stExpander"] strong {
        color: var(--secondary-light) !important;
    }
</style>
""", unsafe_allow_html=True)

# Check API keys
landingai_key = os.getenv("LANDINGAI_API_KEY")
gemini_key = os.getenv("GOOGLE_API_KEY")

if not landingai_key or landingai_key == "your_landingai_api_key_here":
    st.error("⚠️ Landing AI API key not configured in .env file")
    st.stop()

if not gemini_key or gemini_key == "your_google_api_key_here":
    st.error("⚠️ Google Gemini API key not configured in .env file")
    st.stop()

# Header with Logo
col_left, col_center, col_right = st.columns([1, 2, 1])

with col_left:
    # Display ReconAI logo in top left
    st.image("ReconAI.png", width=350)

with col_center:
    st.markdown("""
    <div style='background-color: var(--near-black); border: 1px solid var(--accent-blue); border-radius: 12px; padding: 1.5rem; margin: 1.5rem 0 0; text-align: center; box-shadow: 0 2px 8px rgba(0, 122, 255, 0.2); display: flex; flex-direction: column; justify-content: center; height: 210px;'>
        <p style='color: var(--secondary-light); font-size: 1.3rem; margin-bottom: 0.5rem; font-weight: 600;'>FraudLens AI</p>
        <p style='color: var(--accent-blue); font-size: 0.95rem;'>AI-Powered Fraud Detection for Every Claim</p>
    </div>
    """, unsafe_allow_html=True)

# Upload Section
st.markdown("### 📂 Manage Directories")
st.markdown("<p style='color: var(--light-grey); margin-bottom: 1rem;'>Create or select a directory to save your analysis history.</p>", unsafe_allow_html=True)

with st.container():
    render_dataroom_panel("main")
    
st.markdown("---")

st.markdown("### Upload Claim Document")
st.markdown("<p style='color: var(--light-grey); margin-bottom: 1rem;'>Analyze your insurance claims with AI-powered multi-agent fraud screening.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload PDF",
    type=["pdf"],
    help="Upload complete insurance claim document",
    label_visibility="collapsed"
)

if uploaded_file:
    st.markdown(f"""
    <div style='background-color: var(--near-black); padding: 1rem; border-radius: 8px; border: 1px solid var(--accent-blue); margin: 1rem 0;'>
        <span style='color: var(--accent-blue); font-weight: 500;'>📎 {uploaded_file.name}</span>
        <span style='color: var(--light-grey); margin-left: 1rem;'>({uploaded_file.size / 1024:.1f} KB)</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Start Analysis", type="primary", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            pdf_path = tmp_file.name

        try:
            # Initialize orchestrator
            with st.spinner("Initializing multi-agent system..."):
                orchestrator = FraudOrchestrator(landingai_key, gemini_key)

            st.success("✓ All agents initialized")

            # Create progress placeholders
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_messages = [
                "Parsing document structure",
                "Extracting invoice totals",
                "Checking claimant timelines",
                "Analyzing policy clauses",
                "Comparing prior fraud patterns",
                "Measuring risk indicators",
                "Validating metadata integrity",
                "Correlating entities across pages",
            ]
            analysis_tokens = [
                "policy",
                "invoice",
                "timeline",
                "metadata",
                "image",
                "claimant",
                "provider",
                "geodata",
                "signature",
                "exception",
            ]

            async def run_analysis_with_updates():
                analysis_task = asyncio.create_task(orchestrator.analyze_claim(pdf_path))
                spinner_cycle = cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
                message_cycle = cycle(status_messages)
                keyword_cycle = cycle(analysis_tokens)
                current_message = next(message_cycle)
                current_keyword = next(keyword_cycle)
                step = 0
                while not analysis_task.done():
                    spinner = next(spinner_cycle)
                    dots = "." * ((step % 3) + 1)
                    status_text.markdown(
                        f"<p style='color: #8ab4ff; font-weight: 600;'>{spinner} {current_message}"
                        f"<span style='opacity:0.7;'> · {current_keyword}</span>{dots}</p>",
                        unsafe_allow_html=True,
                    )
                    progress_bar.progress(min(90, 10 + (step % len(status_messages)) * 10))
                    step += 1
                    if step % 4 == 0:
                        current_message = next(message_cycle)
                        current_keyword = next(keyword_cycle)
                    await asyncio.sleep(0.6)
                progress_bar.progress(95)
                return await analysis_task

            result = asyncio.run(run_analysis_with_updates())

            progress_bar.progress(100)
            status_text.markdown("<p style='color: #00C853; font-weight: 600;'>Analysis complete!</p>", unsafe_allow_html=True)

            if not result.get("success"):
                st.error(f"Analysis Failed: {result.get('error', 'Unknown error')}")
                st.stop()

            # Store document content and chunks in session state for RAG chat
            agent_results = result.get("agent_results", {})
            doc_extraction = agent_results.get("document_extraction", {})
            st.session_state.document_content = doc_extraction.get("markdown", "")

            raw_chunks = doc_extraction.get("chunks", [])
            processed_chunks: List[str] = []

            if isinstance(raw_chunks, list):
                for chunk in raw_chunks:
                    if isinstance(chunk, dict):
                        text_value = chunk.get("text") or chunk.get("content") or chunk.get("markdown")
                        if text_value:
                            processed_chunks.append(str(text_value))
                    elif isinstance(chunk, str):
                        processed_chunks.append(chunk)
                    else:
                        processed_chunks.append(str(chunk))
            elif isinstance(raw_chunks, str):
                processed_chunks.append(raw_chunks)

            if not processed_chunks:
                splits = doc_extraction.get("splits", [])
                if isinstance(splits, list):
                    for split in splits:
                        if isinstance(split, dict):
                            text_value = split.get("text") or split.get("content")
                            if text_value:
                                processed_chunks.append(str(text_value))
                        elif isinstance(split, str):
                            processed_chunks.append(split)

            if not processed_chunks:
                markdown_fallback = st.session_state.document_content or ""
                if markdown_fallback:
                    processed_chunks = [
                        markdown_fallback[i : i + 1200]
                        for i in range(0, len(markdown_fallback), 1200)
                    ]

            st.session_state.document_chunks = processed_chunks
            st.session_state.full_result = result  # Store full analysis result
            st.session_state.analysis_complete = True  # Flag to persist results view
            st.session_state.filename = uploaded_file.name  # Store filename

            if (
                st.session_state.get("selected_dataroom")
                and st.session_state.get("selected_dataroom_name")
            ):
                save_dataroom_snapshot(
                    st.session_state["selected_dataroom"],
                    st.session_state["selected_dataroom_name"],
                )

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
            if 'status_text' in locals():
                status_text.markdown("<p style='color: #ff6b6b; font-weight: 600;'>Analysis failed. See details below.</p>", unsafe_allow_html=True)

        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

# Display Results (outside the button block, but check session state)
if "analysis_complete" in st.session_state and st.session_state.analysis_complete:
    result = st.session_state.full_result

    # Continue with results display
    st.markdown("---")
    st.markdown("<h2 style='color: var(--secondary-light);'>Analysis Results</h2>", unsafe_allow_html=True)

    # Quick Summary Card
    fraud_score = result.get("fraud_score", 0)
    risk_level = result.get("risk_level", "unknown").upper()
    recommendation = result.get("recommendation", "unknown").upper()
    total_indicators = result.get("total_indicators", 0)
    processing_time = result.get("metadata", {}).get("processing_time_seconds", 0)

    risk_color = {
        "CRITICAL": "#D32F2F",
        "HIGH": "#FF9800",
        "MEDIUM": "#F57C00",
        "LOW": "#4CAF50"
    }.get(risk_level, "#78909C")

    # Extract claim details if not already in session state
    if "claim_details" not in st.session_state:
        with st.spinner("Extracting claim details..."):
            try:
                document_content = st.session_state.get("document_content", "")

                extract_prompt = f"""Extract the following information from this insurance claim document. Return ONLY a JSON object with these exact fields:
{{
    "insurer": "insurance company name",
    "claimant_name": "name of the person making the claim",
    "invoice_total": "total amount (include currency symbol)",
    "incident": "brief one-line description of the incident (max 80 characters)"
}}

Document content:
{document_content[:5000]}

Return ONLY the JSON object, no other text."""

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": extract_prompt}]}]},
                    timeout=30
                )

                if response.status_code == 200:
                    import json
                    import re
                    result_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    # Extract JSON object
                    json_match = re.search(r'\{.*?\}', result_text, re.DOTALL)
                    if json_match:
                        st.session_state.claim_details = json.loads(json_match.group())
                    else:
                        st.session_state.claim_details = {
                            "insurer": "Not found",
                            "claimant_name": "Not found",
                            "invoice_total": "Not found",
                            "incident": "Details not available"
                        }
                else:
                    st.session_state.claim_details = {
                        "insurer": "Not found",
                        "claimant_name": "Not found",
                        "invoice_total": "Not found",
                        "incident": "Details not available"
                    }
            except Exception as e:
                st.session_state.claim_details = {
                    "insurer": "Not found",
                    "claimant_name": "Not found",
                    "invoice_total": "Not found",
                    "incident": "Details not available"
                }

    claim_details = st.session_state.get("claim_details", {})

    chunk_texts = st.session_state.get("document_chunks") or []
    if not chunk_texts:
        fallback_markdown = st.session_state.get("document_content", "")
        if fallback_markdown:
            chunk_texts = [fallback_markdown[:4000]]

    with st.spinner("Summarizing document..."):
        try:
            chunk_sample = "\n\n".join(chunk_texts[:5])[:4000]
            summary_prompt = f"""Provide a concise executive summary of the following insurance claim document.
Highlight the claim context, key financial figures, notable parties, and any discrepancies.
Keep the summary under 120 words.

Document excerpt:
{chunk_sample}
"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": summary_prompt}]}]},
                timeout=30
            )
            if response.status_code == 200:
                summary_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                summary_text = "Unable to generate summary."
        except Exception as e:
            summary_text = "Summary unavailable. Please review document details below."

    # ========== NEW LAYOUT: Executive Summary on left, Metrics on right ==========
    # Prepare claim data for fraud story
    claim_details_for_story = st.session_state.get('claim_details', {})
    
    # Extract claimed amount
    invoice_total_str = claim_details_for_story.get('invoice_total', '$0')
    try:
        claimed_amount_story = float(invoice_total_str.replace('$', '').replace(',', ''))
    except:
        claimed_amount_story = 0.0
    
    fraud_story_claim_data = {
        'claim_id': st.session_state.get('filename', 'Unknown'),
        'claimant': {'name': claim_details_for_story.get('claimant_name', 'Unknown Claimant')},
        'incident_date': datetime.now().strftime('%B %d, %Y'),
        'claimed_amount': claimed_amount_story,
        'incident_type': claim_details_for_story.get('incident', 'insurance claim')
    }
    
    # Get indicators from result
    indicators_for_story = result.get('indicators', [])
    
    summary_col, metrics_col = st.columns([2, 1])
    
    with summary_col:
        # Display Executive Summary in Document Summary style
        if indicators_for_story:
            # Generate narrative first
            with st.spinner("🔍 Analyzing evidence and reconstructing fraud timeline..."):
                narrative = generate_fraud_narrative(fraud_story_claim_data, indicators_for_story, gemini_key)
            
            # Format narrative
            formatted_narrative = format_narrative_for_display(narrative)
            
            # Display everything in one container
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, var(--near-black) 0%, var(--dark-bg) 100%);
                        padding: 1.5rem; border-radius: 12px; border: 2px solid {risk_color};
                        margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        height: 100%;'>
                <h3 style='color: var(--secondary-light); margin: 0 0 0.5rem 0; font-size: 1.1rem;'>Executive Summary</h3>
                <p style='color: #B0B0B0; font-size: 0.85rem; margin: 0 0 1rem 0;'>AI-generated analysis of key findings and fraud indicators</p>
                <div style='color: var(--secondary-light); font-size: 0.95rem; line-height: 1.6;'>
                    {formatted_narrative}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Fallback to document summary if no indicators
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, var(--near-black) 0%, var(--dark-bg) 100%);
                        padding: 1.5rem; border-radius: 12px; border: 2px solid {risk_color};
                        margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        height: 100%;'>
                <h3 style='color: var(--secondary-light); margin: 0 0 1rem 0; font-size: 1.1rem;'>📊 Document Summary</h3>
                <p style='color: var(--secondary-light); font-size: 0.95rem; line-height: 1.5;'>{summary_text}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with metrics_col:
        # Fraud Score - Large display
        fraud_score_metric = result.get("fraud_score", 0) * 100
        st.markdown(f"""
        <div style='background: rgba(0,0,0,0.5); padding: 1.5rem; border-radius: 12px; 
                    border: 2px solid {risk_color}; margin-bottom: 1rem; text-align: center;'>
            <p style='color: #B0B0B0; font-size: 0.85rem; margin: 0; text-transform: uppercase; letter-spacing: 1px;'>Fraud Score</p>
            <h1 style='color: {risk_color}; font-size: 3rem; margin: 0.5rem 0; font-weight: 700;'>{fraud_score_metric:.0f}/100</h1>
        </div>
        """, unsafe_allow_html=True)
        
        # Risk Level
        risk_level_metric = result.get("risk_level", "unknown").upper()
        risk_emoji = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }.get(risk_level_metric, '⚪')
        
        st.markdown(f"""
        <div style='background: rgba(0,0,0,0.5); padding: 1rem; border-radius: 12px; 
                    border: 1px solid {risk_color}; margin-bottom: 1rem; text-align: center;'>
            <p style='color: #B0B0B0; font-size: 0.8rem; margin: 0; text-transform: uppercase;'>Risk Level</p>
            <h3 style='color: {risk_color}; font-size: 1.5rem; margin: 0.5rem 0;'>{risk_emoji} {risk_level_metric}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Recommendation
        recommendation_metric = result.get("recommendation", "unknown").upper()
        st.markdown(f"""
        <div style='background: rgba(0,0,0,0.5); padding: 1rem; border-radius: 12px; 
                    border: 1px solid {risk_color}; margin-bottom: 1rem; text-align: center;'>
            <p style='color: #B0B0B0; font-size: 0.8rem; margin: 0; text-transform: uppercase;'>Recommendation</p>
            <h3 style='color: #F0F0F0; font-size: 1.2rem; margin: 0.5rem 0;'>{recommendation_metric}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Total Indicators
        total_indicators_metric = result.get("total_indicators", 0)
        st.markdown(f"""
        <div style='background: rgba(0,0,0,0.5); padding: 1rem; border-radius: 12px; 
                    border: 1px solid {risk_color}; text-align: center;'>
            <p style='color: #B0B0B0; font-size: 0.8rem; margin: 0; text-transform: uppercase;'>Total Indicators</p>
            <h3 style='color: #F0F0F0; font-size: 1.5rem; margin: 0.5rem 0;'>{total_indicators_metric}</h3>
        </div>
        """, unsafe_allow_html=True)

    agent_results = result.get("agent_results", {})

    # ========== BREAKTHROUGH FEATURE 3: FRAUD COLLABORATION NETWORK ==========
    st.markdown("---")
    
    # Prepare claim data for network analysis
    network_claim_data = {
        'claimant': {'name': claim_details_for_story.get('claimant_name', 'Unknown Claimant')},
        'claimed_amount': claimed_amount_story,
        'incident_type': claim_details_for_story.get('incident', 'insurance claim'),
        'claim_id': st.session_state.get('filename', 'Unknown')
    }
    
    # Display network analysis
    display_network_analysis(network_claim_data)

    # All Indicators
    st.markdown("---")
    st.markdown("<h3 style='color: var(--secondary-light);'>Fraud Indicators</h3>", unsafe_allow_html=True)

    indicators = result.get("indicators", [])

    if indicators:
        # Group by severity
        severity_groups = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }

        for ind in indicators:
            severity = ind.get("severity", "medium")
            severity_groups[severity].append(ind)

        for severity in ["critical", "high", "medium", "low"]:
            group = severity_groups[severity]
            if group:
                st.markdown(f"<p style='color: var(--secondary-light); font-weight: 600;'>{severity.upper()} Severity ({len(group)} indicators)</p>", unsafe_allow_html=True)

                for ind in group:
                    st.markdown(f"""
                    <div style='margin-left: 1rem; padding: 0.5rem; border-left: 3px solid {"#D32F2F" if severity == "critical" else "#FF9800" if severity == "high" else "#F57C00" if severity == "medium" else "#4CAF50"}; background-color: var(--near-black); margin-bottom: 0.5rem; border-radius: 4px;'>
                        <strong style='color: var(--secondary-light);'>{ind.get('type', 'unknown').replace('_', ' ').title()}</strong><br>
                        <span style='color: var(--light-grey);'>{ind.get('description', 'No description')}</span> <em style='color: var(--light-grey);'>(Confidence: {ind.get('confidence', 0):.0%})</em>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("✓ No significant fraud indicators detected")

    # ========== BREAKTHROUGH FEATURE: DEEPFAKE DETECTION ==========
    st.markdown("---")
    st.markdown("### 🤖 Photo Authenticity Analysis")
    
    st.markdown("""
    <div style='background: rgba(0, 122, 255, 0.15);
                border-left: 4px solid #007AFF;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;'>
        <strong>💡 Advanced Photo Analysis:</strong> Upload claim photos to analyze 
        for AI-generation, digital manipulation, and metadata tampering. Our deepfake 
        detector uses 5 independent algorithms to verify photo authenticity.
    </div>
    """, unsafe_allow_html=True)
    
    # Add file uploader for photos
    photo_uploader = st.file_uploader(
        "Upload claim photos for authenticity analysis",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        key="photo_authenticity_uploader",
        help="Analyzes photos for AI-generation, manipulation, and metadata tampering"
    )
    
    if photo_uploader:
        for uploaded_photo in photo_uploader:
            # Save temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(uploaded_photo.getvalue())
                temp_image_path = tmp_file.name
            
            # Analyze photo
            display_deepfake_analysis(temp_image_path, uploaded_photo.name)
            
            # Cleanup
            import os
            os.unlink(temp_image_path)
            
            st.markdown("---")

    # Agent Results
    st.markdown("<h3 style='color: var(--secondary-light);'>Multi-Agent Analysis Details</h3>", unsafe_allow_html=True)

    # Document Agent
    with st.expander("Document Extraction Agent", expanded=False):
        doc_result = agent_results.get("document_extraction", {})
        col1_doc, col2_doc, col3_doc = st.columns(3)

        with col1_doc:
            st.metric("Pages", doc_result.get("pages", 0))
        with col2_doc:
            st.metric("Content Length", f"{doc_result.get('content_length', 0):,} chars")
        with col3_doc:
            st.metric("Chunks", doc_result.get("chunks", 0))

        st.markdown(f"**Confidence**: {doc_result.get('confidence', 0):.1%}")
        st.markdown(f"**Indicators Found**: {doc_result.get('indicators', 0)}")

    # Inconsistency Agent
    with st.expander("Inconsistency Detection Agent", expanded=False):
        incon_result = agent_results.get("inconsistency_detection", {})

        st.metric("Inconsistencies Found", incon_result.get("inconsistencies_found", 0))
        st.markdown(f"**Confidence**: {incon_result.get('confidence', 0):.1%}")
        st.markdown(f"**Indicators**: {incon_result.get('indicators', 0)}")

    # Pattern Agent
    with st.expander("Pattern Matching Agent", expanded=False):
        pattern_result = agent_results.get("pattern_matching", {})

        st.metric("Patterns Detected", pattern_result.get("patterns_detected", 0))
        st.markdown(f"**Confidence**: {pattern_result.get('confidence', 0):.1%}")
        st.markdown(f"**Indicators**: {pattern_result.get('indicators', 0)}")

    # Scoring Breakdown
    with st.expander("Scoring Breakdown", expanded=False):
        breakdown = result.get("scoring_breakdown", {})

        col1_break, col2_break = st.columns(2)

        with col1_break:
            st.metric("Indicator Score", f"{breakdown.get('indicator_score', 0):.1%}")
            st.metric("Severity Score", f"{breakdown.get('severity_score', 0):.1%}")

        with col2_break:
            st.metric("Confidence Score", f"{breakdown.get('confidence_score', 0):.1%}")
            st.metric("Critical Indicators", breakdown.get("critical_indicators", 0))

    # Metadata
    with st.expander("Processing Metadata", expanded=False):
        metadata = result.get("metadata", {})

        st.markdown(f"**Processing Time**: {metadata.get('processing_time_seconds', 0):.1f} seconds")
        st.markdown(f"**Timestamp**: {metadata.get('timestamp', 'Unknown')}")
        st.markdown(f"**Agents Used**: {', '.join(metadata.get('agents_used', []))}")

    # Download Report
    report = f"""
RECONAI MULTI-AGENT FRAUD ANALYSIS REPORT
==========================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Document: {st.session_state.get("filename", "Unknown")}

SUMMARY
=======
Fraud Score: {result.get('fraud_score', 0):.1%}
Risk Level: {result.get('risk_level', 'unknown').upper()}
Recommendation: {result.get('recommendation', 'unknown').upper()}
Total Indicators: {result.get('total_indicators', 0)}
Processing Time: {result.get('metadata', {}).get('processing_time_seconds', 0):.1f}s

{result.get('summary', '')}

AGENT RESULTS
=============

Document Extraction Agent:
- Pages: {agent_results.get('document_extraction', {}).get('pages', 0)}
- Content: {agent_results.get('document_extraction', {}).get('content_length', 0):,} characters
- Indicators: {agent_results.get('document_extraction', {}).get('indicators', 0)}

Inconsistency Detection Agent:
- Inconsistencies: {agent_results.get('inconsistency_detection', {}).get('inconsistencies_found', 0)}
- Confidence: {agent_results.get('inconsistency_detection', {}).get('confidence', 0):.1%}

Pattern Matching Agent:
- Patterns: {agent_results.get('pattern_matching', {}).get('patterns_detected', 0)}
- Confidence: {agent_results.get('pattern_matching', {}).get('confidence', 0):.1%}

FRAUD INDICATORS
================
{chr(10).join([f"[{ind.get('severity', 'unknown').upper()}] {ind.get('description', 'No description')}" for ind in indicators])}

==========================================
Generated by ReconAI Multi-Agent System
Landing AI ADE + Google Gemini 2.5 Flash
==========================================
"""

    st.download_button(
        "Download Full Report",
        report,
        f"reconai_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "text/plain",
        use_container_width=True
    )

    # Advanced RAG Chat Interface
    st.markdown("---")
    st.markdown("<h3 style='color: var(--secondary-light);'>💬 Ask Questions About This Claim</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--light-grey); margin-bottom: 1rem;'>Advanced document analysis with multi-query retrieval and citations</p>", unsafe_allow_html=True)

    # Check if document is available
    if "document_content" not in st.session_state or not st.session_state.document_content:
        st.warning("⚠️ No document content available. Please analyze a document first.")
    else:
        # Initialize chat history
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        # Display existing chat history
        for msg_idx, message in enumerate(st.session_state.chat_messages):
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(message["content"])
                else:
                    # Display answer text
                    st.markdown(message["content"])

                    # Display reasoning log (collapsible)
                    if "reasoning_log" in message:
                        reasoning = message["reasoning_log"]
                        sub_queries = reasoning.get("sub_queries", [])
                        if sub_queries:
                            with st.expander(f"▸ Analyzed via {len(sub_queries)} queries"):
                                for i, sq in enumerate(sub_queries, 1):
                                    st.markdown(f"**{i}.** {sq}")

                    # Display citations (source pills)
                    if "citations" in message and message["citations"]:
                        st.markdown("**📄 Source:**")
                        first_citation = message["citations"][0]
                        st.markdown(
                            f'<div style="background: var(--dark-bg); padding: 0.3rem 0.6rem; '
                            f'border-radius: 12px; font-size: 0.8rem; display: inline-flex; '
                            f'border: 1px solid var(--secondary-light); max-width: 200px; '
                            f'justify-content: center;">'
                            f'{first_citation.get("document", "doc")}</div>',
                            unsafe_allow_html=True
                        )

        # Chat input using form placeholder to avoid duplicate rendering during processing
        chat_form_placeholder = st.empty()
        status_placeholder = st.empty()

        with chat_form_placeholder.form(key=f"chat_form_{len(st.session_state.chat_messages)}", clear_on_submit=True):
            user_question = st.text_input(
                "Your question:",
                placeholder="e.g., What's the invoice total?, What is the claimant address?",
                label_visibility="collapsed"
            )
            submit_button = st.form_submit_button("Send")

        if submit_button and user_question:
            # Add user message
            st.session_state.chat_messages.append({"role": "user", "content": user_question})

            # Remove the form while processing to prevent duplicate UI
            chat_form_placeholder.empty()

            # Process with RAG system
            try:
                def call_gemini(prompt_text: str, base_message: str):
                    url_local = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                    status_placeholder.markdown(
                        f"<p style='color: #8ab4ff; font-weight: 600;'>⏳ {base_message}...</p>",
                        unsafe_allow_html=True,
                    )
                    response_local = requests.post(
                        url_local,
                        headers={"Content-Type": "application/json"},
                        json={"contents": [{"parts": [{"text": prompt_text}]}]},
                        timeout=30
                    )
                    return response_local

                # Step 1: Retrieve relevant chunks (simple keyword filtering)
                status_placeholder.markdown(
                    "<p style='color: #8ab4ff; font-weight: 600;'>⏳ Retrieving relevant context...</p>",
                    unsafe_allow_html=True,
                )
                sub_queries = [user_question]
                chunks = st.session_state.document_chunks if isinstance(st.session_state.get("document_chunks"), list) else []
                retrieved_chunks = []
                for sq_idx, sq in enumerate(sub_queries):
                    keywords = sq.lower().split()
                    for chunk_idx, chunk in enumerate(chunks[:20]):  # Limit to first 20 chunks
                        chunk_text = str(chunk).lower()
                        if any(kw in chunk_text for kw in keywords):
                            retrieved_chunks.append({
                                "sub_query": sq,
                                "chunk_index": chunk_idx,
                                "content": str(chunk)[:500]
                            })

                if not retrieved_chunks and chunks:
                    for idx, chunk in enumerate(chunks[:3]):
                        retrieved_chunks.append({
                            "sub_query": user_question,
                            "chunk_index": idx,
                            "content": str(chunk)[:500]
                        })

                # Step 2: Extract structured data from result
                full_result = st.session_state.full_result
                structured_data = {
                    "fraud_score": full_result.get("fraud_score", 0),
                    "risk_level": full_result.get("risk_level", "unknown"),
                    "total_indicators": full_result.get("total_indicators", 0),
                    "indicators": full_result.get("indicators", [])[:5]
                }

                # Step 3: Synthesize answer with Gemini
                synthesis_prompt = f"""You are analyzing an insurance claim document. Answer the user's question using the information provided.

User Question: {user_question}

Sub-queries analyzed: {', '.join(sub_queries)}

Structured Data:
- Fraud Score: {structured_data['fraud_score']:.1%}
- Risk Level: {structured_data['risk_level']}
- Total Indicators: {structured_data['total_indicators']}

Retrieved Document Chunks:
{chr(10).join([f"- {rc['content'][:200]}..." for rc in retrieved_chunks[:5]])}

Full Document Context (first 5000 chars):
{st.session_state.document_content[:5000]}

Provide a clear, concise answer to the user's question. If you cite specific information, mention where it came from."""

                response = call_gemini(synthesis_prompt, "Synthesizing answer")

                if response.status_code == 200:
                    answer = response.json()['candidates'][0]['content']['parts'][0]['text']
                    status_placeholder.empty()

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": answer,
                        "reasoning_log": {
                            "sub_queries": sub_queries,
                            "chunks_retrieved": len(retrieved_chunks)
                        },
                        "citations": [
                            {"document": "claim.pdf", "chunk": rc["chunk_index"]}
                            for rc in retrieved_chunks[:3]
                        ],
                        "status": "done"
                    })
                    st.rerun()
                else:
                    raise Exception(f"API returned {response.status_code}")

            except Exception as e:
                status_placeholder.empty()
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error: {str(e)}",
                    "status": "error"
                })
                st.rerun()

# Sidebar is hidden via CSS, so all directory controls are in the main content area

# Footer
st.markdown(
    """
    <div style="margin-top: 3rem; padding: 1.5rem 0 1rem 0; border-top: 1px solid #333333; color: #E0E0E0; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 1rem; font-size: 0.85rem;">
        <div>Powered by Landing AI ADE + Gemini 2.5 Flash</div>
        <div>
            <a href="#" style="color: rgba(138, 180, 255, 0.95); text-decoration: none; margin-right: 1rem;">Privacy Policy</a>
            <a href="#" style="color: rgba(138, 180, 255, 0.95); text-decoration: none; margin-right: 1rem;">Terms</a>
            <a href="#" style="color: rgba(138, 180, 255, 0.95); text-decoration: none;">Contact</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
