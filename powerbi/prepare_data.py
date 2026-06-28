"""
Prepare Power BI-ready data files from processed CSVs.
Reads: data/processed/ + data/final/ → Writes: powerbi/data/

Tables generated:
  1. gk_performance.csv      — Main GK stats & rankings
  2. zscore_metrics.csv       — Unpivoted z-scores (for matrix heatmap)
  3. shots_detail.csv         — Shot-level data (for shot maps)
  4. scoring_weights.csv      — Composite score weights
  5. gk_passes_detail.csv     — Every GK pass with long/short flag + coords
  6. gk_actions_detail.csv    — Every GK action (save/punch/claim/sweeper) with coords
  7. long_short_kings.csv     — Per-GK long & short ball summary
  8. gk_pass_heatmap.csv      — Binned pass destination zones per GK
  9. gk_shot_heatmap.csv      — Binned shot origin zones per GK
"""
import pandas as pd
import numpy as np
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
FINAL_DIR = ROOT / "data" / "final"
PBI_DIR = ROOT / "powerbi" / "data"
PBI_DIR.mkdir(parents=True, exist_ok=True)

LONG_THRESHOLD = 32  # metres — UEFA standard

Z_LABELS = {
    "z_save_pct": "Save %",
    "z_goals_prevented": "Goals Prevented",
    "z_sweeper_per_match": "Sweeper/Match",
    "z_claims_per_match": "Claims/Match",
    "z_goals_conceded": "Goals Conceded (inv.)",
    "z_gp_per_match": "Goals Prev./Match",
    "z_xg_faced": "xG Faced (inv.)",
}

WEIGHTS = {
    "z_goals_prevented": 0.35,
    "z_save_pct": 0.30,
    "z_sweeper_per_match": 0.15,
    "z_claims_per_match": 0.10,
    "z_goals_conceded": 0.10,
}


