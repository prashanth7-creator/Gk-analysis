"""
Single goalkeeper deep-dive analysis with visualizations.
Reads: data/processed/ → Outputs: reports/charts/individual/
"""
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from mplsoccer import VerticalPitch
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "reports" / "charts" / "individual"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

BG = "#ffffff"
TEXT = "#1a1a1a"
BLUE = "#2979ff"
GREEN = "#00e676"
RED = "#ff1744"
YELLOW = "#ffd600"

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


def load_data():
    gk = pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")
    shots = pd.read_csv(PROC_DIR / "shots_faced.csv", low_memory=False)
    return gk, shots


def plot_shot_map_dark(gk_name, shots):
    gk_shots = shots[shots["gk_name"] == gk_name].copy()
    if gk_shots.empty:
        print(f"No shot data found for {gk_name}")
        return

    pitch = VerticalPitch(
        pitch_type="statsbomb", pitch_color="grass",
        line_color="white", half=True, goal_type="box",
    )
    fig, ax = pitch.draw(figsize=(8, 10))
    fig.patch.set_facecolor(BG)

    styles = {
        "Saved": (GREEN, "o"), "Goal": (RED, "X"),
        "Off T": (BLUE, "s"), "Blocked": (YELLOW, "D"),
        "Post": ("#ff9500", "^"), "Wayward": ("#8b949e", "P"),
    }

    for outcome, (color, marker) in styles.items():
        mask = gk_shots["outcome"] == outcome
        if mask.sum() == 0:
            continue
        pitch.scatter(
            gk_shots.loc[mask, "shot_x"], gk_shots.loc[mask, "shot_y"],
            s=gk_shots.loc[mask, "xg"] * 600 + 40,
            c=color, marker=marker, alpha=0.88,
            edgecolors="white", linewidths=0.5,
            label=f"{outcome} ({mask.sum()})", ax=ax,
        )

    total = len(gk_shots)
    ga = (gk_shots["outcome"] == "Goal").sum()
    xg_tot = gk_shots["xg"].sum()
    prev = xg_tot - ga

    fig.text(0.5, 0.98, f"Shot Map — {gk_name}", ha="center", fontsize=15, fontweight="bold", color=TEXT)
    fig.text(0.5, 0.95,
             f"Shots: {total}  ·  GA: {ga}  ·  xG: {xg_tot:.1f}  ·  Goals Prevented: {prev:+.1f}",
             ha="center", fontsize=10, color="#8b949e")
    ax.legend(loc="upper left", framealpha=0.7, labelcolor=TEXT,
              facecolor=BG, edgecolor="#cccccc", fontsize=9)
    plt.tight_layout()

    fname = CHARTS_DIR / f"shot_map_{gk_name.replace(' ', '_')}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fname}")


