"""
Z-score comparison across all Euro 2024 goalkeepers.
Reads: data/processed/goalkeepers_clean.csv → Writes: data/final/goalkeeper_analysis.csv + charts
"""
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
FINAL_DIR = ROOT / "data" / "final"
CHARTS_DIR = ROOT / "reports" / "charts"

BG = "#ffffff"
TEXT = "#1a1a1a"
GREEN = "#2e7d32"
RED = "#d32f2f"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "text.color": TEXT,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "axes.edgecolor": "#cccccc",
    "grid.color": "#e0e0e0",
    "axes.titlecolor": TEXT,
})

METRICS = {
    "save_pct": {"label": "Save %", "higher_better": True},
    "goals_prevented": {"label": "Goals Prevented", "higher_better": True},
    "sweeper_per_match": {"label": "Sweeper/Match", "higher_better": True},
    "claims_per_match": {"label": "Claims/Match", "higher_better": True},
    "goals_conceded": {"label": "Goals Conceded", "higher_better": False},
    "xg_faced": {"label": "xG Faced", "higher_better": False},
    "gp_per_match": {"label": "Goals Prev./Match", "higher_better": True},
}


def compute_zscores(gk):
    for col, info in METRICS.items():
        mean = gk[col].mean()
        std = gk[col].std()
        if std == 0:
            gk[f"z_{col}"] = 0.0
        else:
            z = (gk[col] - mean) / std
            gk[f"z_{col}"] = z if info["higher_better"] else -z
    return gk


def plot_zscore_heatmap(gk):
    z_cols = [f"z_{c}" for c in METRICS]
    labels = [METRICS[c]["label"] for c in METRICS]

    gk_sorted = gk.sort_values("z_save_pct", ascending=False)
    data = gk_sorted[z_cols].values

    fig, ax = plt.subplots(figsize=(14, max(8, len(gk) * 0.5)))

    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=-2.5, vmax=2.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
    ax.set_yticks(range(len(gk_sorted)))
    ax.set_yticklabels(gk_sorted["gk_name"].values, fontsize=9)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            color = "black" if abs(val) < 1.2 else TEXT
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7.5, color=color)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Z-Score (positive = better)", color=TEXT)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT)

    ax.set_title("Euro 2024 — Goalkeeper Z-Score Comparison", fontsize=14, fontweight="bold", pad=14)
    plt.tight_layout()

    fname = CHARTS_DIR / "zscore_heatmap.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fname}")


def plot_zscore_bars(gk):
    z_cols = [f"z_{c}" for c in METRICS]
    gk["z_avg"] = gk[z_cols].mean(axis=1)
    gk_sorted = gk.sort_values("z_avg", ascending=True)

    fig, ax = plt.subplots(figsize=(12, max(7, len(gk) * 0.45)))
    colors = [GREEN if v > 0 else RED for v in gk_sorted["z_avg"]]
    ax.barh(gk_sorted["gk_name"], gk_sorted["z_avg"], color=colors, edgecolor="none", height=0.65)

    for i, (val, name) in enumerate(zip(gk_sorted["z_avg"], gk_sorted["gk_name"])):
        offset = 0.02 if val >= 0 else -0.02
        ha = "left" if val >= 0 else "right"
        ax.text(val + offset, i, f"{val:.2f}", va="center", ha=ha, fontsize=9, color=TEXT)

    ax.axvline(0, color="#8b949e", lw=1, ls="--", alpha=0.6)
    ax.set_xlabel("Average Z-Score (higher = better)", fontsize=11)
    ax.set_title("Euro 2024 — Overall GK Performance (Avg Z-Score)", fontsize=14, fontweight="bold", pad=14)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()

    fname = CHARTS_DIR / "zscore_overall.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fname}")


def main():
    gk = pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")
    print(f"Loaded {len(gk)} goalkeepers")

    print("\nComputing Z-scores...")
    gk = compute_zscores(gk)

    z_cols = [f"z_{c}" for c in METRICS]
    gk["z_avg"] = gk[z_cols].mean(axis=1)

    gk.to_csv(FINAL_DIR / "goalkeeper_analysis.csv", index=False)
    print(f"Saved: {FINAL_DIR / 'goalkeeper_analysis.csv'}")

    print("\nGenerating Z-score charts...")
    plot_zscore_heatmap(gk)
    plot_zscore_bars(gk)

    print("\nZ-Score Rankings:")
    print("-" * 50)
    for i, (_, row) in enumerate(gk.sort_values("z_avg", ascending=False).iterrows(), 1):
        print(f"  {i:2d}. {row['gk_name']:<25s}  Z-avg: {row['z_avg']:+.3f}")

    print("\nDone!")


if __name__ == "__main__":
    main()
