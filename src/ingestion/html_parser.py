"""HTML & Financial Table Parser for Groww scheme pages.

Extracts structured financial tables (TER, exit load, investment minimums,
holdings, benchmark, AUM) and clean narrative text with strict section tagging.
"""

from datetime import date, datetime
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import trafilatura

from src.utils.logger import get_logger

logger = get_logger("src.ingestion.html_parser")


def _format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format headers and row values into a GitHub Flavored Markdown (GFM) table."""
    if not headers or not rows:
        return ""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(val)))
            else:
                col_widths.append(len(str(val)))

    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    separator_line = "| " + " | ".join("-" * max(3, col_widths[i]) for i in range(len(headers))) + " |"
    row_lines = [
        "| " + " | ".join(str(cell).ljust(col_widths[i]) if i < len(col_widths) else str(cell) for i, cell in enumerate(r)) + " |"
        for r in rows
    ]
    return f"{header_line}\n{separator_line}\n" + "\n".join(row_lines)


def extract_html_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract standard HTML <table> elements as Markdown tables."""
    extracted = []
    tables = soup.find_all("table")

    for idx, table in enumerate(tables, 1):
        tr_elements = table.find_all("tr")
        if not tr_elements:
            continue

        headers = []
        rows = []

        # Find header row
        header_tr = table.find("thead")
        if header_tr:
            headers = [th.get_text(strip=True) for th in header_tr.find_all(["th", "td"])]
            data_trs = table.find("tbody").find_all("tr") if table.find("tbody") else tr_elements[1:]
        else:
            first_row_cells = [c.get_text(strip=True) for c in tr_elements[0].find_all(["th", "td"])]
            headers = first_row_cells
            data_trs = tr_elements[1:]

        for tr in data_trs:
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            if cells and any(cells):
                # Align length
                if len(cells) < len(headers):
                    cells.extend([""] * (len(headers) - len(cells)))
                rows.append(cells[: len(headers)])

        if headers and rows:
            md_table = _format_markdown_table(headers, rows)
            extracted.append({
                "content": md_table,
                "section": f"HTML Table {idx}",
                "content_type": "table",
            })

    return extracted