def plot_shot_map_green(gk_name, shots):
    gk_shots = shots[shots["gk_name"] == gk_name].copy()
    if gk_shots.empty:
        return

    pitch = VerticalPitch(
        pitch_type="statsbomb", pitch_color="grass",
        line_color="white", half=True, goal_type="box",
        linewidth=1.5, spot_scale=0.01,
    )
    fig, ax = pitch.draw(figsize=(9, 11))
    fig.set_facecolor(BG)

    styles = {
        "Saved": dict(color="#e60000", marker="o", label="Saved", zorder=5),
        "Goal": dict(color="#530be4", marker="*", label="Goal Conceded", zorder=6),
        "Blocked": dict(color="#ffea00", marker="s", label="Blocked", zorder=4),
        "Off T": dict(color="#1971b8", marker="^", label="Off Target", zorder=3),
        "Post": dict(color="#ff9100", marker="D", label="Post/Bar", zorder=4),
        "Wayward": dict(color="#b0bec5", marker="v", label="Wayward", zorder=3),
    }

    for outcome, style in styles.items():
        mask = gk_shots["outcome"] == outcome
        if mask.sum() == 0:
            continue
        sizes = gk_shots.loc[mask, "xg"] * 800 + 60
        pitch.scatter(
            gk_shots.loc[mask, "shot_x"], gk_shots.loc[mask, "shot_y"],
            s=sizes, c=style["color"], marker=style["marker"],
            alpha=0.88, edgecolors="white", linewidths=0.6,
            label=f"{style['label']} ({mask.sum()})", ax=ax, zorder=style["zorder"],
        )

    for _, row in gk_shots[gk_shots["xg"] > 0.30].iterrows():
        ax.annotate(
            f"xG {row['xg']:.2f}",
            (row["shot_y"], row["shot_x"]),
            fontsize=7, color="white", fontweight="bold",
            xytext=(0, 8), textcoords="offset points", ha="center",
            path_effects=[pe.withStroke(linewidth=2, foreground="black")],
        )

    total = len(gk_shots)
    ga = (gk_shots["outcome"] == "Goal").sum()
    saves = (gk_shots["outcome"] == "Saved").sum()
    xg_tot = gk_shots["xg"].sum()
    sv_pct = saves / max((saves + ga), 1) * 100
    prev = xg_tot - ga

    stats_text = (
        f"Shots faced: {total}   |   Saves: {saves}   |   Goals: {ga}\n"
        f"Save %: {sv_pct:.1f}%   |   xG faced: {xg_tot:.2f}   |   Goals prevented: {prev:+.2f}"
    )

    fig.text(0.5, 0.97, gk_name, ha="center", va="top", fontsize=17, fontweight="bold", color=TEXT)
    fig.text(0.5, 0.935, "UEFA Euro 2024 — Shot Map (GK perspective)", ha="center", va="top",
             fontsize=10, color="#555555")
    fig.text(0.5, 0.905, stats_text, ha="center", va="top", fontsize=9, color=TEXT, linespacing=1.6)

    ax.legend(loc="upper left", fontsize=9, framealpha=0.7, facecolor=BG,
              edgecolor="#cccccc", labelcolor=TEXT, markerscale=1.2)
    plt.tight_layout(rect=[0, 0.03, 1, 0.90])

    fname = CHARTS_DIR / f"green_shot_map_{gk_name.replace(' ', '_')}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {fname}")


