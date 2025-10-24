
import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import pytz
import streamlit as st

# ---------------------- App Meta ----------------------
APP_TITLE = "AI SIGNAL BOARD"
TAGLINE = "Monitoring governance, safety, and incident signals."
TZ = os.getenv("APP_TZ", "America/Los_Angeles")

# Primary data source
# 1) Local CSV in the repo root (default): GAIN_AI_SignalBoard_DataSources.csv
# 2) OR a Google Sheets/CSV URL provided in sidebar or as SHEETS_CSV_URL in secrets
SHEETS_CSV_URL = os.getenv("SHEETS_CSV_URL", st.secrets.get("SHEETS_CSV_URL", ""))

# ---------------------- Helpers ----------------------
def now_local():
    try:
        return datetime.now(pytz.timezone(TZ))
    except Exception:
        return datetime.now(timezone.utc)

def normalize_sheets_url(link: str) -> str:
    if not link:
        return link
    if "/export?format=csv" in link:
        return link
    if "docs.google.com/spreadsheets/d/" in link:
        try:
            root, gid = link.split("#gid=") if "#gid=" in link else (link, "0")
            sid = root.split("/d/")[1].split("/")[0]
            return f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}"
        except Exception:
            return link
    return link

@st.cache_data(ttl=60)
def read_csv_url(url: str) -> pd.DataFrame:
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.warning(f"Could not read CSV from URL: {e}")
        return pd.DataFrame()

def load_repo_csv() -> pd.DataFrame:
    # Prefer canonical filename; gracefully fallback
    for name in ["GAIN_AI_SignalBoard_DataSources.csv", "latest_metrics.csv", "data/latest_metrics.csv"]:
        if os.path.exists(name):
            try:
                return pd.read_csv(name)
            except Exception as e:
                st.warning(f"Found {name} but could not read it: {e}")
    return pd.DataFrame()

def status_to_icon(val: str) -> str:
    if not isinstance(val, str):
        return "⚪"
    v = val.strip().lower()
    if v in ["ok", "green", "✅", "live"]:
        return "🟢"
    if v in ["warning", "amber", "⚠️"]:
        return "🟡"
    if v in ["error", "down", "❌", "red"]:
        return "🔴"
    return "⚪"

def render_kpis(df: pd.DataFrame):
    total = len(df) if not df.empty else 0
    ok = sum(status_to_icon(s) == "🟢" for s in (df["Status"] if "Status" in df.columns else []))
    warn = sum(status_to_icon(s) == "🟡" for s in (df["Status"] if "Status" in df.columns else []))
    bad = sum(status_to_icon(s) == "🔴" for s in (df["Status"] if "Status" in df.columns else []))

    a,b,c,d = st.columns(4)
    a.metric("Total Signals", total)
    b.metric("Healthy", ok)
    c.metric("Warnings", warn)
    d.metric("Incidents", bad)

# ---------------------- UI ----------------------
st.set_page_config(page_title=APP_TITLE, page_icon="📡", layout="wide")

from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit_autorefresh import st_autorefresh

# Auto-refresh
if 'auto' in locals() and 'interval' in locals():
    try:
        if auto:
            st_autorefresh(interval=int(interval*1000), key='auto_refresh')
    except Exception:
        pass

st.title(APP_TITLE)
st.caption(TAGLINE)
st.markdown("---")

with st.sidebar:
    st.header("Data Controls")
    auto = st.toggle("Auto-refresh", value=True, help="Refresh the dashboard automatically.")
    interval = st.number_input("Refresh every (seconds)", min_value=10, max_value=3600, value=60, step=10)
    source_choice = st.radio("Data source", ["Repo CSV", "Google Sheets / CSV URL"], horizontal=False)
    url_input = ""
    if source_choice == "Google Sheets / CSV URL":
        url_input = st.text_input("Paste Sheets link or CSV URL", value=SHEETS_CSV_URL, placeholder="https://docs.google.com/spreadsheets/d/...")
    show_debug = st.toggle("Show debug logs", value=False)

# Load data
csv_url = None
if source_choice == "Google Sheets / CSV URL":
    url_val = url_input or SHEETS_CSV_URL
    if url_val:
        csv_url = normalize_sheets_url(url_val)
if csv_url:
    df = read_csv_url(csv_url)
    if show_debug:
        st.caption(f"Source: {csv_url}")
else:
    df = load_repo_csv()
    if show_debug:
        st.caption("Source: Repository CSV (GAIN_AI_SignalBoard_DataSources.csv)")

# KPIs
st.subheader("Overview")
render_kpis(df)

# Main table
st.subheader("GAIN – AI Signal Board Data Sources")
if df.empty:
    st.warning("No data found. Provide a Google Sheet/CSV URL in the sidebar or include `GAIN_AI_SignalBoard_DataSources.csv` in the repo root.")
else:
    # Optional prettification: add StatusIcon column if not present
    if "Status" in df.columns and "StatusIcon" not in df.columns:
        df = df.copy()
        df.insert(0, "StatusIcon", df["Status"].apply(status_to_icon))
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(f"© 2025 Governable AI Network – Showcase of useful signals, with truth preceding control. • Last refreshed: {now_local().strftime('%Y-%m-%d %H:%M:%S %Z')}")
