"""
Fetch Euro 2024 GK data from StatsBomb, clean it, and save CSVs.
Reads: StatsBomb API → Writes: data/raw/ and data/processed/
"""
import sys
import pandas as pd
import numpy as np
from statsbombpy import sb
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"

COMPETITION_ID = 55
SEASON_ID = 282
MIN_MATCHES = 2


def safe_get(val, *keys, default=""):
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, default)
        else:
            return default
    return val


def flatten(series, *keys):
    return series.apply(lambda x: safe_get(x, *keys))


def load_events():
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    print(f"Euro 2024: {len(matches)} matches loaded")

    all_events = []
    for i, mid in enumerate(matches["match_id"]):
        try:
            ev = sb.events(match_id=mid)
            ev["match_id"] = mid
            all_events.append(ev)
        except Exception as e:
            print(f"  Failed match {mid}: {e}")
        if (i + 1) % 10 == 0 or (i + 1) == len(matches):
            print(f"  {i+1}/{len(matches)} loaded...")

    events = pd.concat(all_events, ignore_index=True)
    print(f"Total events: {len(events):,}")
    return events


def normalize_columns(events):
    sample = events["type"].iloc[0] if "type" in events.columns else None
    is_nested = isinstance(sample, dict)

    if is_nested:
        events["type_name"] = flatten(events["type"], "name")
        events["player_name"] = flatten(events["player"], "name")
        events["player_id"] = flatten(events["player"], "id")
        events["team_name"] = flatten(events["team"], "name")
        pos_col = events["position"] if "position" in events.columns else pd.Series([{}] * len(events))
        events["position_name"] = flatten(pos_col, "name")
    else:
        rename = {"type": "type_name", "player": "player_name", "team": "team_name", "position": "position_name"}
        for old, new in rename.items():
            if old in events.columns and new not in events.columns:
                events[new] = events[old]

    return events, is_nested


def build_match_gk_map(events):
    """Map each (match_id, team) to the goalkeeper's name using position data."""
    gk_rows = events[events["position_name"] == "Goalkeeper"][["match_id", "team_name", "player_name"]].drop_duplicates()
    gk_map = {}
    for _, row in gk_rows.iterrows():
        gk_map[(row["match_id"], row["team_name"])] = row["player_name"]
    return gk_map


def get_match_teams(events):
    """Get the two teams per match."""
    return events.groupby("match_id")["team_name"].unique()


def extract_shots(events, is_nested):
    shots_raw = events[events["type_name"] == "Shot"].copy()

    if is_nested:
        shots_raw["xg"] = shots_raw["shot"].apply(lambda x: safe_get(x, "statsbomb_xg", default=0) if isinstance(x, dict) else 0)
        shots_raw["outcome"] = shots_raw["shot"].apply(lambda x: safe_get(x, "outcome", "name"))
        shots_raw["gk_name"] = shots_raw["shot"].apply(lambda x: safe_get(x, "goalkeeper", "name"))
        shots_raw["gk_id"] = shots_raw["shot"].apply(lambda x: safe_get(x, "goalkeeper", "id", default=None))
        shots_raw["body_part"] = shots_raw["shot"].apply(lambda x: safe_get(x, "body_part", "name"))
        shots_raw["technique"] = shots_raw["shot"].apply(lambda x: safe_get(x, "technique", "name"))
        shots_raw["shot_x"] = shots_raw["location"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
        shots_raw["shot_y"] = shots_raw["location"].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else None)
    else:
        xg_col = next((c for c in shots_raw.columns if "statsbomb_xg" in c), None)
        outcome_col = next((c for c in shots_raw.columns if c == "shot_outcome"), None)

        if xg_col:
            shots_raw["xg"] = shots_raw[xg_col]
        if outcome_col:
            shots_raw["outcome"] = shots_raw[outcome_col]

        if "location" in shots_raw.columns:
            shots_raw["shot_x"] = shots_raw["location"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
            shots_raw["shot_y"] = shots_raw["location"].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else None)

        # In flat format, GK name is not on the shot row — derive from opposing team's GK
        gk_map = build_match_gk_map(events)
        match_teams = get_match_teams(events)

        def find_opposing_gk(row):
            teams = match_teams.get(row["match_id"], [])
            for t in teams:
                if t != row["team_name"]:
                    return gk_map.get((row["match_id"], t), "")
            return ""

        shots_raw["gk_name"] = shots_raw.apply(find_opposing_gk, axis=1)

    shots_raw["xg"] = pd.to_numeric(shots_raw.get("xg", 0), errors="coerce").fillna(0)
    shots = shots_raw[shots_raw["gk_name"].notna() & (shots_raw["gk_name"] != "")].copy()
    return shots


def extract_gk_events(events, is_nested):
    gk_ev = events[events["type_name"] == "Goal Keeper"].copy()

    if is_nested:
        gk_ev["gk_action"] = gk_ev["goalkeeper"].apply(lambda x: safe_get(x, "type", "name") if isinstance(x, dict) else "")
        gk_ev["gk_outcome"] = gk_ev["goalkeeper"].apply(lambda x: safe_get(x, "outcome", "name") if isinstance(x, dict) else "")
    else:
        gk_ev["gk_action"] = gk_ev["goalkeeper_type"] if "goalkeeper_type" in gk_ev.columns else ""
        gk_ev["gk_outcome"] = gk_ev["goalkeeper_outcome"] if "goalkeeper_outcome" in gk_ev.columns else ""

    return gk_ev


