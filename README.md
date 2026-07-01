# Euro 2024 Goalkeeper Analysis

A data-driven analysis of goalkeeper performances at UEFA Euro 2024, using StatsBomb open data to rank and compare goalkeepers across multiple metrics.

## Key Features

- **Statistical Analysis** — Save percentage, xG prevention, goals saved above expected (GSAE)
- **Z-Score Ranking** — Composite ranking system using standardized metrics across all tournament goalkeepers
- **Shot Maps** — Individual shot-facing maps for every goalkeeper
- **Radar Charts** — Multi-metric comparison of top performers
- **Power BI Dashboard** — Interactive dashboard with DAX measures for deeper exploration

## Project Structure

```
├── data/
│   ├── raw/                  # Raw StatsBomb pull (written by clean_data.py)
│   ├── processed/            # Cleaned, per-goalkeeper event tables
│   └── final/                # Analysis-ready datasets (z-scores, rankings, stats)
├── scripts/
│   ├── clean_data.py         # Step 1 — pulls StatsBomb data, builds data/raw + data/processed
│   ├── statistical_analysis.py  # Step 2 — per-goalkeeper shot maps / GSaE charts
│   ├── zscore_analysis.py    # Step 3 — z-score metrics -> data/final
│   ├── rank_goalkeepers.py   # Step 4 — composite ranking -> data/final
│   ├── chart.py              # Step 5 — tournament-level charts
│   ├── dashboard.py          # Step 6 — top-3 goalkeeper dashboards
│   └── stat_tests.py         # Step 7 — descriptive stats, correlation p-values
├── notebooks/
│   └── Euro2024_GK_Analysis.ipynb  # Full analysis notebook (same pipeline, one file)
├── powerbi/
│   ├── data/                 # Power BI-ready datasets (written by prepare_data.py)
│   ├── dax_measures.dax      # DAX measures for Power BI
│   └── prepare_data.py       # Step 8 (optional) — exports data/ -> powerbi/data/
└── reports/
    ├── charts/                    # Generated visualizations (tournament, individual, dashboards)
    └── statistical_analysis.md    # Descriptive stats + correlation p-values (from stat_tests.py)
```

## Methodology

Goalkeeper events are pulled from StatsBomb (all 51 Euro 2024 matches), filtered to keepers with 2+ appearances (24 qualify), and reduced to core metrics — save %, xG faced, and Goals Saved above Expectation (GSaE = xG faced − goals conceded). Each metric is converted to a z-score across the tournament field (sign-flipped so higher is always better), then combined into a composite score weighted 35% GSaE · 30% save % · 15% sweeper actions/match · 10% claims/match · 10% goals conceded (inv.). Keepers are ranked by that composite score.

See [reports/statistical_analysis.md](reports/statistical_analysis.md) for descriptive statistics and correlation p-values. Known limitations: small per-keeper samples, xG-model dependency, no opponent adjustment, subjective weighting.

## Tech Stack

- **Python** — pandas, numpy, scikit-learn
- **Visualization** — matplotlib, seaborn, mplsoccer
- **Data Source** — StatsBomb open data (statsbombpy)
- **BI Tool** — Power BI

## Getting Started

Install dependencies (Python 3.10+):

```bash
pip install -r requirements.txt
```

## Pipeline — step by step, folder by folder

Run these from the project root, in order — each step reads the previous step's output.

**Step 1 — `python scripts/clean_data.py`**
Pulls all 51 Euro 2024 matches from StatsBomb's open data (network access, no local input needed).
Writes → `data/raw/euro2024_goalkeepers_raw.csv`, `data/processed/goalkeepers_clean.csv`, `shots_faced.csv`, `gk_events.csv`, `goal_kicks.csv`

**Step 2 — `python scripts/statistical_analysis.py --all`**
Requires an argument: a goalkeeper name (e.g. `"Jan Oblak"`) for one keeper, or `--all` for every keeper. Running it with no argument just prints usage and exits.
Reads ← `data/processed/goalkeepers_clean.csv`, `shots_faced.csv`, `gk_events.csv`
Writes → `reports/charts/individual/*.png` (shot maps, GSaE efficiency/ranking, action heatmaps)

**Step 3 — `python scripts/zscore_analysis.py`**
Reads ← `data/processed/goalkeepers_clean.csv`
Writes → `data/final/goalkeeper_analysis.csv`, `reports/charts/zscore_heatmap.png`, `zscore_overall.png`

**Step 4 — `python scripts/rank_goalkeepers.py`**
Reads ← `data/final/goalkeeper_analysis.csv` (must run after Step 3)
Writes → `data/final/gk_rank.csv`, `top10_gk_performance.csv`, `reports/charts/top10_composite.png`, `top10_zscore_heatmap.png`, `top10_radar.png`

**Step 5 — `python scripts/chart.py`**
Reads ← `data/processed/goalkeepers_clean.csv`; `data/final/gk_rank.csv` if present (ranking/radar charts are skipped with a warning otherwise, so run after Step 4)
Writes → `reports/charts/save_pct.png`, `xg_prevention.png`, `gk_actions.png`, `distribution.png`, `rank.png`, `radar_top5.png`

**Step 6 — `python scripts/dashboard.py`**
Reads ← `data/processed/*.csv`, `data/final/gk_rank.csv` (must run after Step 4)
Writes → `reports/charts/dashboards/dashboard_0N_<Name>.png` (top 3 keepers)

**Step 7 — `python scripts/stat_tests.py`**
Reads ← `data/processed/goalkeepers_clean.csv`, `data/final/goalkeeper_analysis.csv` (must run after Step 3)
Writes → `data/final/descriptive_stats.csv`, `correlation_pvalues.csv`, `reports/statistical_analysis.md`

**Step 8 (optional) — `python powerbi/prepare_data.py`**
Reads ← `data/processed/*.csv`, `data/final/gk_rank.csv` (must run after Step 4)
Writes → `powerbi/data/*.csv` (9 files ready to import into Power BI Desktop)

Or explore the full analysis in the [Jupyter notebook](notebooks/Euro2024_GK_Analysis.ipynb), which runs the same pipeline in one file.