def safe_parse_location(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val.startswith("["):
        try:
            return ast.literal_eval(val)
        except Exception:
            return [None, None]
    return [None, None]


# ─────────────────────────────────────────────────────────────
# 1. GK Performance (existing)
# ─────────────────────────────────────────────────────────────
def build_gk_performance():
    gk_clean = pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")
    gk_rank = pd.read_csv(FINAL_DIR / "gk_rank.csv")

    z_cols = [c for c in gk_rank.columns if c.startswith("z_")]
    rank_merge = gk_rank[["gk_name", "composite_score"] + z_cols].copy()

    gk = gk_clean.merge(rank_merge, on="gk_name", how="left")
    gk["composite_score"] = gk["composite_score"].fillna(0)
    gk = gk.sort_values("composite_score", ascending=False).reset_index(drop=True)
    gk.insert(0, "rank", range(1, len(gk) + 1))

    for c in ["save_pct", "goals_prevented", "xg_faced", "sweeper_per_match",
              "claims_per_match", "punches_per_match", "goal_kicks_per_match",
              "gp_per_match", "xg_per_match"]:
        if c in gk.columns:
            gk[c] = gk[c].round(2)
    if "avg_gk_length" in gk.columns:
        gk["avg_gk_length"] = gk["avg_gk_length"].round(1)
    gk["composite_score"] = gk["composite_score"].round(4)
    for c in z_cols:
        if c in gk.columns:
            gk[c] = gk[c].round(4)

    col_order = [
        "rank", "gk_name", "matches_played",
        "shots_faced", "shots_on_target", "saves", "blocked_shots", "save_pct",
        "xg_faced", "goals_conceded", "goals_prevented",
        "sweeper_actions", "claims", "punches", "total_gk_events",
        "goal_kicks", "avg_gk_length",
        "sweeper_per_match", "claims_per_match", "punches_per_match",
        "goal_kicks_per_match", "gp_per_match", "xg_per_match",
        "composite_score",
    ] + z_cols
    col_order = [c for c in col_order if c in gk.columns]
    gk = gk[col_order]

    gk.to_csv(PBI_DIR / "gk_performance.csv", index=False)
    print(f"  gk_performance.csv ({len(gk)} rows, {len(gk.columns)} cols)")
    return gk


# ─────────────────────────────────────────────────────────────
# 2. Z-Score long format (existing)
# ─────────────────────────────────────────────────────────────
def build_zscore_long(gk):
    rows = []
    for _, row in gk.iterrows():
        for z_col, label in Z_LABELS.items():
            if z_col in row.index:
                rows.append({
                    "gk_name": row["gk_name"],
                    "rank": int(row["rank"]),
                    "metric": label,
                    "z_score": round(row[z_col], 4),
                    "weight": WEIGHTS.get(z_col, 0.0),
                })
    df = pd.DataFrame(rows)
    df.to_csv(PBI_DIR / "zscore_metrics.csv", index=False)
    print(f"  zscore_metrics.csv ({len(df)} rows)")


# ─────────────────────────────────────────────────────────────
# 3. Shots detail (existing — enhanced)
# ─────────────────────────────────────────────────────────────
def build_shots_detail():
    shots = pd.read_csv(PROC_DIR / "shots_faced.csv", low_memory=False)

    keep_cols = {
        "match_id": "match_id",
        "player_name": "shooter",
        "team_name": "shooting_team",
        "gk_name": "goalkeeper",
        "xg": "xg",
        "outcome": "outcome",
        "shot_x": "shot_x",
        "shot_y": "shot_y",
        "minute": "minute",
        "period": "period",
    }
    available = {k: v for k, v in keep_cols.items() if k in shots.columns}
    detail = shots[list(available.keys())].rename(columns=available).copy()

    detail["xg"] = pd.to_numeric(detail["xg"], errors="coerce").fillna(0).round(4)
    detail["shot_x"] = pd.to_numeric(detail["shot_x"], errors="coerce")
    detail["shot_y"] = pd.to_numeric(detail["shot_y"], errors="coerce")

    detail["is_goal"] = (detail["outcome"] == "Goal").astype(int)
    detail["is_save"] = (detail["outcome"] == "Saved").astype(int)
    detail["is_on_target"] = detail["outcome"].isin(["Goal", "Saved"]).astype(int)

    # Danger zone classification
    detail["distance_to_goal"] = np.sqrt((120 - detail["shot_x"])**2 + (40 - detail["shot_y"])**2)
    detail["danger_zone"] = pd.cut(
        detail["distance_to_goal"],
        bins=[0, 10, 18, 25, 999],
        labels=["6-yard box", "Penalty area close", "Penalty area edge", "Outside box"],
    )

    detail.to_csv(PBI_DIR / "shots_detail.csv", index=False)
    print(f"  shots_detail.csv ({len(detail)} rows)")


# ─────────────────────────────────────────────────────────────
# 4. Scoring weights (existing)
# ─────────────────────────────────────────────────────────────
def build_weight_table():
    rows = []
    for z_col, weight in WEIGHTS.items():
        label = Z_LABELS.get(z_col, z_col.replace("z_", "").replace("_", " ").title())
        rows.append({
            "z_column": z_col,
            "metric": label,
            "weight": weight,
            "weight_pct": f"{weight * 100:.0f}%",
        })
    df = pd.DataFrame(rows)
    df.to_csv(PBI_DIR / "scoring_weights.csv", index=False)
    print(f"  scoring_weights.csv ({len(df)} rows)")


# ─────────────────────────────────────────────────────────────
# 5. GK Passes Detail (NEW — for individual player pass analysis)
# ─────────────────────────────────────────────────────────────
def build_gk_passes_detail():
    goal_kicks_df = pd.read_csv(PROC_DIR / "goal_kicks.csv", low_memory=False)
    gk_events_df = pd.read_csv(PROC_DIR / "gk_events.csv", low_memory=False)

    gk_names = set(gk_events_df["player_name"].dropna().unique())

    all_passes = goal_kicks_df.copy()

    rows = []
    for _, row in all_passes.iterrows():
        loc = safe_parse_location(row.get("location", None))
        end_loc_raw = row.get("pass_end_location", None)
        end_loc = safe_parse_location(end_loc_raw)

        length = pd.to_numeric(row.get("pass_length", 0), errors="coerce")
        if pd.isna(length):
            length = 0

        outcome = str(row.get("pass_outcome", ""))
        is_complete = 1 if outcome in ("", "nan", "Complete") else 0

        rows.append({
            "gk_name": row.get("player_name", ""),
            "team": row.get("team_name", ""),
            "match_id": row.get("match_id", ""),
            "minute": row.get("minute", ""),
            "period": row.get("period", ""),
            "pass_type": "Goal Kick",
            "pass_length": round(length, 1),
            "is_long": 1 if length >= LONG_THRESHOLD else 0,
            "is_short": 1 if length < LONG_THRESHOLD else 0,
            "is_complete": is_complete,
            "pass_outcome": outcome if outcome not in ("", "nan") else "Complete",
            "start_x": loc[0] if len(loc) > 0 else None,
            "start_y": loc[1] if len(loc) > 1 else None,
            "end_x": end_loc[0] if len(end_loc) > 0 else None,
            "end_y": end_loc[1] if len(end_loc) > 1 else None,
            "pass_height": row.get("pass_height", row.get("pass_height_name", "")),
            "pass_body_part": row.get("pass_body_part", row.get("pass_body_part_name", "")),
        })

    df = pd.DataFrame(rows)
    df = df[df["gk_name"].isin(gk_names)].copy()

    for col in ["start_x", "start_y", "end_x", "end_y", "pass_length"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.to_csv(PBI_DIR / "gk_passes_detail.csv", index=False)
    print(f"  gk_passes_detail.csv ({len(df)} rows)")
    return df


# ─────────────────────────────────────────────────────────────
# 6. GK Actions Detail (NEW — saves, punches, claims, sweeper)
# ─────────────────────────────────────────────────────────────
def build_gk_actions_detail():
    gk_ev = pd.read_csv(PROC_DIR / "gk_events.csv", low_memory=False)

    rows = []
    for _, row in gk_ev.iterrows():
        loc = safe_parse_location(row.get("location", None))
        action = str(row.get("gk_action", ""))
        outcome = str(row.get("gk_outcome", ""))

        action_category = "Other"
        if "Save" in action or "Shot Faced" in action:
            action_category = "Save"
        elif "Punch" in action:
            action_category = "Punch"
        elif "Claim" in action:
            action_category = "Claim"
        elif "Sweeper" in action or "Keeper Sweeper" in action:
            action_category = "Sweeper"
        elif "Smother" in action:
            action_category = "Smother"

        rows.append({
            "gk_name": row.get("player_name", ""),
            "team": row.get("team_name", ""),
            "match_id": row.get("match_id", ""),
            "minute": row.get("minute", ""),
            "period": row.get("period", ""),
            "action_type": action,
            "action_category": action_category,
            "action_outcome": outcome if outcome not in ("", "nan") else "",
            "action_x": loc[0] if len(loc) > 0 else None,
            "action_y": loc[1] if len(loc) > 1 else None,
            "body_part": row.get("goalkeeper_body_part", ""),
            "technique": row.get("goalkeeper_technique", ""),
        })

    df = pd.DataFrame(rows)
    for col in ["action_x", "action_y"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.to_csv(PBI_DIR / "gk_actions_detail.csv", index=False)
    print(f"  gk_actions_detail.csv ({len(df)} rows)")
    return df


# ─────────────────────────────────────────────────────────────
# 7. Long & Short Ball Kings (NEW — summary per GK)
# ─────────────────────────────────────────────────────────────
def build_long_short_kings(gk_passes_df, gk_perf):
    if gk_passes_df is None or len(gk_passes_df) == 0:
        print("  long_short_kings.csv — SKIPPED (no pass data)")
        return

    mp_map = dict(zip(gk_perf["gk_name"], gk_perf["matches_played"]))

    stats = gk_passes_df.groupby("gk_name").agg(
        total_passes=("pass_length", "count"),
        long_balls=("is_long", "sum"),
        short_balls=("is_short", "sum"),
        long_complete=("is_long", lambda x: ((gk_passes_df.loc[x.index, "is_long"] == 1) & (gk_passes_df.loc[x.index, "is_complete"] == 1)).sum()),
        short_complete=("is_short", lambda x: ((gk_passes_df.loc[x.index, "is_short"] == 1) & (gk_passes_df.loc[x.index, "is_complete"] == 1)).sum()),
        avg_pass_length=("pass_length", "mean"),
        avg_long_length=("pass_length", lambda x: gk_passes_df.loc[x.index[gk_passes_df.loc[x.index, "is_long"] == 1], "pass_length"].mean()),
        avg_short_length=("pass_length", lambda x: gk_passes_df.loc[x.index[gk_passes_df.loc[x.index, "is_short"] == 1], "pass_length"].mean()),
    ).reset_index()

    stats["matches_played"] = stats["gk_name"].map(mp_map).fillna(1)
    mp = stats["matches_played"].replace(0, 1)

    stats["long_per_match"] = (stats["long_balls"] / mp).round(2)
    stats["short_per_match"] = (stats["short_balls"] / mp).round(2)
    stats["long_accuracy"] = (stats["long_complete"] / stats["long_balls"].replace(0, 1) * 100).round(1)
    stats["short_accuracy"] = (stats["short_complete"] / stats["short_balls"].replace(0, 1) * 100).round(1)
    stats["long_pct"] = (stats["long_balls"] / stats["total_passes"].replace(0, 1) * 100).round(1)
    stats["short_pct"] = (stats["short_balls"] / stats["total_passes"].replace(0, 1) * 100).round(1)
    stats["avg_pass_length"] = stats["avg_pass_length"].round(1)
    stats["avg_long_length"] = stats["avg_long_length"].round(1)
    stats["avg_short_length"] = stats["avg_short_length"].round(1)

    # Rank by long/short volume per match
    stats["long_ball_rank"] = stats["long_per_match"].rank(ascending=False, method="min").astype(int)
    stats["short_ball_rank"] = stats["short_per_match"].rank(ascending=False, method="min").astype(int)

    stats = stats.sort_values("long_per_match", ascending=False).reset_index(drop=True)
    stats.to_csv(PBI_DIR / "long_short_kings.csv", index=False)
    print(f"  long_short_kings.csv ({len(stats)} rows)")


# ─────────────────────────────────────────────────────────────
# 8. Pass Destination Heatmap bins (NEW — for Power BI matrix)
# ─────────────────────────────────────────────────────────────
def build_pass_heatmap(gk_passes_df):
    if gk_passes_df is None or len(gk_passes_df) == 0:
        print("  gk_pass_heatmap.csv — SKIPPED (no pass data)")
        return

    df = gk_passes_df.dropna(subset=["end_x", "end_y"]).copy()

    # Bin into pitch zones: 12 cols x 8 rows on StatsBomb 120x80 pitch
    df["zone_x"] = pd.cut(df["end_x"], bins=np.linspace(0, 120, 13), labels=range(1, 13), include_lowest=True)
    df["zone_y"] = pd.cut(df["end_y"], bins=np.linspace(0, 80, 9), labels=range(1, 9), include_lowest=True)

    # Named zones for readability
    def zone_label(zx, zy):
        x_labels = {1: "Own 6yd", 2: "Own Box", 3: "Own Def 3rd", 4: "Own Def 3rd",
                    5: "Own Mid 3rd", 6: "Own Mid 3rd", 7: "Opp Mid 3rd", 8: "Opp Mid 3rd",
                    9: "Opp Att 3rd", 10: "Opp Att 3rd", 11: "Opp Box", 12: "Opp 6yd"}
        y_labels = {1: "Left", 2: "Left", 3: "Left-Center", 4: "Center",
                    5: "Center", 6: "Right-Center", 7: "Right", 8: "Right"}
        return f"{x_labels.get(zx, '?')} {y_labels.get(zy, '?')}"

    hm = df.groupby(["gk_name", "zone_x", "zone_y"]).agg(
        pass_count=("pass_length", "count"),
        avg_length=("pass_length", "mean"),
        complete_count=("is_complete", "sum"),
    ).reset_index()

    hm["zone_x"] = hm["zone_x"].astype(int)
    hm["zone_y"] = hm["zone_y"].astype(int)
    hm["avg_length"] = hm["avg_length"].round(1)
    hm["zone_label"] = hm.apply(lambda r: zone_label(r["zone_x"], r["zone_y"]), axis=1)
    hm["accuracy"] = (hm["complete_count"] / hm["pass_count"].replace(0, 1) * 100).round(1)

    hm.to_csv(PBI_DIR / "gk_pass_heatmap.csv", index=False)
    print(f"  gk_pass_heatmap.csv ({len(hm)} rows)")


# ─────────────────────────────────────────────────────────────
# 9. Shot Origin Heatmap bins (NEW — for Power BI matrix)
# ─────────────────────────────────────────────────────────────
def build_shot_heatmap():
    shots = pd.read_csv(PROC_DIR / "shots_faced.csv", low_memory=False)
    shots["shot_x"] = pd.to_numeric(shots.get("shot_x"), errors="coerce")
    shots["shot_y"] = pd.to_numeric(shots.get("shot_y"), errors="coerce")
    shots = shots.dropna(subset=["shot_x", "shot_y", "gk_name"]).copy()

    shots["zone_x"] = pd.cut(shots["shot_x"], bins=np.linspace(60, 120, 7), labels=range(1, 7), include_lowest=True)
    shots["zone_y"] = pd.cut(shots["shot_y"], bins=np.linspace(0, 80, 6), labels=range(1, 6), include_lowest=True)

    shots["xg"] = pd.to_numeric(shots["xg"], errors="coerce").fillna(0)
    shots["is_goal"] = (shots["outcome"] == "Goal").astype(int)
    shots["is_save"] = (shots["outcome"] == "Saved").astype(int)

    hm = shots.groupby(["gk_name", "zone_x", "zone_y"]).agg(
        shot_count=("xg", "count"),
        total_xg=("xg", "sum"),
        avg_xg=("xg", "mean"),
        goals=("is_goal", "sum"),
        saves=("is_save", "sum"),
    ).reset_index()

    hm["zone_x"] = hm["zone_x"].astype(int)
    hm["zone_y"] = hm["zone_y"].astype(int)
    hm["total_xg"] = hm["total_xg"].round(3)
    hm["avg_xg"] = hm["avg_xg"].round(3)

    def shot_zone_label(zx):
        labels = {1: "Long Range", 2: "Edge of Box", 3: "Penalty Area",
                  4: "Central Box", 5: "Close Range", 6: "6-Yard Box"}
        return labels.get(zx, "?")

    hm["zone_label"] = hm["zone_x"].apply(shot_zone_label)

    hm.to_csv(PBI_DIR / "gk_shot_heatmap.csv", index=False)
    print(f"  gk_shot_heatmap.csv ({len(hm)} rows)")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Preparing Power BI data files...")
    print("=" * 60)

    gk = build_gk_performance()
    build_zscore_long(gk)
    build_shots_detail()
    build_weight_table()
    gk_passes_df = build_gk_passes_detail()
    build_gk_actions_detail()
    build_long_short_kings(gk_passes_df, gk)
    build_pass_heatmap(gk_passes_df)
    build_shot_heatmap()

    print("\n" + "=" * 60)
    print(f"All Power BI files saved to: {PBI_DIR}")
    print("=" * 60)
    print("\nImport these CSVs into Power BI Desktop:")
    print("  1. gk_performance.csv       — Main goalkeeper stats & rankings")
    print("  2. zscore_metrics.csv        — Unpivoted z-scores (for heatmap)")
    print("  3. shots_detail.csv          — Shot-level data (for shot maps)")
    print("  4. scoring_weights.csv       — Composite score weights")
    print("  5. gk_passes_detail.csv      — Every GK pass with long/short flag")
    print("  6. gk_actions_detail.csv     — Every GK action (save/punch/claim/sweeper)")
    print("  7. long_short_kings.csv      — Long & short ball summary per GK")
    print("  8. gk_pass_heatmap.csv       — Pass destination zones (for heatmap)")
    print("  9. gk_shot_heatmap.csv       — Shot origin zones (for heatmap)")


if __name__ == "__main__":
    main()
