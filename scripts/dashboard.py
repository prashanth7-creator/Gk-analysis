"""
Individual GK dashboard: stat cards + pitch maps + z-score radar.
Reads: data/processed/ + data/final/ → Writes: reports/charts/dashboards/
"""
import sys
import ast
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
from mplsoccer import Pitch
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
FINAL_DIR = ROOT / "data" / "final"
CHARTS_DIR = ROOT / "reports" / "charts" / "dashboards"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

BG = "#ffffff"
CARD_BG = "#f5f5f5"
CYAN = "#00897b"
TEXT = "#1a1a1a"
RED = "#d32f2f"
LIME = "#43a047"
GRAY = "#555555"
BORDER = "#00897b"


def parse_loc(val):
    if isinstance(val, str):
        try:
            r = ast.literal_eval(val)
            if isinstance(r, (list, tuple)) and len(r) >= 2:
                return float(r[0]), float(r[1])
        except Exception:
            pass
    return None


def load_data():
    gk = pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")
    shots = pd.read_csv(PROC_DIR / "shots_faced.csv", low_memory=False)
    events = pd.read_csv(PROC_DIR / "gk_events.csv", low_memory=False)
    kicks = pd.read_csv(PROC_DIR / "goal_kicks.csv", low_memory=False)
    rank = pd.read_csv(FINAL_DIR / "gk_rank.csv")
    return gk, shots, events, kicks, rank


