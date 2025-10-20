# --- imports
import os, sys, subprocess, time
import datetime as dt
from pathlib import Path
import pandas as pd
import streamlit as st

# --- paths
ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "data" / "latest_metrics.csv"
OFFLINE = ROOT / "data" / "latest_metrics_offline.csv"
LIVE_SCRIPT = ROOT / "scripts" / "gain_collect_live.py"
OFFLINE_SCRIPT = ROOT / "scripts" / "gain_collect_offline.py"

# --- app setup
st.set_page_config(page_title="AI Signal Board", page_icon="🌐", layout="wide")
st.title("AI SIGNAL BOARD")
st.caption("Monitoring AI Governance, Safety, and Societal Indicators")

# --- helpers
@st.cache_data(ttl=60)
def load_metrics(p: Path) -> pd.DataFrame | None:
    if not p.exists():
        return None
    df = pd.read_csv(p)
    # normalize numeric strings if it's already wide
    for col in ["governance_index", "openness_score", "incident_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False),
                errors="coerce"
            )
    return df

def file_timestamp(path: Path):
    try:
        ts = os.path.getmtime(path)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    except Exception:
        return "—"

def fmt(v):
    try:
        x = float(v)
        if x >= 1_000_000: return f"{x/1_000_000:.1f}M"
        if x >= 1_000:     return f"{x/1_000:.1f}k"
        if float(x).is_integer(): return str(int(x))
        return str(x)
    except Exception:
        return str(v)

def humanize_secs(s: float) -> str:
    s = max(0, int(s))
    if s < 60: return f"{s}s ago"
    m, s = divmod(s, 60)
    if m < 60: return f"{m}m {s}s ago"
    h, m = divmod(m, 60)
    return f"{h}h {m}m ago"

def last_write_ago(path: Path) -> str:
    try:
        return humanize_secs(time.time() - os.path.getmtime(path))
    except Exception:
        return "—"

def mark_status(path: Path, label: str):
    ts = file_timestamp(path)
    st.markdown(
        f"""
        <div style="display:inline-block;padding:6px 10px;border-radius:999px;
                    background:#1b3654;color:#fff;border:1px solid #2c5a8a;
                    font-size:12px;">
            <b>Data source:</b> {label} &nbsp; • &nbsp; <b>Last write:</b> {ts}
        </div>
        """,
        unsafe_allow_html=True
    )

def run_script(path: Path, cwd: Path):
    try:
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, cwd=str(cwd))
        return proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return False, "", str(e)

# --- sidebar controls
with st.sidebar:
    st.subheader("Data Controls")
    refresh_live = st.button("🔄 Refresh Live Data", use_container_width=True)
    use_offline  = st.button("📁 Use Offline Data", use_container_width=True)
    auto_refresh = st.toggle("⏱ Auto-refresh every 30s", value=False, help="Reruns the app every 30 seconds")
    force_offline = st.checkbox("Force OFFLINE source", value=False, help="Ignore LIVE data even if it exists")
    st.caption("Live refresh runs the script in /scripts and updates /data/latest_metrics.csv")

log_expander = st.expander("Show refresh logs", expanded=False)
status = st.empty()

# --- actions
if refresh_live:
    if LIVE_SCRIPT.exists():
        ok, out, err = run_script(LIVE_SCRIPT, ROOT)
        log_expander.code(out or "(no stdout)")
        if err: log_expander.code(err)
        if ok and LIVE.exists():
            st.toast("Live data refreshed ✅", icon="✅")
            st.rerun()
        else:
            status.error("Live refresh failed. Falling back to offline data if available.")
    else:
        status.error("Live script not found: scripts/gain_collect_live.py")

if use_offline:
    if OFFLINE_SCRIPT.exists():
        run_script(OFFLINE_SCRIPT, ROOT)  # bump timestamp
    if OFFLINE.exists():
        st.toast("Offline data selected 📁", icon="📁")
        if LIVE.exists():
            LIVE.unlink(missing_ok=True)   # force fallback to offline
        st.rerun()
    else:
        status.error("Offline file missing: data/latest_metrics_offline.csv")

# --- choose & load data (prefer LIVE)
data_path = OFFLINE if force_offline else (LIVE if LIVE.exists() else OFFLINE)
if not data_path.exists():
    st.warning("No metrics file found. Click **📁 Use Offline Data** or **🔄 Refresh Live Data**.")
    st.stop()

label = "LIVE (data/latest_metrics.csv)" if data_path == LIVE else "OFFLINE (data/latest_metrics_offline.csv)"
mark_status(data_path, label)
if force_offline:
    st.caption("**Source override:** OFFLINE (forced)")
st.caption(f"Last updated: { last_write_ago(data_path) }")

df = load_metrics(data_path)
if df is None or df.empty:
    st.warning("No data found in the selected source.")
    st.stop()

# --- make a long (metric,value) view for cards regardless of input shape
if {"metric", "value"}.issubset(df.columns):
    df_long = df.copy()
else:
    # convert wide -> long for known metrics
    known_cols = [c for c in ["governance_index", "openness_score", "incident_count"] if c in df.columns]
    df_long = (
        df[known_cols]
        .iloc[:1]  # first row as the snapshot
        .melt(var_name="metric", value_name="value")
        .dropna(subset=["metric"])
    )

# --- headline three metrics
wide_map = dict(zip(df_long["metric"], pd.to_numeric(df_long["value"], errors="coerce")))
gov = wide_map.get("governance_index")
opn = wide_map.get("openness_score")
inc = wide_map.get("incident_count")

st.metric("Governance Index", f"{gov:.2f}" if pd.notna(gov) else "—")
st.metric("Openness Score", f"{opn:.2f}" if pd.notna(opn) else "—")
st.metric("Incident Log", int(inc) if pd.notna(inc) else 0)

# --- ensure timestamp column for footer
if "timestamp" not in df.columns:
    df["timestamp"] = dt.date.today().isoformat()

# --- deltas vs previous run (using long view to be consistent)
if "prev_df_long" not in st.session_state:
    st.session_state.prev_df_long = None
prev_long = st.session_state.prev_df_long
st.session_state.prev_df_long = df_long.copy()

prev_map = {}
if prev_long is not None and {"metric", "value"}.issubset(prev_long.columns):
    for _, r in prev_long.iterrows():
        prev_map[r["metric"]] = r["value"]

# --- headline cards from long view
st.divider()
top = df_long.drop_duplicates(subset=["metric"]).head(5)
cols = st.columns(len(top) if len(top) else 1)
for c, (_, row) in zip(cols, top.iterrows()):
    old = prev_map.get(row["metric"])
    try:
        delta = None
        if old not in (None, "") and str(row["value"]) != "":
            delta = float(row["value"]) - float(old)
    except Exception:
        delta = None
    c.metric(row["metric"], fmt(row["value"]), delta=delta)

# --- download + footer
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button("Download current data (CSV)", data=csv_bytes, file_name=data_path.name, mime="text/csv")
st.caption(f"Showing: {data_path.name}  •  Last updated (timestamp column): {df['timestamp'].max()}")
st.caption("GAIN — Building systems where truth precedes control, and intelligence remains human-aligned.")

# --- optional auto-refresh
if auto_refresh:
    time.sleep(30)
    st.rerun()
