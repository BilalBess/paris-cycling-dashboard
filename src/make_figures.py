"""Static figures for the README (the dashboard itself is in app.py)."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

daily = pd.read_csv(PROC / "daily_counts.csv", parse_dates=["day"])
daily = daily[daily["complete_day"]]
counters = pd.read_csv(PROC / "counters.csv")
hourly = pd.read_csv(PROC / "hourly_profile.csv")

total = daily.groupby("day")["count"].sum()

# 1) daily series
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(total.index, total.values, alpha=0.35, label="Daily")
ax.plot(total.index, total.rolling(7, min_periods=3).mean(), color="red", label="7-day average")
ax.set_ylabel("Passages (all counters)")
ax.set_title("Daily bike traffic in Paris")
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "daily_traffic.png", dpi=150)
plt.close(fig)

# 2) hourly profile
h = hourly.groupby(["is_weekend", "hour"])["avg_count"].sum().unstack(0)
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(h.index, h[False], marker="o", label="Weekday")
ax.plot(h.index, h[True], marker="o", label="Weekend")
ax.set_xlabel("Hour of the day")
ax.set_ylabel("Avg passages per hour (all counters)")
ax.set_title("Weekdays show two commute peaks, weekends one afternoon plateau")
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "hourly_profile.png", dpi=150)
plt.close(fig)

# 3) day of the week
wd = total.groupby(total.index.day_of_week).mean()
wd.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(wd.index, wd.values, color="#2b6cb0")
ax.set_ylabel("Avg passages per day")
ax.set_title("Average traffic by day of the week")
fig.tight_layout()
fig.savefig(FIG / "weekday_profile.png", dpi=150)
plt.close(fig)

# 4) monthly (only full months)
m = total.groupby(total.index.to_period("M")).agg(["mean", "count"])
m = m[m["count"] >= 25]
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(m.index.astype(str), m["mean"], color="#2f855a")
plt.xticks(rotation=45)
ax.set_ylabel("Avg passages per day")
ax.set_title("Monthly average (full months only)")
fig.tight_layout()
fig.savefig(FIG / "monthly_average.png", dpi=150)
plt.close(fig)

# 5) top counters
top = counters.sort_values("total", ascending=False).head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(top["nom_compteur"], top["total"] / 1e6, color="#c05621")
ax.set_xlabel("Total passages (millions)")
ax.set_title("Top 10 counters")
fig.tight_layout()
fig.savefig(FIG / "top_counters.png", dpi=150)
plt.close(fig)

print(m.round(0))
print("weekend vs weekday:",
      round(total[total.index.day_of_week >= 5].mean() / total[total.index.day_of_week < 5].mean() - 1, 3))
print("Aug 2026 vs Jun 2026:", round(m.loc["2026-08", "mean"] / m.loc["2026-06", "mean"] - 1, 3))
