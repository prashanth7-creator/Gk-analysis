"""
Build composite goalkeeper ranking with weighted Z-scores.
Reads: data/final/goalkeeper_analysis.csv → Writes: data/final/gk_rank.csv + top10 report
"""
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
FINAL_DIR = ROOT / "data" / "final"
CHARTS_DIR = ROOT / "reports" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

BG = "#ffffff"
TEXT = "#1a1a1a"
GREEN = "#2e7d32"
RED = "#d32f2f"
BLUE = "#1a73e8"
YELLOW = "#f9a825"

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

WEIGHTS = {
    "z_goals_prevented": 0.35,
    "z_save_pct": 0.30,
    "z_sweeper_per_match": 0.15,
    "z_claims_per_match": 0.10,
    "z_goals_conceded": 0.10,
}

Z_METRICS = {
    "z_save_pct": "Save %",
    "z_goals_prevented": "Goals Prev.",
    "z_sweeper_per_match": "Sweeper",
    "z_claims_per_match": "Claims",
    "z_goals_conceded": "GA (inv.)",
    "z_gp_per_match": "GP/Match",
    "z_xg_faced": "xG Faced (inv.)",
}


def print_top10_report(top10):
    print("\n" + "=" * 80)
    print("  TOP 10 GOALKEEPER INDIVIDUAL PERFORMANCE — Euro 2024")
    print("  (Ranked by Weighted Composite Z-Score)")
    print("=" * 80)

    for i, (_, row) in enumerate(top10.iterrows(), 1):
        print(f"\n  {'─' * 74}")
        print(f"  #{i}  {row['gk_name']}")
        print(f"  {'─' * 74}")
        print(f"    Composite Score:    {row['composite_score']:+.3f}")
        print(f"    Matches Played:     {int(row['matches_played'])}")
        print(f"    Shots Faced:        {int(row['shots_faced'])}   |   Saves: {int(row['saves'])}")
        print(f"    Save %:             {row['save_pct']:.1f}%")
        print(f"    xG Faced:           {row['xg_faced']:.2f}")
        print(f"    Goals Conceded:     {int(row['goals_conceded'])}")
        print(f"    Goals Prevented:    {row['goals_prevented']:+.2f}")
        print(f"    Sweeper/Match:      {row['sweeper_per_match']:.2f}")
        print(f"    Claims/Match:       {row['claims_per_match']:.2f}")
        print(f"    Z-Scores:")
        for zcol, label in Z_METRICS.items():
            if zcol in row.index:
                print(f"      {label:<18s}  {row[zcol]:+.3f}")
    print(f"\n  {'=' * 74}")


def plot_top10_composite(top10):
    fig, ax = plt.subplots(figsize=(14, 7))

    names = top10["gk_name"].values[::-1]
    scores = top10["composite_score"].values[::-1]
    pal = cm.viridis(np.linspace(0.3, 0.95, len(names)))

    bars = ax.barh(names, scores, color=pal, edgecolor="none", height=0.65)

    for bar, row_tuple in zip(bars, top10.iloc[::-1].itertuples()):
        ax.text(
            bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{row_tuple.composite_score:+.3f}  |  Sv% {row_tuple.save_pct:.0f}%  |  Prev {row_tuple.goals_prevented:+.1f}  |  MP {int(row_tuple.matches_played)}",
            va="center", ha="left", fontsize=9, color=TEXT,
        )

    ax.axvline(0, color="#8b949e", lw=1, ls="--", alpha=0.6)
    ax.set_xlabel("Composite Z-Score (higher = better)", fontsize=11)
    ax.set_title(
        "Euro 2024 — Top 10 Goalkeeper Performance\n"
        "Score = Goals Prev. 35% · Save% 30% · Sweeper 15% · Claims 10% · GA 10%",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.set_xlim(min(scores) - 0.15, max(scores) * 1.6)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    fname = CHARTS_DIR / "top10_composite.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fname}")


def plot_top10_zscore_heatmap(top10):
    z_cols = [c for c in Z_METRICS if c in top10.columns]
    labels = [Z_METRICS[c] for c in z_cols]
    data = top10[z_cols].values

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=-2.5, vmax=2.5)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
    ax.set_yticks(range(len(top10)))
    ax.set_yticklabels(
        [f"#{i+1} {n}" for i, n in enumerate(top10["gk_name"].values)],
        fontsize=9,
    )

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            color = "black" if abs(val) < 1.2 else TEXT
            ax.text(j, i, f"{val:+.2f}", ha="center", va="center", fontsize=8, color=color)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Z-Score (positive = better)", color=TEXT)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT)

    ax.set_title("Euro 2024 — Top 10 GK Z-Score Breakdown", fontsize=14, fontweight="bold", pad=14)
    plt.tight_layout()
    fname = CHARTS_DIR / "top10_zscore_heatmap.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fname}")