def plot_gsae_vs_save_pct(gk_df, highlight_gk=None):
    """GSaE vs Save % Efficiency Analysis with quadrant classification."""
    df = gk_df.copy()
    df["gsae"] = df["goals_prevented"]  # GSaE = xG faced - goals conceded

    DARK_BG = "#0d1117"
    DARK_CARD = "#161b22"
    CYAN = "#00e5ff"
    WHITE = "#e6edf3"
    GRID = "#21262d"

    fig = plt.figure(figsize=(14, 8), facecolor=DARK_BG)
    ax = fig.add_axes([0.08, 0.10, 0.58, 0.78])
    ax.set_facecolor(DARK_BG)

    # Scatter all GKs
    ax.scatter(
        df["gsae"], df["save_pct"],
        c=CYAN, s=70, alpha=0.9, edgecolors="white", linewidths=0.5, zorder=5,
    )

    # Trend / regression line
    mask = df["gsae"].notna() & df["save_pct"].notna()
    if mask.sum() >= 2:
        z = np.polyfit(df.loc[mask, "gsae"], df.loc[mask, "save_pct"], 1)
        x_line = np.linspace(df["gsae"].min() - 0.3, df["gsae"].max() + 0.3, 100)
        y_line = np.polyval(z, x_line)
        ax.plot(x_line, y_line, color=CYAN, lw=2, alpha=0.5, zorder=3)
        ax.fill_between(x_line, y_line - 4, y_line + 4, color=CYAN, alpha=0.06, zorder=2)

    # Highlight specific GK
    if highlight_gk and highlight_gk in df["gk_name"].values:
        row = df[df["gk_name"] == highlight_gk].iloc[0]
        ax.scatter(
            row["gsae"], row["save_pct"],
            c="#ff6d00", s=200, marker="*", edgecolors="white", linewidths=1,
            zorder=10, label=highlight_gk,
        )
        ax.annotate(
            highlight_gk,
            (row["gsae"], row["save_pct"]),
            xytext=(8, 10), textcoords="offset points",
            fontsize=9, fontweight="bold", color="#ff6d00",
            arrowprops=dict(arrowstyle="->", color="#ff6d00", lw=1.2),
            zorder=11,
        )

    # Quadrant reference lines
    ax.axvline(0, color="#8b949e", ls=":", lw=0.8, alpha=0.5)
    med_save = df["save_pct"].median()
    ax.axhline(med_save, color="#8b949e", ls=":", lw=0.8, alpha=0.5)

    # Axis styling
    ax.set_xlabel("GSaE  (Goals Saved Above Expectation)", fontsize=12, color=WHITE)
    ax.set_ylabel("Save %", fontsize=12, color=WHITE)
    ax.tick_params(colors=WHITE, labelsize=10)
    ax.spines["bottom"].set_color(GRID)
    ax.spines["left"].set_color(GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color=GRID, alpha=0.4, ls="-", lw=0.5)
    ax.set_ylim(0, max(df["save_pct"].max() + 5, 95))

    # Title with cyan underline
    fig.text(0.08, 0.95, "GSaE vs. Save %  Efficiency Analysis",
             fontsize=18, fontweight="bold", color=WHITE, va="top")
    fig.patches.append(plt.Rectangle(
        (0.08, 0.925), 0.35, 0.006, transform=fig.transFigure,
        facecolor=CYAN, edgecolor="none", zorder=20,
    ))

    # ── Quadrant info boxes on the right ─────────────────────
    box_x, box_w, box_h = 0.70, 0.27, 0.17

    # Top Right — Elite
    fig.patches.append(plt.Rectangle(
        (box_x, 0.72), box_w, box_h, transform=fig.transFigure,
        facecolor=DARK_CARD, edgecolor="#2e7d32", linewidth=2, zorder=15,
    ))
    fig.text(box_x + 0.015, 0.87, "Top Right", fontsize=12, fontweight="bold",
             color="#4caf50", va="top", transform=fig.transFigure, zorder=16)
    fig.text(box_x + 0.015, 0.82, "High GSaE + High Save %\nElite performers",
             fontsize=10, color=WHITE, va="top", transform=fig.transFigure,
             linespacing=1.5, zorder=16)

    # Bottom Right — Quality over quantity
    fig.patches.append(plt.Rectangle(
        (box_x, 0.49), box_w, box_h, transform=fig.transFigure,
        facecolor=DARK_CARD, edgecolor="#1565c0", linewidth=2, zorder=15,
    ))
    fig.text(box_x + 0.015, 0.64, "Bottom Right", fontsize=12, fontweight="bold",
             color="#42a5f5", va="top", transform=fig.transFigure, zorder=16)
    fig.text(box_x + 0.015, 0.59, "High GSaE + Lower Save %\nQuality over quantity",
             fontsize=10, color=WHITE, va="top", transform=fig.transFigure,
             linespacing=1.5, zorder=16)

    # Left — Underperforming
    fig.patches.append(plt.Rectangle(
        (box_x, 0.26), box_w, box_h, transform=fig.transFigure,
        facecolor="#3e1a1a", edgecolor="#c62828", linewidth=2, zorder=15,
    ))
    fig.text(box_x + 0.015, 0.41, "Left Quadrants", fontsize=12, fontweight="bold",
             color="#ef5350", va="top", transform=fig.transFigure, zorder=16)
    fig.text(box_x + 0.015, 0.36, "Negative GSaE\nUnder-performing vs. xG",
             fontsize=10, color=WHITE, va="top", transform=fig.transFigure,
             linespacing=1.5, zorder=16)

    # GK name labels on dots
    for _, row in df.iterrows():
        if highlight_gk and row["gk_name"] == highlight_gk:
            continue
        ax.annotate(
            row["gk_name"].split()[-1],
            (row["gsae"], row["save_pct"]),
            xytext=(4, 4), textcoords="offset points",
            fontsize=6.5, color=WHITE, alpha=0.6, zorder=6,
        )

    if highlight_gk:
        suffix = f"_{highlight_gk.replace(' ', '_')}"
    else:
        suffix = "_all"
    fname = CHARTS_DIR / f"gsae_efficiency{suffix}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"  Saved: {fname}")


