"""Reusable UI components rendering the Groww Obsidian Emerald dark theme interface."""

import html
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import streamlit as st

from src.state.models import AssistantResponse, Message, ThreadSummary


def render_disclaimer_banner() -> None:
    """Render the fixed top regulatory compliance banner."""
    html_code = """
    <div class="disclaimer-banner">
        <div class="disclaimer-content">
            <span class="disclaimer-badge">SEBI Compliance</span>
            <span>Facts-only financial assistant. No investment advice, recommendations, or predictions.</span>
        </div>
        <div class="coverage-pill">
            <span class="coverage-dot"></span>
            <span>Coverage: 5 HDFC Direct-Growth Schemes</span>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_welcome_hero() -> None:
    """Render welcome title and trust metrics."""
    html_code = """
    <div class="hero-container">
        <div class="hero-pill">
            <span>●</span> Groww AI • Grounded Financial Factsheets
        </div>
        <h1 class="hero-title">
            Groww HDFC Mutual Fund <span class="hero-gradient">Facts Assistant</span>
        </h1>
        <p class="hero-subtitle">
            Instant, official financial parameters directly grounded in Groww scheme factsheets and regulatory filings. Zero speculation, 100% verified facts.
        </p>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_schemes_overview() -> None:
    """Render the 5 covered HDFC scheme snapshot cards."""
    html_code = """
    <div class="schemes-section">
        <div class="section-header">
            <h2 class="section-title">Covered HDFC Direct Schemes</h2>
            <span style="font-size: 0.8rem; color: var(--accent-primary);">● Verified Factsheets</span>
        </div>
        <div class="schemes-grid">
            <div class="scheme-card">
                <div>
                    <div class="scheme-header">
                        <span class="category-tag">Mid Cap</span>
                        <span class="risk-tag risk-high">High Risk</span>
                    </div>
                    <div class="scheme-name">HDFC Mid-Cap Opportunities Fund</div>
                    <div class="scheme-plan">Direct Plan • Growth</div>
                    <div class="scheme-nav-block">
                        <span class="scheme-nav">₹198.42</span>
                        <span class="scheme-change">+0.84%</span>
                    </div>
                </div>
                <div class="scheme-metrics-table">
                    <div class="metric-row"><span class="metric-label">Direct TER</span><span class="metric-value">0.74%</span></div>
                    <div class="metric-row"><span class="metric-label">Exit Load</span><span class="metric-value">1.0% (&lt;1Y)</span></div>
                    <div class="metric-row"><span class="metric-label">AUM</span><span class="metric-value" style="color: var(--accent-primary);">₹68,420 Cr</span></div>
                </div>
            </div>
            <div class="scheme-card">
                <div>
                    <div class="scheme-header">
                        <span class="category-tag">Small Cap</span>
                        <span class="risk-tag risk-very-high">Very High Risk</span>
                    </div>
                    <div class="scheme-name">HDFC Small Cap Fund</div>
                    <div class="scheme-plan">Direct Plan • Growth</div>
                    <div class="scheme-nav-block">
                        <span class="scheme-nav">₹142.15</span>
                        <span class="scheme-change">+1.12%</span>
                    </div>
                </div>
                <div class="scheme-metrics-table">
                    <div class="metric-row"><span class="metric-label">Direct TER</span><span class="metric-value">0.68%</span></div>
                    <div class="metric-row"><span class="metric-label">Exit Load</span><span class="metric-value">1.0% (&lt;1Y)</span></div>
                    <div class="metric-row"><span class="metric-label">AUM</span><span class="metric-value" style="color: var(--accent-primary);">₹32,150 Cr</span></div>
                </div>
            </div>
            <div class="scheme-card">
                <div>
                    <div class="scheme-header">
                        <span class="category-tag">Large & Mid</span>
                        <span class="risk-tag risk-high">High Risk</span>
                    </div>
                    <div class="scheme-name">HDFC Large and Mid Cap Fund</div>
                    <div class="scheme-plan">Direct Plan • Growth</div>
                    <div class="scheme-nav-block">
                        <span class="scheme-nav">₹284.90</span>
                        <span class="scheme-change">+0.42%</span>
                    </div>
                </div>
                <div class="scheme-metrics-table">
                    <div class="metric-row"><span class="metric-label">Direct TER</span><span class="metric-value">0.81%</span></div>
                    <div class="metric-row"><span class="metric-label">Exit Load</span><span class="metric-value">1.0% (&lt;1Y)</span></div>
                    <div class="metric-row"><span class="metric-label">AUM</span><span class="metric-value" style="color: var(--accent-primary);">₹21,800 Cr</span></div>
                </div>
            </div>
            <div class="scheme-card">
                <div>
                    <div class="scheme-header">
                        <span class="category-tag">Silver FoF</span>
                        <span class="risk-tag risk-very-high">Very High Risk</span>
                    </div>
                    <div class="scheme-name">HDFC Silver ETF Fund of Fund</div>
                    <div class="scheme-plan">Direct Plan • Growth</div>
                    <div class="scheme-nav-block">
                        <span class="scheme-nav">₹18.64</span>
                        <span class="scheme-change">+2.15%</span>
                    </div>
                </div>
                <div class="scheme-metrics-table">
                    <div class="metric-row"><span class="metric-label">Direct TER</span><span class="metric-value">0.35%</span></div>
                    <div class="metric-row"><span class="metric-label">Exit Load</span><span class="metric-value" style="color: var(--accent-primary);">Nil (0%)</span></div>
                    <div class="metric-row"><span class="metric-label">Min SIP</span><span class="metric-value">₹100</span></div>
                </div>
            </div>
            <div class="scheme-card">
                <div>
                    <div class="scheme-header">
                        <span class="category-tag">Multi Cap</span>
                        <span class="risk-tag risk-very-high">Very High Risk</span>
                    </div>
                    <div class="scheme-name">HDFC Multi Cap Fund</div>
                    <div class="scheme-plan">Direct Plan • Growth</div>
                    <div class="scheme-nav-block">
                        <span class="scheme-nav">₹19.38</span>
                        <span class="scheme-change">+0.65%</span>
                    </div>
                </div>
                <div class="scheme-metrics-table">
                    <div class="metric-row"><span class="metric-label">Direct TER</span><span class="metric-value">0.79%</span></div>
                    <div class="metric-row"><span class="metric-label">Lock-in</span><span class="metric-value" style="color: var(--accent-primary);">Nil</span></div>
                    <div class="metric-row"><span class="metric-label">Min Lumpsum</span><span class="metric-value">₹100</span></div>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_user_message(content: str) -> None:
    """Render right-aligned user bubble."""
    safe_content = html.escape(content).replace("\n", "<br/>")
    html_code = f"""
    <div class="message-container">
        <div class="user-bubble">
            <div class="user-label">Investor Query</div>
            <div>{safe_content}</div>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_assistant_message(response: AssistantResponse) -> None:
    """Render compliant assistant factual answer card or refusal card."""
    if response.is_refusal:
        render_refusal_card(response.answer_text)
        return

    # Strip raw markdown artifacts from content for clean card rendering
    body = response.answer_text.split("**Source**:")[0].split("*Last updated")[0].strip()
    # Strip any inline markdown links or URL references (e.g. [GrowwPage](...), {GrowwPage], etc.)
    body = re.sub(r"[\[{\(【]\s*Groww[^\n\]}\)]*[\]}\)](\([^\)]*\))?.*", "", body, flags=re.I)
    body = re.sub(r"[\[【{][^\]】}]*[\]】}]\([^\)]*\)?", "", body)
    body = re.sub(r"【[^】]*】", "", body)
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"\s+([.,;:!?])", r"\1", body)
    body = re.sub(r"\s{2,}", " ", body).strip()

    safe_body = html.escape(body).replace("\n", "<br/>")
    citation_url = str(response.citation_url)
    date_str = response.last_updated_date.strftime("%Y-%m-%d")

    html_code = f"""
    <div class="message-container">
        <div class="assistant-card">
            <div class="assistant-header">
                <span class="engine-pill">Groww Facts Engine</span>
                <span>• Grounded Verification</span>
            </div>
            <div class="answer-body">
                {safe_body}
            </div>
            <div class="citation-strip">
                <a href="{citation_url}" target="_blank" class="citation-badge">
                    <span>🔗 Groww Scheme Page ↗</span>
                </a>
                <span class="freshness-footer">
                    Last updated from sources: {date_str}
                </span>
            </div>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_refusal_card(content: str) -> None:
    """Render amber/coral refusal card with educational redirect links."""
    safe_content = html.escape(content).replace("\n", "<br/>")
    html_code = f"""
    <div class="message-container">
        <div class="refusal-card">
            <div class="refusal-header">
                <span>🛡️ Compliance Notice: Advice & Out-of-Scope Prohibited</span>
            </div>
            <div class="refusal-body">
                {safe_content}
            </div>
            <div class="refusal-links">
                <a href="https://www.amfiindia.com/investor-corner/knowledge-center" target="_blank" class="refusal-link">
                    ↗ AMFI Investor Knowledge Center
                </a>
                <a href="https://www.sebi.gov.in/investor.html" target="_blank" class="refusal-link">
                    ↗ SEBI Investor Portal
                </a>
            </div>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


def render_sidebar_covered_schemes() -> None:
    """Render covered schemes list in sidebar."""
    html_code = """
    <div class="covered-schemes-box">
        <div class="covered-schemes-title">
            <span>Covered Schemes</span>
            <span style="color: var(--accent-primary);">5 Active</span>
        </div>
        <div class="covered-scheme-item"><span style="color: var(--accent-primary);">●</span> HDFC Mid-Cap Opps Fund</div>
        <div class="covered-scheme-item"><span style="color: var(--accent-primary);">●</span> HDFC Small Cap Fund</div>
        <div class="covered-scheme-item"><span style="color: var(--accent-primary);">●</span> HDFC Large & Mid Cap Fund</div>
        <div class="covered-scheme-item"><span style="color: var(--accent-primary);">●</span> HDFC Silver ETF FoF</div>
        <div class="covered-scheme-item"><span style="color: var(--accent-primary);">●</span> HDFC Multi Cap Fund</div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)
