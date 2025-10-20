import pandas as pd
from datetime import date
from pathlib import Path

DATA = Path("data")
OUT = DATA/"latest_metrics_offline.csv"

def read_latest(csv, metric, unit):
    df = pd.read_csv(DATA/csv)
    v = df["value"].astype(str).replace("", pd.NA).dropna()
    value = v.iloc[-1] if not v.empty else ""
    return {"metric":metric,"value":value,"unit":unit,"source":df["source"].iloc[-1], "collected_from":"offline-csv"}

def main():
    rows = [
        read_latest("governance_index.csv","Governance Index","policies"),
        read_latest("openness_score.csv","Openness Score","%"),
        read_latest("incident_log.csv","Incident Log","incidents YTD"),
        read_latest("militarization_tracker.csv","Militarization Tracker","platforms"),
        read_latest("energy_footprint.csv","Energy Footprint","kWh per large run"),
        read_latest("public_trust.csv","Public Trust Index","index/score")
    ]
    df = pd.DataFrame(rows)
    df["timestamp"] = date.today().isoformat()
    df.to_csv(OUT, index=False)
    print(df)

if __name__ == "__main__":
    main()
