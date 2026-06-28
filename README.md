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
│   ├── raw/                  # Raw StatsBomb data
│   ├── processed/            # Cleaned and transformed data
│   └── final/                # Analysis-ready datasets
├── scripts/
│   ├── clean_data.py         # Data cleaning and preprocessing
│   ├── statistical_analysis.py  # Core statistical analysis
│   ├── zscore_analysis.py    # Z-score based ranking
│   ├── rank_goalkeepers.py   # Final ranking logic
│   ├── chart.py              # Visualization generation
│   └── dashboard.py          # Dashboard creation
├── notebooks/
│   └── Euro2024_GK_Analysis.ipynb  # Full analysis notebook
├── powerbi/
│   ├── data/                 # Power BI ready datasets
│   ├── dax_measures.dax      # DAX measures for Power BI
│   └── prepare_data.py       # Data preparation for Power BI
└── reports/
    └── charts/               # Generated visualizations
```

## Tech Stack

- **Python** — pandas, numpy, scikit-learn
- **Visualization** — matplotlib, seaborn, mplsoccer
- **Data Source** — StatsBomb open data (statsbombpy)
- **BI Tool** — Power BI

## Getting Started

```bash
pip install -r requirements.txt
```

Run the analysis pipeline:

```bash
python scripts/clean_data.py
python scripts/statistical_analysis.py
python scripts/zscore_analysis.py
python scripts/rank_goalkeepers.py
python scripts/chart.py
```

Or explore the full analysis in the [Jupyter notebook](notebooks/Euro2024_GK_Analysis.ipynb).
