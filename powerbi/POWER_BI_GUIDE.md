# Build the same dashboard in Power BI

The Streamlit app is the main deliverable, but Power BI is the tool used in many companies, so here is how I rebuild the dashboard with the same processed files.

> I did not commit a `.pbix` file. Open Power BI Desktop and follow these steps (about 30 minutes).

## 1. Load the data
`Get data > Text/CSV`, load the three files from `data/processed/`:
- `daily_counts.csv` (fact table: counter x day)
- `counters.csv` (dimension: name, lat, lon)
- `hourly_profile.csv` (counter x weekday/weekend x hour)

In Power Query: set `day` as Date, `id_compteur` as Text, `is_weekend` as True/False.

## 2. Model
- `counters[id_compteur]` 1 -> * `daily_counts[id_compteur]`
- `counters[id_compteur]` 1 -> * `hourly_profile[id_compteur]`
- Create a calendar table (see below) and link it to `daily_counts[day]`.

## 3. Measures (DAX)
```DAX
Calendar =
ADDCOLUMNS (
    CALENDAR ( MIN ( daily_counts[day] ), MAX ( daily_counts[day] ) ),
    "Year", YEAR ( [Date] ),
    "Month", FORMAT ( [Date], "yyyy-MM" ),
    "Weekday Number", WEEKDAY ( [Date], 2 ),
    "Weekday", FORMAT ( [Date], "ddd" ),
    "Is Weekend", WEEKDAY ( [Date], 2 ) >= 6
)

Total Passages =
CALCULATE ( SUM ( daily_counts[count] ), daily_counts[complete_day] = TRUE () )

Avg Passages per Day =
AVERAGEX (
    VALUES ( 'Calendar'[Date] ),
    CALCULATE ( [Total Passages] )
)

Weekday Avg =
CALCULATE ( [Avg Passages per Day], 'Calendar'[Is Weekend] = FALSE () )

Weekend Avg =
CALCULATE ( [Avg Passages per Day], 'Calendar'[Is Weekend] = TRUE () )

Weekend vs Weekday % =
DIVIDE ( [Weekend Avg], [Weekday Avg] ) - 1

Passages 7d Moving Avg =
AVERAGEX (
    DATESINPERIOD ( 'Calendar'[Date], MAX ( 'Calendar'[Date] ), -7, DAY ),
    [Total Passages]
)

Busiest Day =
MAXX ( VALUES ( 'Calendar'[Date] ), [Total Passages] )
```

## 4. Report page
| Visual | Fields |
|---|---|
| 4 KPI cards | Total Passages, Avg Passages per Day, Busiest Day, Weekend vs Weekday % |
| Line chart | `Calendar[Date]` on axis, `Total Passages` and `Passages 7d Moving Avg` |
| Column chart | `Calendar[Weekday]` (sorted by Weekday Number), `Avg Passages per Day` |
| Line chart | `hourly_profile[hour]`, `avg_count` (sum), legend `is_weekend` |
| Map | latitude `counters[lat]`, longitude `counters[lon]`, size `Total Passages` |
| Slicers | Date range, counter name |

## 5. Tips
- Sort the weekday column by `Weekday Number`, otherwise days are alphabetical.
- Turn off "auto date/time" in the options to keep the model clean.
- Keep the same filter on `complete_day` as in the Python version, so numbers match between both tools. A good check: total passages should be **85,696,653** with the full period.
