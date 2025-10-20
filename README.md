# AI Signal Board — Starter Kit (GAIN)

This starter includes **both** live web retrieval and an **offline reproducible** workflow.

## Quick Start
```bash
pip install streamlit pandas requests beautifulsoup4 lxml
python scripts/gain_collect_live.py        # live web retrieval (requires internet)
# or
python scripts/gain_collect_offline.py     # uses ./data CSVs you edit manually
streamlit run streamlit_app.py
```

## Data CSV schema
Each file in `./data`: `date,value,unit,source,notes`

Metrics and sources: OECD.AI (governance), Open LLM Leaderboard (openness), AI Incident Database (incidents), SIPRI (militarization), ESG/MLCO2 (energy), Ipsos/Pew (trust).

Tagline: *Because the mind of Earth must stay human.*