def plot_gsae_bar_ranking(gk_df, highlight_gk=None):
    """Horizontal bar chart ranking GKs by GSaE."""
    DARK_BG = "#0d1117"
    WHITE = "#e6edf3"
    GRID = "#21262d"

    df = gk_df.copy()
    df["gsae"] = df["goals_prevented"]
    df = df.sort_values("gsae", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 7), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)

    colors = []
    for _, row in df.iterrows():
        if highlight_gk and row["gk_name"] == highlight_gk:
            colors.append("#ff6d00")
        elif row["gsae"] >= 0:
            colors.append("#00e676")
        else:
            colors.append("#ff1744")

    bars = ax.barh(df["gk_name"], df["gsae"], color=colors, edgecolor="none", height=0.65)

    for bar, (_, row) in zip(bars, df.iterrows()):
        val = row["gsae"]
        offset = 0.05 if val >= 0 else -0.05
        ha = "left" if val >= 0 else "right"
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f'{val:+.2f}', va="center", ha=ha, fontsize=8.5,
                fontweight="bold", color=WHITE)

    ax.axvline(0, color="#8b949e", ls="-", lw=1, alpha=0.6)
    ax.set_xlabel("GSaE  (Goals Saved Above Expectation)", fontsize=11, color=WHITE)
    ax.set_title("Euro 2024 — Goalkeeper GSaE Ranking\n"
                 "Green = overperforming xG  ·  Red = underperforming",
                 fontsize=13, fontweight="bold", color=WHITE, pad=14)
    ax.tick_params(colors=WHITE, labelsize=9)
    ax.spines["bottom"].set_color(GRID)
    ax.spines["left"].set_color(GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color=GRID, alpha=0.3)
    plt.tight_layout()

    suffix = f"_{highlight_gk.replace(' ', '_')}" if highlight_gk else "_all"
    fname = CHARTS_DIR / f"gsae_ranking{suffix}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"  Saved: {fname}")


def plot_gk_action_heatmap(gk_name, gk_events_path=None):
    """Pitch heatmap of a GK's action locations (saves, punches, claims)."""
    if gk_events_path is None:
        gk_events_path = PROC_DIR / "gk_events.csv"
    if not gk_events_path.exists():
        print(f"  Skipping action heatmap — {gk_events_path} not found")
        return

    import ast
    gk_ev = pd.read_csv(gk_events_path, low_memory=False)
    gk_ev = gk_ev[gk_ev["player_name"] == gk_name].copy()
    if gk_ev.empty:
        print(f"  No GK events for {gk_name}")
        return

    def parse_loc(val):
        if isinstance(val, str) and val.startswith("["):
            try:
                coords = ast.literal_eval(val)
                return coords[0], coords[1]
            except Exception:
                return None, None
        return None, None

    gk_ev[["loc_x", "loc_y"]] = gk_ev["location"].apply(
        lambda v: pd.Series(parse_loc(v))
    )
    gk_ev = gk_ev.dropna(subset=["loc_x", "loc_y"])
    if gk_ev.empty:
        return

    pitch = VerticalPitch(
        pitch_type="statsbomb", pitch_color="grass",
        line_color="white", half=True, goal_type="box", linewidth=1.5,
    )
    fig, ax = pitch.draw(figsize=(9, 11))
    fig.set_facecolor("#1a472a")

    action_styles = {
        "Shot Faced": ("#00e676", "o", "Save"),
        "Punch": ("#ffd600", "D", "Punch"),
        "Claim": ("#42a5f5", "s", "Claim"),
        "Keeper Sweeper": ("#00e5ff", "^", "Sweeper"),
        "Smother": ("#ff9100", "P", "Smother"),
    }

    action_col = "gk_action" if "gk_action" in gk_ev.columns else "goalkeeper_type"
    for action, (color, marker, label) in action_styles.items():
        mask = gk_ev[action_col].str.contains(action, case=False, na=False)
        if mask.sum() == 0:
            continue
        pitch.scatter(
            gk_ev.loc[mask, "loc_x"], gk_ev.loc[mask, "loc_y"],
            s=80, c=color, marker=marker, alpha=0.85,
            edgecolors="white", linewidths=0.5,
            label=f"{label} ({mask.sum()})", ax=ax, zorder=5,
        )

    fig.text(0.5, 0.97, f"Action Heatmap — {gk_name}", ha="center",
             fontsize=16, fontweight="bold", color="white",
             path_effects=[pe.withStroke(linewidth=3, foreground="#1a472a")])
    fig.text(0.5, 0.935, f"Euro 2024 — {len(gk_ev)} total actions on pitch",
             ha="center", fontsize=10, color="#c8e6c9",
             path_effects=[pe.withStroke(linewidth=2, foreground="#1a472a")])

    ax.legend(loc="upper left", fontsize=9, framealpha=0.6,
              facecolor="#1b5e20", edgecolor="white", labelcolor="white")
    plt.tight_layout(rect=[0, 0.02, 1, 0.92])

    fname = CHARTS_DIR / f"action_heatmap_{gk_name.replace(' ', '_')}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {fname}")