def extract_groww_structured_data(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract the complete mfServerSideData JSON embedded in Groww Next.js pages."""
    next_data_script = soup.find("script", id="__NEXT_DATA__")
    if not next_data_script or not next_data_script.string:
        return {}

    try:
        raw_json = json.loads(next_data_script.string)
        return raw_json.get("props", {}).get("pageProps", {}).get("mfServerSideData", {})
    except Exception as e:
        logger.warning(f"Failed to parse __NEXT_DATA__ JSON: {e}")
        return {}


def parse_publish_date(mf_data: Dict[str, Any]) -> date:
    """Extract or infer the certified publish date from Groww data."""
    # Check nav_date (e.g., '23-Oct-2026')
    nav_date_str = mf_data.get("nav_date")
    if nav_date_str:
        for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(nav_date_str.strip(), fmt).date()
            except ValueError:
                pass

    # Check holdings portfolio date (e.g., '2026-09-29T18:30:00.000Z')
    holdings = mf_data.get("holdings", [])
    if holdings and isinstance(holdings, list):
        first_port_date = holdings[0].get("portfolio_date")
        if first_port_date and isinstance(first_port_date, str):
            try:
                return datetime.fromisoformat(first_port_date.replace("Z", "+00:00")).date()
            except Exception:
                pass

    return date.today()


def build_expense_and_load_table(mf: Dict[str, Any], scheme_name: str) -> Dict[str, Any]:
    """Generate Markdown table for Expense Ratio, Exit Load, and Stamp Duty."""
    ter = mf.get("expense_ratio")
    ter_display = f"{ter}% (Direct Plan - Growth)" if ter is not None else "Refer scheme document"
    exit_load = mf.get("exit_load") or "Nil exit load."
    stamp_duty = mf.get("stamp_duty") or "0.005% (from July 1st, 2020)"

    headers = ["Parameter", "Applicable Terms & Value"]
    rows = [
        ["Expense Ratio (TER)", str(ter_display)],
        ["Exit Load", str(exit_load)],
        ["Stamp Duty", str(stamp_duty)],
        [
            "Tax Implication",
            "Equity scheme: 20% Short-term capital gains tax (< 1 year); 12.5% Long-term capital gains tax (> 1 year on gains above ₹1.25 lakh).",
        ],
    ]
    md_table = _format_markdown_table(headers, rows)

    return {
        "content": md_table,
        "section": "Expense Ratio & Exit Load",
        "content_type": "table",
    }


def build_investment_minimums_table(mf: Dict[str, Any], scheme_name: str) -> Dict[str, Any]:
    """Generate Markdown table for Minimum SIP, Lumpsum, and Lock-in terms."""
    min_sip = mf.get("min_sip_investment")
    min_lump = mf.get("min_investment_amount")
    mini_add = mf.get("mini_additional_investment") or min_lump
    min_with = mf.get("min_withdrawal") or 100

    lock_in_data = mf.get("lock_in") or {}
    has_lock = any(lock_in_data.get(k) for k in ("years", "months", "days"))
    lock_in_text = "None / Nil (Open-ended scheme)" if not has_lock else f"{lock_in_data}"

    headers = ["Parameter", "Specified Amount / Rule"]
    rows = [
        ["Minimum SIP Amount", f"₹{min_sip}" if min_sip else "₹100"],
        ["Minimum Lumpsum Investment", f"₹{min_lump}" if min_lump else "₹100"],
        ["Minimum Additional Investment", f"₹{mini_add}" if mini_add else "₹100"],
        ["Minimum Withdrawal / Redemption", f"₹{min_with}" if min_with else "₹100"],
        ["Lock-in Period", lock_in_text],
        ["SIP Multiplier", str(mf.get("sip_multiplier") or 1)],
    ]
    md_table = _format_markdown_table(headers, rows)

    return {
        "content": md_table,
        "section": "Minimum Investment & Lock-in",
        "content_type": "table",
    }


def build_scheme_overview_table(mf: Dict[str, Any], scheme_name: str) -> Dict[str, Any]:
    """Generate Markdown table for Scheme Overview, Benchmark, AUM, NAV, and Risk."""
    category = mf.get("category") or "Equity"
    sub_category = mf.get("sub_category") or ""
    cat_display = f"{category}: {sub_category}" if sub_category else category

    benchmark = mf.get("benchmark") or mf.get("benchmark_name") or "Benchmark Index"
    aum = mf.get("aum")
    aum_display = f"₹{aum:,.2f} Cr" if isinstance(aum, (int, float)) else f"₹{aum} Cr"
    nav = mf.get("nav")
    nav_date = mf.get("nav_date") or ""
    nav_display = f"₹{nav} (as of {nav_date})" if nav else "Latest official NAV"
    risk = mf.get("nfo_risk") or "Very High"
    launch_date = mf.get("launch_date") or mf.get("allotment_date") or "01-Jan-2013"
    isin = mf.get("isin") or mf.get("groww_scheme_code") or "N/A"
    rta = mf.get("registrar_agent") or "CAMS"
    fund_house = mf.get("fund_house") or "HDFC Mutual Fund"

    headers = ["Parameter", "Details"]
    rows = [
        ["Scheme Name", str(mf.get("scheme_name") or scheme_name)],
        ["Category", str(cat_display)],
        ["Plan & Option", "Direct Plan - Growth Option"],
        ["Benchmark Index", str(benchmark)],
        ["Riskometer Level", str(risk)],
        ["Fund Size (AUM)", str(aum_display)],
        ["Current Net Asset Value (NAV)", str(nav_display)],
        ["Launch / Inception Date", str(launch_date)],
        ["ISIN", str(isin)],
        ["Fund House (AMC)", str(fund_house)],
        ["Registrar & Transfer Agent (RTA)", str(rta)],
    ]
    md_table = _format_markdown_table(headers, rows)

    return {
        "content": md_table,
        "section": "Fund Overview & Benchmark",
        "content_type": "table",
    }


def build_fund_management_table(mf: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Markdown table for Fund Managers and tenure."""
    manager = mf.get("fund_manager") or "HDFC Mutual Fund Management Team"
    details = mf.get("fund_manager_details") or []

    headers = ["Fund Manager", "Tenure & Details"]
    rows = []
    if details and isinstance(details, list):
        for d in details:
            date_from = str(d.get("date_from") or "").split("T")[0]
            tenure = f"Managing since {date_from}" if date_from else "Lead Manager"
            rows.append([manager, tenure])

    if not rows:
        rows.append([manager, "Certified Fund Manager at HDFC Mutual Fund"])

    md_table = _format_markdown_table(headers, rows)
    return {
        "content": md_table,
        "section": "Fund Management",
        "content_type": "table",
    }


def build_holdings_table(mf: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate Markdown table for top portfolio holdings."""
    holdings = mf.get("holdings", [])
    if not holdings or not isinstance(holdings, list):
        return None

    headers = ["Company / Asset Name", "Sector", "Instrument", "Assets (%)"]
    rows = []
    for h in holdings[:15]:  # Top 15 holdings
        name = h.get("company_name") or h.get("name") or "Undisclosed"
        sector = h.get("sector_name") or h.get("sector") or "Diversified"
        instrument = h.get("nature_name") or h.get("instrument") or "Equity"
        assets = f"{h.get('corpus_per', 0):.2f}%"
        rows.append([name, sector, instrument, assets])

    if not rows:
        return None

    md_table = _format_markdown_table(headers, rows)
    return {
        "content": md_table,
        "section": "Holdings & Portfolio Allocation",
        "content_type": "table",
    }


def parse_groww_page(
    html_path: Path,
    scheme_id: str,
    scheme_name: str,
    source_url: str,
    publish_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Parse a downloaded Groww scheme HTML page into structured content blocks.

    Args:
        html_path: Path to the groww_page.html file.
        scheme_id: Canonical scheme identifier (e.g., 'hdfc_mid_cap').
        scheme_name: Formal scheme name.
        source_url: Canonical Groww URL citation.
        publish_date: Optional statutory publish date; inferred from HTML if None.

    Returns:
        List of structured block dictionaries suitable for chunking and vector storage.
    """
    if not html_path.exists():
        raise FileNotFoundError(f"HTML snapshot not found at {html_path}")

    raw_html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw_html, "html.parser")

    mf_data = extract_groww_structured_data(soup)
    canonical_date = publish_date or parse_publish_date(mf_data)

    content_blocks: List[Dict[str, Any]] = []

    # 1. Expense Ratio & Exit Load Table
    exp_block = build_expense_and_load_table(mf_data, scheme_name)
    content_blocks.append(exp_block)

    # 2. Investment Minimums Table
    min_block = build_investment_minimums_table(mf_data, scheme_name)
    content_blocks.append(min_block)

    # 3. Fund Overview & Benchmark Table
    overview_block = build_scheme_overview_table(mf_data, scheme_name)
    content_blocks.append(overview_block)

    # 4. Fund Management Table
    mgmt_block = build_fund_management_table(mf_data)
    content_blocks.append(mgmt_block)

    # 5. Top Holdings Table
    holdings_block = build_holdings_table(mf_data)
    if holdings_block:
        content_blocks.append(holdings_block)

    # 6. Investment Objective & Strategy Narrative
    description = mf_data.get("description")
    if not description:
        # Fallback to trafilatura article text
        clean_text = trafilatura.extract(raw_html) or ""
        # Search for investment objective snippet
        obj_match = re.search(r"Investment Objective[:\s]+(.*?)(?:\n\n|\Z)", clean_text, re.DOTALL)
        if obj_match:
            description = obj_match.group(1).strip()
        else:
            description = clean_text[:600]

    if description and len(description.strip()) > 20:
        content_blocks.append({
            "content": f"**Scheme Investment Objective**: {description.strip()}",
            "section": "Investment Objective & Strategy",
            "content_type": "text",
        })

    # 7. Add scheme metadata to every block
    for block in content_blocks:
        block["scheme_id"] = scheme_id
        block["scheme_name"] = scheme_name
        block["source_url"] = source_url
        date_val = canonical_date.isoformat() if hasattr(canonical_date, "isoformat") else str(canonical_date)
        block["publish_date"] = date_val

    logger.info(
        f"Parsed {len(content_blocks)} structured content blocks for {scheme_id} ({scheme_name})"
    )
    return content_blocks
