"""Download the hourly bike counts from Paris open data and build small tables
for the dashboard (so the app is fast and the repo stays light).

Source: opendata.paris.fr, dataset "comptage-velo-donnees-compteurs".
Note: the dataset is a rolling window (about the last 13 months), so the dates
you get depend on the day you run the script. The processed files in
data/processed/ are the ones I used for the README numbers.
"""
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw_counts.csv"
PROC = ROOT / "data" / "processed"

URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/"
    "comptage-velo-donnees-compteurs/exports/csv"
    "?select=id_compteur,nom_compteur,sum_counts,date,coordinates&delimiter=%2C"
)


def download():
    if RAW.exists():
        print("raw file already there")
        return
    RAW.parent.mkdir(exist_ok=True)
    with requests.get(URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(RAW, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def prepare(raw=RAW, proc=PROC):
    df = pd.read_csv(raw, encoding="utf-8-sig")
    print("raw rows:", len(df))

    # 1) cleaning
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert("Europe/Paris")
    df = df.drop_duplicates(["id_compteur", "date"])
    n_missing = df["sum_counts"].isna().sum()
    df = df.dropna(subset=["sum_counts"])  # a missing count is NOT a zero
    print(f"dropped {n_missing} rows with missing counts")

    ll = df["coordinates"].str.split(",", expand=True).astype(float)
    df["lat"], df["lon"] = ll[0], ll[1]

    # 2) time features
    df["day"] = df["date"].dt.date
    df["hour"] = df["date"].dt.hour
    df["weekday"] = df["date"].dt.day_of_week  # 0 = Monday
    df["is_weekend"] = df["weekday"] >= 5

    proc.mkdir(parents=True, exist_ok=True)

    # 3) counter table
    counters = (
        df.groupby(["id_compteur", "nom_compteur"])
        .agg(lat=("lat", "first"), lon=("lon", "first"), total=("sum_counts", "sum"),
             n_hours=("sum_counts", "size"))
        .reset_index()
    )
    counters.to_csv(proc / "counters.csv", index=False)

    # 4) daily table (one row per counter and day)
    daily = (
        df.groupby(["id_compteur", "day"])
        .agg(count=("sum_counts", "sum"), n_hours=("sum_counts", "size"))
        .reset_index()
    )
    daily["day"] = pd.to_datetime(daily["day"])
    # a day is "complete" only if the counter reported at least 20 hours
    daily["complete_day"] = daily["n_hours"] >= 20
    daily.to_csv(proc / "daily_counts.csv", index=False)

    # 5) hourly profile (counter x weekday-type x hour)
    hourly = (
        df.groupby(["id_compteur", "is_weekend", "hour"])["sum_counts"]
        .mean()
        .round(1)
        .reset_index(name="avg_count")
    )
    hourly.to_csv(proc / "hourly_profile.csv", index=False)

    print("period:", df["date"].min().date(), "->", df["date"].max().date())
    print("counters:", len(counters), "| daily rows:", len(daily))


if __name__ == "__main__":
    download()
    prepare()