def print_gk_summary(gk_name, gk_df):
    row = gk_df[gk_df["gk_name"] == gk_name]
    if row.empty:
        print(f"No data for {gk_name}")
        return

    row = row.iloc[0]
    print(f"\n{'=' * 55}")
    print(f"  {gk_name} — Euro 2024 Performance")
    print(f"{'=' * 55}")
    print(f"  Matches Played:      {int(row['matches_played'])}")
    print(f"  Shots Faced:         {int(row['shots_faced'])}")
    print(f"  Saves:               {int(row['saves'])}")
    print(f"  Save %:              {row['save_pct']:.1f}%")
    print(f"  xG Faced:            {row['xg_faced']:.2f}")
    print(f"  Goals Conceded:      {int(row['goals_conceded'])}")
    print(f"  Goals Prevented:     {row['goals_prevented']:+.2f}")
    print(f"  Sweeper Actions/M:   {row['sweeper_per_match']:.2f}")
    print(f"  Claims/M:            {row['claims_per_match']:.2f}")
    print(f"  Punches/M:           {row['punches_per_match']:.2f}")
    print(f"  Goal Kicks/M:        {row['goal_kicks_per_match']:.2f}")
    print(f"{'=' * 55}")


def analyze_single_gk(gk_name):
    gk, shots = load_data()

    if gk_name not in gk["gk_name"].values:
        print(f"'{gk_name}' not found. Available GKs:")
        for name in sorted(gk["gk_name"].values):
            print(f"  - {name}")
        return

    print_gk_summary(gk_name, gk)
    print("\nGenerating charts...")
    plot_shot_map_dark(gk_name, shots)
    plot_shot_map_green(gk_name, shots)
    plot_gsae_vs_save_pct(gk, highlight_gk=gk_name)
    plot_gsae_bar_ranking(gk, highlight_gk=gk_name)
    plot_gk_action_heatmap(gk_name)
    print("\nDone!")


def analyze_all_gks():
    gk, shots = load_data()
    print(f"Generating individual analysis for {len(gk)} goalkeepers...\n")

    # Overall GSaE charts (all GKs)
    print("\nGenerating GSaE analysis charts...")
    plot_gsae_vs_save_pct(gk)
    plot_gsae_bar_ranking(gk)

    for _, row in gk.iterrows():
        name = row["gk_name"]
        print(f"\n--- {name} ---")
        print_gk_summary(name, gk)
        plot_shot_map_dark(name, shots)
        plot_shot_map_green(name, shots)
        plot_gsae_vs_save_pct(gk, highlight_gk=name)
        plot_gsae_bar_ranking(gk, highlight_gk=name)
        plot_gk_action_heatmap(name)

    print(f"\nAll individual reports saved to: {CHARTS_DIR}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        gk_name = " ".join(sys.argv[1:])
        if gk_name.lower() == "--all":
            analyze_all_gks()
        else:
            analyze_single_gk(gk_name)
    else:
        print("Usage:")
        print('  python statistical_analysis.py "Goalkeeper Name"')
        print("  python statistical_analysis.py --all")
        print("\nAvailable goalkeepers:")
        gk, _ = load_data()
        for name in sorted(gk["gk_name"].values):
            print(f"  - {name}")