def extract_goal_kicks(events, is_nested):
    passes_all = events[events["type_name"] == "Pass"].copy()

    if is_nested:
        passes_all["pass_type"] = passes_all["pass"].apply(lambda x: safe_get(x, "type", "name") if isinstance(x, dict) else "")
        passes_all["pass_length"] = passes_all["pass"].apply(lambda x: safe_get(x, "length", default=0) if isinstance(x, dict) else 0)
    else:
        passes_all["pass_type"] = passes_all["pass_type"] if "pass_type" in passes_all.columns else ""
        passes_all["pass_length"] = pd.to_numeric(passes_all["pass_length"], errors="coerce").fillna(0) if "pass_length" in passes_all.columns else 0

    return passes_all[passes_all["pass_type"] == "Goal Kick"].copy()


def build_gk_table(shots, gk_ev, goal_kicks):
    gk_shots = shots.groupby("gk_name").agg(
        shots_faced=("xg", "count"),
        xg_faced=("xg", "sum"),
        goals_conceded=("outcome", lambda x: (x == "Goal").sum()),
        shots_on_target=("outcome", lambda x: x.isin(["Saved", "Goal"]).sum()),
        saves=("outcome", lambda x: (x == "Saved").sum()),
        blocked_shots=("outcome", lambda x: (x == "Blocked").sum()),
    ).reset_index()

    gk_shots["save_pct"] = (gk_shots["saves"] / gk_shots["shots_on_target"].replace(0, np.nan) * 100).fillna(0)
    gk_shots["goals_prevented"] = gk_shots["xg_faced"] - gk_shots["goals_conceded"]

    gk_actions = gk_ev.groupby("player_name").agg(
        sweeper_actions=("gk_action", lambda x: (x == "Keeper Sweeper").sum()),
        claims=("gk_action", lambda x: (x == "Collected").sum()),
        punches=("gk_action", lambda x: (x == "Punch").sum()),
        total_gk_events=("gk_action", "count"),
    ).reset_index().rename(columns={"player_name": "gk_name"})

    gk_gks = goal_kicks.groupby("player_name").agg(
        goal_kicks=("pass_type", "count"),
        avg_gk_length=("pass_length", "mean"),
    ).reset_index().rename(columns={"player_name": "gk_name"})

    gk_mp = gk_ev.groupby("player_name")["match_id"].nunique().reset_index()
    gk_mp.columns = ["gk_name", "matches_played"]

    gk = (
        gk_shots
        .merge(gk_actions, on="gk_name", how="left")
        .merge(gk_gks, on="gk_name", how="left")
        .merge(gk_mp, on="gk_name", how="left")
        .fillna(0)
    )

    mp = gk["matches_played"].replace(0, 1)
    gk["sweeper_per_match"] = gk["sweeper_actions"] / mp
    gk["claims_per_match"] = gk["claims"] / mp
    gk["punches_per_match"] = gk["punches"] / mp
    gk["goal_kicks_per_match"] = gk["goal_kicks"] / mp
    gk["gp_per_match"] = gk["goals_prevented"] / mp
    gk["xg_per_match"] = gk["xg_faced"] / mp

    gk = gk[gk["matches_played"] >= MIN_MATCHES].copy()
    return gk


def main():
    print("=" * 60)
    print("STEP 1: Loading events from StatsBomb...")
    events = load_events()

    print("\nSTEP 2: Normalizing columns...")
    events, is_nested = normalize_columns(events)

    print("\nSTEP 3: Extracting GK-related data...")
    shots = extract_shots(events, is_nested)
    gk_ev = extract_gk_events(events, is_nested)
    goal_kicks = extract_goal_kicks(events, is_nested)

    print(f"  Shots with GK info: {len(shots)}")
    print(f"  GK events: {len(gk_ev)}")
    print(f"  Goal kicks: {len(goal_kicks)}")

    # Save raw data
    raw_cols = ["match_id", "player_name", "team_name", "type_name", "gk_name", "xg", "outcome", "shot_x", "shot_y"]
    raw_save = shots[[c for c in raw_cols if c in shots.columns]]
    raw_save.to_csv(RAW_DIR / "euro2024_goalkeepers_raw.csv", index=False)
    print(f"\nSaved raw data: {RAW_DIR / 'euro2024_goalkeepers_raw.csv'}")

    print("\nSTEP 4: Building aggregated GK table...")
    gk = build_gk_table(shots, gk_ev, goal_kicks)
    print(f"  GKs with >= {MIN_MATCHES} matches: {len(gk)}")

    # Save processed
    gk.to_csv(PROC_DIR / "goalkeepers_clean.csv", index=False)
    print(f"Saved processed data: {PROC_DIR / 'goalkeepers_clean.csv'}")

    # Also save shots for individual analysis
    shots.to_csv(PROC_DIR / "shots_faced.csv", index=False)
    gk_ev.to_csv(PROC_DIR / "gk_events.csv", index=False)
    goal_kicks.to_csv(PROC_DIR / "goal_kicks.csv", index=False)
    print("Saved supporting CSVs (shots_faced, gk_events, goal_kicks)")

    print("\n" + "=" * 60)
    print("Data cleaning complete!")


if __name__ == "__main__":
    main()
