"""
Generate all tournament-level charts.
Reads: data/processed/ + data/final/ → Writes: reports/charts/
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
FINAL_DIR = ROOT / "data" / "final"
CHARTS_DIR = ROOT / "reports" / "charts"

BG = "#ffffff"
TEXT = "#1a1a1a"
BLUE = "#1a73e8"
GREEN = "#2e7d32"
RED = "#d32f2f"
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


def plot_save_pct(gk):
    top = gk.sort_values("save_pct", ascending=True)
    med = gk["save_pct"].median()

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = [GREEN if v >= med else RED for v in top["save_pct"]]
    bars = ax.barh(top["gk_name"], top["save_pct"], color=colors, edgecolor="none", height=0.65)

    ax.axvline(med, color=YELLOW, ls="--", lw=1.5, alpha=0.8, label=f"Median: {med:.1f}%")
    ax.set_xlabel("Save Percentage (%)", fontsize=11)
    ax.set_title("Euro 2024 — Goalkeeper Save Percentage", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlim(0, 110)
    ax.legend(framealpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "save_pct.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: save_pct.png")


def plot_xg_scatter(gk):
    fig, ax = plt.subplots(figsize=(13, 8))
    sc = ax.scatter(
        gk["xg_faced"], gk["goals_conceded"],
        c=gk["goals_prevented"], cmap="RdYlGn",
        s=gk["matches_played"] * 35 + 40,
        edgecolors="#333333", linewidths=0.6, alpha=0.92,
    )

    lim = max(gk["xg_faced"].max(), gk["goals_conceded"].max()) + 0.5
    ax.plot([0, lim], [0, lim], color="#8b949e", ls="--", lw=1.3, alpha=0.6, label="Expected (xG = GA)")

    cbar = plt.colorbar(sc, ax=ax, pad=0.01)
    cbar.set_label("Goals Prevented (xG - GA)", color=TEXT, fontsize=10)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT)

    ax.set_xlabel("Total xG Faced", fontsize=11)
    ax.set_ylabel("Goals Conceded", fontsize=11)
    ax.set_title("Euro 2024 GKs — xG Faced vs Goals Conceded\n"
                 "(Green = more goals prevented · bubble size = matches played)",
                 fontsize=13, fontweight="bold", pad=14)
    ax.legend(framealpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "xg_prevention.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: xg_prevention.png")


def plot_actions(gk):
    top10 = gk.nlargest(min(10, len(gk)), "total_gk_events").copy()
    x = np.arange(len(top10))
    width = 0.6

    fig, ax = plt.subplots(figsize=(13, 6))
    bottom = np.zeros(len(top10))

    for col, color, label in [
        ("sweeper_per_match", BLUE, "Sweeper Actions / match"),
        ("claims_per_match", GREEN, "Claims / match"),
        ("punches_per_match", YELLOW, "Punches / match"),
    ]:
        vals = top10[col].values
        ax.bar(x, vals, width, bottom=bottom, color=color, edgecolor="none", label=label)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels([n.split()[-1] for n in top10["gk_name"]], rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("Actions per Match", fontsize=11)
    ax.set_title("Euro 2024 — Goalkeeper Actions per Match (Top 10 by Volume)", fontsize=13, fontweight="bold", pad=14)
    ax.legend(framealpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "gk_actions.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: gk_actions.png")


def plot_ranking(gk_rank):
    top_n = min(15, len(gk_rank))
    top = gk_rank.head(top_n)
    pal = cm.Blues(np.linspace(0.4, 0.9, top_n))[::-1]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(top["gk_name"][::-1], top["composite_score"][::-1], color=pal, edgecolor="none", height=0.65)

    ax.set_xlabel("Composite Performance Score", fontsize=11)
    ax.set_title(f"Euro 2024 — Goalkeeper Rankings (Top {top_n})\n"
                 "Score = Goals Prev. 35% · Save% 30% · Sweeper 15% · Claims 10% · GA 10%",
                 fontsize=13, fontweight="bold", pad=14)
    min_score = top["composite_score"].min()
    ax.set_xlim(min(min_score - 0.15, -0.05), top["composite_score"].max() * 1.4)
    ax.axvline(0, color="#cccccc", lw=0.8, ls="--", alpha=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "rank.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: rank.png")


def plot_radar(gk_rank):
    def norm(series, ascending=True):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series(0.5, index=series.index)
        n = (series - mn) / (mx - mn)
        return n if ascending else 1 - n

    gk_r = gk_rank.copy()
    gk_r["n_save_pct"] = norm(gk_r["save_pct"])
    gk_r["n_gp"] = norm(gk_r["goals_prevented"])
    gk_r["n_sweeper"] = norm(gk_r["sweeper_per_match"])
    gk_r["n_claims"] = norm(gk_r["claims_per_match"])
    gk_r["n_ga"] = norm(gk_r["goals_conceded"], ascending=False)

    top5 = gk_r.head(5)
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
    ax.set_title("Euro 2024 — Top 5 Goalkeepers\n(all metrics normalised 0-1)",
                 fontsize=14, fontweight="bold", pad=35, color=TEXT)
    ax.legend(loc="upper right", bbox_to_anchor=(1.38, 1.12),
              labelcolor=TEXT, facecolor=BG, edgecolor="#cccccc", fontsize=10)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "radar_top5.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: radar_top5.png")


def plot_distribution(gk):
    gk_sorted = gk.sort_values("goal_kicks_per_match", ascending=True)

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # ── Left: Goal Kicks per Match bar chart ────────────────────────────────
    med_gk = gk_sorted["goal_kicks_per_match"].median()
    colors = [GREEN if v >= med_gk else BLUE for v in gk_sorted["goal_kicks_per_match"]]
    bars = axes[0].barh(gk_sorted["gk_name"], gk_sorted["goal_kicks_per_match"],
                        color=colors, edgecolor="none", height=0.65)
    for bar, val in zip(bars, gk_sorted["goal_kicks_per_match"]):
        axes[0].text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                     f"{val:.1f}", va="center", ha="left", fontsize=9, fontweight="bold", color=TEXT)
    axes[0].axvline(med_gk, color=YELLOW, ls="--", lw=1.5, alpha=0.8, label=f"Median: {med_gk:.1f}")
    axes[0].set_xlabel("Goal Kicks per Match", fontsize=11)
    axes[0].set_title("Goal Kicks per Match", fontsize=13, fontweight="bold", pad=12)
    axes[0].legend(framealpha=0.25, fontsize=9)
    axes[0].set_xlim(0, gk_sorted["goal_kicks_per_match"].max() * 1.25)
    axes[0].spines[["top", "right"]].set_visible(False)
    axes[0].grid(axis="x", alpha=0.3)

    # ── Right: Avg GK Length vs Goals Prevented/match scatter ───────────────
    sc = axes[1].scatter(
        gk["avg_gk_length"], gk["gp_per_match"],
        c=gk["save_pct"], cmap="YlGn",
        s=gk["matches_played"] * 40 + 80,
        edgecolors="#333333", lw=0.8, alpha=0.9, zorder=5,
    )
    axes[1].axhline(0, color="#cccccc", lw=0.8, ls="--", alpha=0.7)
    cbar = plt.colorbar(sc, ax=axes[1], pad=0.02)
    cbar.set_label("Save %", color=TEXT, fontsize=10)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT)
    axes[1].set_xlabel("Avg Goal Kick Length (m)", fontsize=11)
    axes[1].set_ylabel("Goals Prevented per Match", fontsize=11)
    axes[1].set_title("Kick Length vs Goals Prevented/Match\n(bubble size = matches played · colour = save %)",
                      fontsize=12, fontweight="bold", pad=12)
    axes[1].spines[["top", "right"]].set_visible(False)
    axes[1].grid(alpha=0.25)

    plt.suptitle("Euro 2024 — Goal Kick Distribution Analysis", fontsize=15, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: distribution.png")


def main():
    gk = pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")
    print(f"Loaded {len(gk)} goalkeepers\n")

    print("Generating tournament charts...")
    plot_save_pct(gk)
    plot_xg_scatter(gk)
    plot_actions(gk)
    plot_distribution(gk)

    rank_file = FINAL_DIR / "gk_rank.csv"
    if rank_file.exists():
        gk_rank = pd.read_csv(rank_file)
        plot_ranking(gk_rank)
        plot_radar(gk_rank)
    else:
        print(f"\n  Warning: {rank_file} not found. Run rank_goalkeepers.py first for ranking charts.")

    print("\nAll charts saved to: reports/charts/")


if __name__ == "__main__":
    main()
