import pandas as pd, requests
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "latest_metrics.csv"
LOG = ROOT / "data" / "debug_aiid_response.txt"

HDRS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Connection": "keep-alive",
}

def fetch_aiid_count():
    """Return (count, collected_from, note). Never raise; always safe."""
    urls = [
        "https://incidentdatabase.ai/api/v1/incidents?limit=500&sort=date",
        "https://incidentdatabase.ai/api/v1/incidents?format=json&limit=500",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HDRS, timeout=60, allow_redirects=True)
            ct = r.headers.get("content-type", "").lower()
            if r.status_code != 200:
                LOG.write_text(f"HTTP {r.status_code} {ct}\n{r.text[:1200]}")
                continue
            try:
                data = r.json()
            except Exception:
                LOG.write_text(f"CT={ct}\n{r.text[:1200]}")
                continue
            if not isinstance(data, dict) or "results" not in data:
                LOG.write_text(f"Unexpected JSON shape: {str(data)[:1200]}")
                continue
            yr = str(date.today().year)
            results = data.get("results", [])
            count = sum(1 for item in results if yr in str(item.get("date", "")))
            return count, url, ""
        except Exception as e:
            LOG.write_text(f"{url}\n{type(e).__name__}: {e}")
            continue
    # Fallback: safe default; explain in note
    return 0, "fallback", "AIID API returned non-JSON/blocked; see data/debug_aiid_response.txt"

def openness_score():
    url = "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard"
    try:
        tables = pd.read_html(url)
        df = tables[0]
        n = len(df)
        open_evals = df["Eval type"].notna().sum() if "Eval type" in df.columns else 0
        pct = round((open_evals / n) * 100, 1) if n else 0
        return {"metric":"Openness Score","value":pct,"unit":"%","source":"Open LLM Leaderboard","collected_from":url}
    except Exception as e:
        return {"metric":"Openness Score","value":"", "unit":"%","source":"Open LLM Leaderboard (manual)","collected_from":f"read_html failed: {type(e).__name__}"}

def governance_index():
    # Keep manual for now
    return {"metric":"Governance Index","value":"","unit":"policies","source":"OECD.AI (manual)","collected_from":"manual"}

def incident_log():
    cnt, src, note = fetch_aiid_count()
    return {"metric":"Incident Log","value":cnt,"unit":"incidents YTD","source":"AI Incident Database","collected_from":src if not note else f"{src} | {note}"}

def main():
    rows = [governance_index(), openness_score(), incident_log()]
    df = pd.DataFrame(rows)
    df["timestamp"] = date.today().isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print("Saved:", OUT)
    print(df)

if __name__ == "__main__":
    main()
