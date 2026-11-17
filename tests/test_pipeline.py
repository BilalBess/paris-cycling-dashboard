from pathlib import Path

import pandas as pd
import pytest

import prepare_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def processed(tmp_path):
    """Run the cleaning on a tiny fake raw file."""
    rows = []
    # counter A: full day (24 hours) on 2025-06-10 Paris time -> complete day, 1 passage per hour
    for h in range(24):
        ts = pd.Timestamp("2025-06-10 00:00", tz="Europe/Paris") + pd.Timedelta(hours=h)
        rows.append(["A", "Counter A", 1.0, ts.tz_convert("UTC").isoformat(), "48.85, 2.35"])
    # counter B: only 5 hours -> incomplete day
    for h in range(5):
        ts = pd.Timestamp("2025-06-10 08:00", tz="Europe/Paris") + pd.Timedelta(hours=h)
        rows.append(["B", "Counter B", 10.0, ts.tz_convert("UTC").isoformat(), "48.86, 2.36"])
    # a duplicated row and a row with a missing count (must NOT be turned into a zero)
    rows.append(rows[0])
    rows.append(["B", "Counter B", None, "2025-06-10T20:00:00+00:00", "48.86, 2.36"])
    # UTC 22:30 on 30 June is already 1 July in Paris (UTC+2 in summer)
    rows.append(["C", "Counter C", 7.0, "2025-06-30T22:00:00+00:00", "48.87, 2.37"])
    raw = tmp_path / "raw.csv"
    pd.DataFrame(rows, columns=["id_compteur", "nom_compteur", "sum_counts", "date", "coordinates"]).to_csv(
        raw, index=False)
    out = tmp_path / "out"
    prepare_data.prepare(raw=raw, proc=out)
    return {n: pd.read_csv(out / f"{n}.csv") for n in ["daily_counts", "counters", "hourly_profile"]}


def test_duplicates_are_removed(processed):
    d = processed["daily_counts"]
    a = d[d["id_compteur"] == "A"].iloc[0]
    assert a["n_hours"] == 24 and a["count"] == 24


def test_missing_counts_are_dropped_not_zero(processed):
    d = processed["daily_counts"]
    b = d[d["id_compteur"] == "B"].iloc[0]
    assert b["n_hours"] == 5 and b["count"] == 50


def test_complete_day_flag(processed):
    d = processed["daily_counts"].set_index("id_compteur")
    assert bool(d.loc["A", "complete_day"]) is True
    assert bool(d.loc["B", "complete_day"]) is False


def test_timestamps_are_converted_to_paris_time(processed):
    c = processed["daily_counts"].query("id_compteur == 'C'").iloc[0]
    assert c["day"] == "2025-07-01"


def test_counter_table_has_coordinates(processed):
    c = processed["counters"].set_index("id_compteur")
    assert c.loc["A", "lat"] == pytest.approx(48.85)
    assert c.loc["A", "lon"] == pytest.approx(2.35)


def test_dashboard_runs_without_error():
    """Smoke test on the real processed files that are committed in the repo."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert len(at.metric) == 4
