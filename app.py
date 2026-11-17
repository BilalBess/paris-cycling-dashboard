"""Streamlit dashboard: bike traffic in Paris (open data counters).

Run with:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROC = Path(__file__).parent / "data" / "processed"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.set_page_config(page_title="Paris cycling traffic", layout="wide")


@st.cache_data
def load():
    daily = pd.read_csv(PROC / "daily_counts.csv", parse_dates=["day"])
    counters = pd.read_csv(PROC / "counters.csv")
    hourly = pd.read_csv(PROC / "hourly_profile.csv")
    daily = daily[daily["complete_day"]].merge(counters[["id_compteur", "nom_compteur", "lat", "lon"]],
                                               on="id_compteur")
    return daily, counters, hourly


daily, counters, hourly = load()

st.title("Cycling traffic in Paris")
st.caption("Source: Paris open data, automatic bike counters. Only days with at least 20 hours of data are used.")

# ---- sidebar filters
st.sidebar.header("Filters")
dmin, dmax = daily["day"].min().date(), daily["day"].max().date()
start, end = st.sidebar.date_input("Period", (dmin, dmax), min_value=dmin, max_value=dmax)
names = sorted(daily["nom_compteur"].unique())
chosen = st.sidebar.multiselect("Counters (empty = all)", names)

f = daily[(daily["day"].dt.date >= start) & (daily["day"].dt.date <= end)]
if chosen:
    f = f[f["nom_compteur"].isin(chosen)]
if f.empty:
    st.warning("No data for this selection.")
    st.stop()

# ---- KPIs
total_by_day = f.groupby("day")["count"].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total passages", f"{int(f['count'].sum()):,}")
c2.metric("Avg per day (all selected counters)", f"{int(total_by_day.mean()):,}")
best = total_by_day.idxmax()
c3.metric("Busiest day", best.strftime("%d %b %Y"), f"{int(total_by_day.max()):,}")
wk = total_by_day[total_by_day.index.day_of_week < 5].mean()
we = total_by_day[total_by_day.index.day_of_week >= 5].mean()
c4.metric("Weekend vs weekday", f"{we / wk - 1:+.0%}")

# ---- time series
st.subheader("Daily traffic")
ts = total_by_day.reset_index(name="count")
ts["7-day average"] = ts["count"].rolling(7, min_periods=3).mean()
fig = px.line(ts, x="day", y=["count", "7-day average"], labels={"value": "passages", "day": ""})
st.plotly_chart(fig, width="stretch")

left, right = st.columns(2)

# ---- weekday profile
with left:
    st.subheader("Average by day of the week")
    wd = total_by_day.groupby(total_by_day.index.day_of_week).mean().reindex(range(7))
    wd.index = DAYS
    st.plotly_chart(px.bar(wd, labels={"value": "avg passages", "index": ""}).update_layout(showlegend=False),
                    width="stretch")

# ---- hourly profile
with right:
    st.subheader("Average by hour (sum over counters)")
    h = hourly if not chosen else hourly[hourly["id_compteur"].isin(
        counters.loc[counters["nom_compteur"].isin(chosen), "id_compteur"])]
    h = h.groupby(["is_weekend", "hour"])["avg_count"].sum().reset_index()
    h["type"] = h["is_weekend"].map({False: "Weekday", True: "Weekend"})
    st.plotly_chart(px.line(h, x="hour", y="avg_count", color="type",
                            labels={"avg_count": "avg passages per hour"}), width="stretch")

# ---- monthly + map
left, right = st.columns(2)
with left:
    st.subheader("Monthly average per day")
    m = total_by_day.groupby(total_by_day.index.to_period("M")).mean()
    m.index = m.index.astype(str)
    st.plotly_chart(px.bar(m, labels={"value": "avg passages / day", "index": ""}).update_layout(showlegend=False),
                    width="stretch")

with right:
    st.subheader("Where is it busy? (average per day)")
    per_counter = f.groupby(["nom_compteur", "lat", "lon"])["count"].mean().reset_index()
    st.plotly_chart(
        px.scatter_map(per_counter, lat="lat", lon="lon", size="count", color="count",
                       hover_name="nom_compteur", zoom=10.5, height=420,
                       color_continuous_scale="Viridis"),
        width="stretch")

st.subheader("Top 10 counters")
top = f.groupby("nom_compteur")["count"].sum().sort_values(ascending=False).head(10)
st.dataframe(top.rename("total passages"))
