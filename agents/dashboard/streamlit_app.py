"""
Streamlit dashboard for Exercise 1.3 — renders JSON from scraper (Exercise 1.2).

Loads agents/data/staging/raw_scrape_sample.json. No network calls or credentials.
"""

import json
from pathlib import Path

import streamlit as st

# Path to JSON relative to repo root (works regardless of cwd)
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "agents" / "data" / "staging" / "raw_scrape_sample.json"

RAW_TEXT_PREVIEW_MIN = 500
RAW_TEXT_PREVIEW_MAX = 800


def load_scrape_data():
    """Load and parse scrape JSON. Returns (data_dict, error_message). error_message is None on success."""
    if not DATA_PATH.exists():
        return None, f"File not found: `{DATA_PATH}`. Run the scraper first to generate it."
    try:
        text = DATA_PATH.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"Could not read file: {e}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"
    if not isinstance(data, dict):
        return None, "Expected JSON root to be an object."
    if "records" not in data:
        return None, "Missing required key: 'records'."
    records = data.get("records")
    if not isinstance(records, list):
        return None, "'records' must be a list."
    return data, None


def raw_text_preview(raw_text: str) -> str:
    """First 500–800 chars; indicate when truncated."""
    if not raw_text or not isinstance(raw_text, str):
        return ""
    text = raw_text.strip()
    if len(text) <= RAW_TEXT_PREVIEW_MAX:
        return text
    # Prefer cutting at word boundary in [500, 800]
    chunk = text[:RAW_TEXT_PREVIEW_MAX]
    last_space = chunk.rfind(" ", RAW_TEXT_PREVIEW_MIN)
    if last_space > RAW_TEXT_PREVIEW_MIN:
        chunk = chunk[: last_space + 1]
    return chunk + " […] [truncated]"


def main():
    st.set_page_config(page_title="Scraped Job Data", layout="wide")
    st.title("Scraped Job Data")

    data, err = load_scrape_data()
    if err:
        st.error(err)
        return

    scrape_run_id = data.get("scrape_run_id", "—")
    scraped_at = data.get("scraped_at", "—")
    target_url = data.get("target_url", "—")
    records = data.get("records", [])
    total = len(records)

    # Top section: run info and total count
    st.subheader("Run info")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Scrape run ID", scrape_run_id[:20] + "…" if len(str(scrape_run_id)) > 20 else scrape_run_id)
    with col2:
        st.metric("Scraped at", scraped_at)
    with col3:
        st.metric("Target URL", target_url[:40] + "…" if len(str(target_url)) > 40 else target_url)
    with col4:
        st.metric("Total records", total)

    if total == 0:
        st.info("No records in the file.")
        return

    # Sidebar: source filter
    all_sources = sorted({r.get("source") for r in records if r.get("source")})
    sidebar_source = st.sidebar.selectbox(
        "Filter by source",
        options=["All"] + all_sources,
        index=0,
    )
    if sidebar_source == "All":
        filtered = records
    else:
        filtered = [r for r in records if r.get("source") == sidebar_source]
    shown = len(filtered)
    st.sidebar.caption(f"Showing {shown} of {total}")

    # Main content: expandable cards per record
    for i, rec in enumerate(filtered, start=1):
        header = rec.get("title") or rec.get("url") or f"Record {i}"
        if isinstance(header, str) and len(header) > 80:
            header = header[:77] + "..."
        with st.expander(f"{i}. {header}"):
            st.write("**Source:**", rec.get("source", "—"))
            st.write("**URL:**", rec.get("url", "—"))
            st.write("**Scraped at:**", rec.get("scraped_at", "—"))
            preview = raw_text_preview(rec.get("raw_text", ""))
            st.write("**Raw text preview:**")
            st.text(preview)


if __name__ == "__main__":
    main()

# Run from repo root:
#   streamlit run agents/dashboard/streamlit_app.py