def draw_card(fig, x, y, w, h, value, label):
    ax = fig.add_axes([x, y, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor(CARD_BG)
    for sp in ax.spines.values():
        sp.set_color(BORDER)
        sp.set_linewidth(1.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(0.5, 0.58, str(value), ha="center", va="center",
            fontsize=20, fontweight="bold", color=CYAN, family="monospace")
    ax.text(0.5, 0.18, label, ha="center", va="center",
            fontsize=7.5, color=GRAY, linespacing=1.3)


def pitch_ax(fig, pos, title=""):
    ax = fig.add_subplot(pos)
    pitch = Pitch(pitch_type="statsbomb", pitch_color="grass",
                  line_color="white", linewidth=1, goal_type="box")
    pitch.draw(ax=ax)
    for sp in ax.spines.values():
        sp.set_color("#cccccc")
    if title:
        ax.set_title(title, fontsize=9, color=GRAY, pad=6)
    return pitch, ax


def panel_saves(fig, pos, gk_name, shots_df):
    saved = shots_df[(shots_df["gk_name"] == gk_name) & (shots_df["outcome"] == "Saved")]
    goals = shots_df[(shots_df["gk_name"] == gk_name) & (shots_df["outcome"] == "Goal")]
    others = shots_df[(shots_df["gk_name"] == gk_name) &
                      (~shots_df["outcome"].isin(["Saved", "Goal"]))]
    pitch, ax = pitch_ax(fig, pos, f"Saves (●) vs Shots Faced (·)")
    if not others.empty:
        pitch.scatter(others["shot_x"], others["shot_y"], s=18, c="#888888",
                      marker=".", alpha=0.5, ax=ax, zorder=3)
    if not saved.empty:
        pitch.scatter(saved["shot_x"], saved["shot_y"], s=55, c=CYAN, marker="o",
                      edgecolors="white", linewidths=0.4, alpha=0.85, ax=ax, zorder=5)
    if not goals.empty:
        pitch.scatter(goals["shot_x"], goals["shot_y"], s=80, c=RED, marker="*",
                      edgecolors="white", linewidths=0.4, alpha=0.9, ax=ax, zorder=6)


def panel_punches(fig, pos, gk_name, events_df):
    punches = events_df[(events_df["player_name"] == gk_name) &
                        (events_df["gk_action"] == "Punch")]
    n = 0
    pitch, ax = pitch_ax(fig, pos)
    for _, row in punches.iterrows():
        loc = parse_loc(row["location"])
        if loc:
            ax.plot(loc[0], loc[1], "*", color=CYAN, ms=11, mec="white",
                    mew=0.3, alpha=0.85, zorder=5)
            n += 1
    ax.set_title(f"Punches (★)  n={n}", fontsize=9, color=GRAY, pad=6)


def panel_kicks(fig, pos, gk_name, kicks_df, long=True, threshold=32):
    gk_kicks = kicks_df[kicks_df["player_name"] == gk_name].copy()
    gk_kicks["pl"] = pd.to_numeric(gk_kicks["pass_length"], errors="coerce").fillna(0)
    subset = gk_kicks[gk_kicks["pl"] >= threshold] if long else gk_kicks[gk_kicks["pl"] < threshold]
    color = CYAN if long else LIME
    tag = f"Long Kicks / Goal Kicks (≥{threshold}m)" if long else f"Short Distribution (<{threshold}m)"
    pitch, ax = pitch_ax(fig, pos)
    n = 0
    for _, row in subset.iterrows():
        s = parse_loc(row["location"])
        e = parse_loc(row["pass_end_location"])
        if s and e:
            ax.annotate("", xy=(e[0], e[1]), xytext=(s[0], s[1]),
                        arrowprops=dict(arrowstyle="-", color=color, alpha=0.45, lw=0.8))
            ax.plot(e[0], e[1], "o", color=color, ms=2.5, alpha=0.65)
            n += 1
    ax.set_title(f"{tag}  n={n}", fontsize=9, color=GRAY, pad=6)


def panel_radar(fig, pos, gk_name, gk_stats):
    row = gk_stats[gk_stats["gk_name"] == gk_name]
    if row.empty:
        return
    row = row.iloc[0]

    metrics = {
        "save_pct": ("Save %", True),
        "saves": ("Saves", True),
        "shots_faced": ("Shots\nFaced", True),
        "goals_conceded": ("vs Goals\nConceded", False),
        "punches": ("Punches", True),
        "sweeper_actions": ("Sweeper", True),
        "goal_kicks": ("Long\nKicks", True),
    }

    vals_raw = []
    labels = []
    for col, (lbl, higher_better) in metrics.items():
        mean = gk_stats[col].mean()
        std = gk_stats[col].std()
        if std == 0:
            z = 0.0
        else:
            z = (row[col] - mean) / std
            if not higher_better:
                z = -z
        vals_raw.append(z)
        labels.append(lbl)

    norm = [(v + 3) / 6 for v in vals_raw]
    norm = [max(0.02, min(0.98, v)) for v in norm]

    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    norm += norm[:1]
    angles += angles[:1]

    ax = fig.add_subplot(pos, polar=True)
    ax.set_facecolor(BG)

    for r_val in [0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.plot(angles, [r_val] * (N + 1), color="#cccccc", lw=0.5)

    for z_ref, tag in [(-2, "-2σ"), (-1, "-1σ"), (1, "+1σ"), (2, "+2σ")]:
        r_ref = (z_ref + 3) / 6
        circle = [r_ref] * (N + 1)
        ax.plot(angles, circle, color="#bbbbbb", lw=0.3, ls="--")
        ax.text(angles[0], r_ref + 0.03, tag, fontsize=5.5, color="#999999", ha="center")

    ax.plot(angles, norm, "o-", lw=2, ms=4.5, color=CYAN)
    ax.fill(angles, norm, alpha=0.18, color=CYAN)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=GRAY, fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.spines["polar"].set_color("#cccccc")
    ax.grid(False)
    ax.set_title("Z-Score Profile", fontsize=10, color=GRAY, pad=18)


def generate_dashboard(gk_name, rank_num, gk, shots, events, kicks, gk_rank):
    row = gk[gk["gk_name"] == gk_name]
    if row.empty:
        print(f"  Skipping {gk_name} — no stats")
        return
    row = row.iloc[0]

    rank_row = gk_rank[gk_rank["gk_name"] == gk_name]
    comp = rank_row.iloc[0]["composite_score"] if not rank_row.empty else 0.0

    gk_kicks_all = kicks[kicks["player_name"] == gk_name].copy()
    gk_kicks_all["pl"] = pd.to_numeric(gk_kicks_all["pass_length"], errors="coerce").fillna(0)
    long_n = int((gk_kicks_all["pl"] >= 32).sum())

    fig = plt.figure(figsize=(19, 14), facecolor=BG)

    fig.text(0.5, 0.975,
             f"\U0001F9E4  {gk_name}  —  UEFA Euro 2024  |  Individual GK Dashboard",
             ha="center", va="top", fontsize=17, fontweight="bold", color=TEXT)
    fig.text(0.025, 0.975, f"#{rank_num}", ha="left", va="top",
             fontsize=24, fontweight="bold", color=CYAN)

    cw, ch = 0.105, 0.085
    gap = 0.008
    sx = 0.05
    cy = 0.865
    cards = [
        (str(int(row["matches_played"])), "Matches"),
        (str(int(row["shots_faced"])), "Shots Faced"),
        (str(int(row["saves"])), "Saves"),
        (f"{row['save_pct']:.1f}%", "Save %"),
        (str(int(row["goals_conceded"])), "Goals\nConceded"),
        (str(int(row["punches"])), "Punches"),
        (str(long_n), "Long\nKicks"),
        (f"{comp:.3f}", "Composite\nZ-Score"),
    ]
    for i, (val, lbl) in enumerate(cards):
        draw_card(fig, sx + i * (cw + gap), cy, cw, ch, val, lbl)

    gs = GridSpec(2, 3, figure=fig,
                  left=0.03, right=0.97, top=0.83, bottom=0.02,
                  wspace=0.12, hspace=0.18)

    panel_saves(fig, gs[0, 0], gk_name, shots)
    panel_punches(fig, gs[0, 1], gk_name, events)
    panel_kicks(fig, gs[0, 2], gk_name, kicks, long=True)
    panel_kicks(fig, gs[1, 0], gk_name, kicks, long=False)

    ax_blank = fig.add_subplot(gs[1, 1])
    ax_blank.set_facecolor(BG)
    ax_blank.axis("off")

    panel_radar(fig, gs[1, 2], gk_name, gk)

    fname = CHARTS_DIR / f"dashboard_{rank_num:02d}_{gk_name.replace(' ', '_')}.png"
    plt.savefig(fname, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  Saved: {fname}")


def main():
    print("Loading data...")
    gk, shots, events, kicks, gk_rank = load_data()

    top = gk_rank.head(3)
    print(f"Generating dashboards for top 3 goalkeepers...\n")

    for i, (_, r) in enumerate(top.iterrows(), 1):
        name = r["gk_name"]
        print(f"  #{i} {name}")
        generate_dashboard(name, i, gk, shots, events, kicks, gk_rank)

    print(f"\nAll dashboards saved to: {CHARTS_DIR}")


if __name__ == "__main__":
    main()
