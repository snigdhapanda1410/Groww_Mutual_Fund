"""Main Streamlit Application for Groww HDFC Mutual Fund Facts-Only Assistant."""

import sys
from pathlib import Path

# Ensure repository root is in sys.path when launched via `streamlit run ui/app.py`
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import streamlit as st

from src.config import config
from src.generation import answer_query
from src.state.models import AssistantResponse, Message
from src.state.session_manager import SessionManager
from ui.components import (
    render_assistant_message,
    render_disclaimer_banner,
    render_schemes_overview,
    render_sidebar_covered_schemes,
    render_user_message,
    render_welcome_hero,
)

# ------------------------------------------------------------------------------
# 1. Page Configuration
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title=config.app_title,
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# 2. Inject Custom Groww Dark Theme CSS
# ------------------------------------------------------------------------------
css_path = Path(__file__).parent / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 3. State & Session Manager Initialization
# ------------------------------------------------------------------------------
if "session_manager" not in st.session_state:
    st.session_state.session_manager = SessionManager()

sm: SessionManager = st.session_state.session_manager
active_thread = sm.get_active_thread()

# ------------------------------------------------------------------------------
# 4. Sidebar: Thread & Session Management
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-title">
            <span style="color: var(--accent-primary); font-size: 1.3rem;">📈</span> Groww
        </div>
        <div class="sidebar-subtitle">HDFC Facts Assistant</div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("➕ New Thread", use_container_width=True, type="primary"):
        new_t = sm.create_thread(title="New Conversation")
        st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<span style='font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;'>Saved Sessions</span>",
        unsafe_allow_html=True,
    )

    threads = sm.list_threads()
    for t in threads:
        is_active = active_thread and active_thread.thread_id == t.thread_id
        col_btn, col_del = st.columns([0.82, 0.18])
        with col_btn:
            label = f"{'🟢 ' if is_active else '💬 '}{t.title}"
            if st.button(
                label,
                key=f"thread_btn_{t.thread_id}",
                use_container_width=True,
                help=f"{t.message_count} messages | Last active: {t.last_active.strftime('%H:%M')}",
            ):
                sm.switch_thread(t.thread_id)
                st.rerun()

        with col_del:
            if st.button("🗑️", key=f"del_{t.thread_id}", help="Delete thread"):
                sm.delete_thread(t.thread_id)
                st.rerun()

    # API key status indicator
    has_api_key = bool(
        config.groq_api_key
        and config.groq_api_key != "your-groq-api-key-here"
        and not config.groq_api_key.startswith("mock_")
    )
    if has_api_key:
        st.markdown(
            """
            <div style="background: rgba(0, 208, 156, 0.08); border: 1px solid rgba(0, 208, 156, 0.25); border-radius: 8px; padding: 8px 12px; margin-top: 14px; font-size: 0.78rem;">
                <span style="color: var(--accent-primary); font-weight: 600;">● Groq API Connected</span>
                <div style="color: var(--text-muted); font-size: 0.72rem; margin-top: 2px;">Model: openai/gpt-oss-120b</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background: rgba(255, 183, 77, 0.08); border: 1px solid rgba(255, 183, 77, 0.3); border-radius: 8px; padding: 8px 12px; margin-top: 14px; font-size: 0.78rem;">
                <span style="color: #FFB74D; font-weight: 600;">⚠️ Groq API Key Not Set</span>
                <div style="color: var(--text-muted); font-size: 0.72rem; margin-top: 2px;">Set <code>GROQ_API_KEY</code> in <code>.env</code> to enable online LLM responses.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Bottom sidebar drawer: Covered schemes reference
    render_sidebar_covered_schemes()

# ------------------------------------------------------------------------------
# 5. Main Canvas: Regulatory Disclaimer Banner
# ------------------------------------------------------------------------------
render_disclaimer_banner()

# ------------------------------------------------------------------------------
# 6. Conversation Stream / Welcome View
# ------------------------------------------------------------------------------
history: list[Message] = sm.get_active_history()

def handle_prompt_submission(prompt_text: str):
    """Execute pipeline on user prompt and record to active thread."""
    if not prompt_text.strip():
        return
    # Add user message
    sm.add_message(role="user", content=prompt_text)

    # Invoke RAG pipeline
    with st.spinner("Looking up official HDFC factsheets..."):
        tid = active_thread.thread_id if active_thread else ""
        response: AssistantResponse = answer_query(prompt_text, thread_id=tid)

    # Add assistant response message
    pub_date_str = response.last_updated_date.strftime("%Y-%m-%d")
    sm.add_message(
        role="assistant",
        content=response.answer_text,
        citation_url=str(response.citation_url),
        last_updated=pub_date_str,
        is_refusal=response.is_refusal,
    )
    st.rerun()


if not history:
    # Render Welcome Screen
    render_welcome_hero()
    render_schemes_overview()

    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; margin-top: 10px;">
            <span style="color: var(--accent-primary); font-size: 1.1rem;">⚡</span>
            <span style="font-weight: 600; font-size: 1.05rem; color: var(--text-primary);">Popular Factual Inquiries</span>
            <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 6px;">Click to load query into facts parser</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Interactive Starter Query Chips Grid (2 rows x 3 columns)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(
            "⏱️ What is the exit load for HDFC Mid-Cap Fund?\n\n*Redemption windows • 1-year cutoff*",
            key="chip_1",
            use_container_width=True,
        ):
            handle_prompt_submission("What is the exit load for HDFC Mid-Cap Opportunities Fund?")

        if st.button(
            "🔓 Does HDFC Multi Cap have a lock-in period?\n\n*Statutory lock-in check vs ELSS*",
            key="chip_4",
            use_container_width=True,
        ):
            handle_prompt_submission("Does HDFC Multi Cap Fund have any lock-in period?")

    with col2:
        if st.button(
            "📊 What is the expense ratio of HDFC Small Cap?\n\n*Direct Total Expense Ratio (TER)*",
            key="chip_2",
            use_container_width=True,
        ):
            handle_prompt_submission("What is the expense ratio for HDFC Small Cap Fund Direct Growth?")

        if st.button(
            "🏛️ What is the stamp duty on Silver ETF FoF?\n\n*Statutory 0.005% stamp duty rate*",
            key="chip_5",
            use_container_width=True,
        ):
            handle_prompt_submission("What is the stamp duty on buying HDFC Silver ETF FoF units?")

    with col3:
        if st.button(
            "💰 What is the minimum SIP for HDFC Silver ETF FoF?\n\n*Mandate limits • ₹100 threshold*",
            key="chip_3",
            use_container_width=True,
        ):
            handle_prompt_submission("What is the minimum SIP amount for HDFC Silver ETF FoF?")

        if st.button(
            "📈 What benchmark index does HDFC Large & Mid track?\n\n*NIFTY LargeMidcap 250 TRI*",
            key="chip_6",
            use_container_width=True,
        ):
            handle_prompt_submission("What is the benchmark of HDFC Large and Mid Cap Fund?")

else:
    # Render Active Conversation Messages
    for msg in history:
        if msg.role == "user":
            render_user_message(msg.content)
        elif msg.role == "assistant":
            # Reconstruct response model for renderer
            from datetime import date
            try:
                pdate = date.fromisoformat(msg.last_updated) if msg.last_updated else date.today()
            except Exception:
                pdate = date.today()

            resp_obj = AssistantResponse(
                answer_text=msg.content,
                sentence_count=min(3, max(1, len(msg.content.split(".")) - 1)),
                citation_url=msg.citation_url or "https://groww.in/mutual-funds",
                last_updated_date=pdate,
                is_refusal=msg.is_refusal,
            )
            render_assistant_message(resp_obj)

# ------------------------------------------------------------------------------
# 7. Sticky Bottom Input Dock
# ------------------------------------------------------------------------------
user_query = st.chat_input("Ask a factual question about HDFC Mutual Fund schemes (e.g., exit load, TER, SIP minimum)...")
if user_query:
    handle_prompt_submission(user_query)