def plot_top10_radar(top10):
    def norm(series, ascending=True):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series(0.5, index=series.index)
        n = (series - mn) / (mx - mn)
        return n if ascending else 1 - n

    gk_r = top10.copy()
    gk_r["n_save_pct"] = norm(gk_r["save_pct"])
    gk_r["n_gp"] = norm(gk_r["goals_prevented"])
    gk_r["n_sweeper"] = norm(gk_r["sweeper_per_match"])
    gk_r["n_claims"] = norm(gk_r["claims_per_match"])
    gk_r["n_ga"] = norm(gk_r["goals_conceded"], ascending=False)

    metrics = ["n_save_pct", "n_gp", "n_sweeper", "n_claims", "n_ga"]
    labels = ["Save %", "Goals\nPrevented", "Sweeper\nActions", "Claims", "GA\n(inv.)"]
    N = len(metrics)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.plot(angles, [r] * (N + 1), color="#cccccc", lw=0.7, zorder=0)

    cmap = plt.cm.tab10
    top5 = gk_r.head(5)
    for i, (_, row) in enumerate(top5.iterrows()):
        vals = [row[m] for m in metrics] + [row[metrics[0]]]
        color = cmap(i)
        ax.plot(angles, vals, "o-", lw=2.2, ms=5, color=color, label=row["gk_name"])
        ax.fill(angles, vals, alpha=0.18, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=TEXT, fontsize=11)
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.spines["polar"].set_color("#cccccc")
    ax.grid(False)
    ax.set_title("Euro 2024 — Top 5 Goalkeepers (normalised 0-1)",
                 fontsize=14, fontweight="bold", pad=35, color=TEXT)
    ax.legend(loc="upper right", bbox_to_anchor=(1.38, 1.12),
              labelcolor=TEXT, facecolor=BG, edgecolor="#cccccc", fontsize=10)
    plt.tight_layout()
    fname = CHARTS_DIR / "top10_radar.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fname}")


def main():
    gk = pd.read_csv(FINAL_DIR / "goalkeeper_analysis.csv")
    print(f"Loaded {len(gk)} goalkeepers")

    print("\nWeights:")
    for col, w in WEIGHTS.items():
        label = col.replace("z_", "").replace("_", " ").title()
        print(f"  {label:<25s} {w*100:.0f}%")

    gk["composite_score"] = sum(gk[col] * w for col, w in WEIGHTS.items())
    gk = gk.sort_values("composite_score", ascending=False).reset_index(drop=True)
    gk.index += 1
    gk.index.name = "rank"

    output_cols = [
        "gk_name", "matches_played", "shots_faced", "saves", "save_pct",
        "xg_faced", "goals_conceded", "goals_prevented",
        "sweeper_per_match", "claims_per_match",
        "z_save_pct", "z_goals_prevented", "z_sweeper_per_match",
        "z_claims_per_match", "z_goals_conceded",
        "z_gp_per_match", "z_xg_faced",
        "composite_score",
    ]
    rank_df = gk[[c for c in output_cols if c in gk.columns]]

    rank_df.to_csv(FINAL_DIR / "gk_rank.csv")
    print(f"\nSaved: {FINAL_DIR / 'gk_rank.csv'}")

    print("\nFull Rankings:")
    print("=" * 65)
    for i, (_, row) in enumerate(rank_df.iterrows(), 1):
        print(
            f"  {i:2d}. {row['gk_name']:<25s}  "
            f"Score: {row['composite_score']:+.3f}  |  "
            f"MP: {int(row['matches_played'])}  |  "
            f"Sv%: {row['save_pct']:.1f}%  |  "
            f"Prev: {row['goals_prevented']:+.1f}"
        )

    top10 = rank_df.head(10).copy()
    top10.to_csv(FINAL_DIR / "top10_gk_performance.csv")
    print(f"\nSaved: {FINAL_DIR / 'top10_gk_performance.csv'}")

    print_top10_report(top10)

    print("\nGenerating Top 10 charts...")
    plot_top10_composite(top10)
    plot_top10_zscore_heatmap(top10)
    plot_top10_radar(top10)

    print("\nDone!")


if __name__ == "__main__":
    main()
