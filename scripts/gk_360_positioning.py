"""
Step 9: Goalkeeper 360 positioning -- distance off the line and lateral offset per shot.
Reads: StatsBomb API (event freeze frames, competition 55 / season 282), data/processed/goalkeepers_clean.csv
Writes: data/final/gk_360_positioning.csv, data/final/gk_360_positioning_summary.csv

For each shot, the defending keeper's position is taken from the shot's own
shot_freeze_frame, filtered to position == "Goalkeeper" and teammate == False
(i.e. an opponent of the shooter). Using the freeze_frame's teammate flag is
important: in rare situations (stoppage-time desperation, a keeper pushed up
for a corner) the shooting team's own keeper is also visible in frame, and a
naive "whichever keeper is tracked" lookup can pick the wrong one.

Shots are filtered to the same qualifying-keeper population (matches_played
>= 2) as the rest of data/final, so gk_name is joinable across every file
without silently dropping rows for backup keepers who played one match.
"""
import sys
import pandas as pd
from statsbombpy import sb
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
FINAL_DIR = ROOT / "data" / "final"

COMPETITION_ID = 55
SEASON_ID = 282
GOAL_LINE_X = 120
GOAL_CENTER_Y = 40
EXTREME_THRESHOLD = 8  # yards off line -> flagged as a desperation/build-up outlier, not dropped


def get_defending_keeper(freeze_frame):
    """Return (gk_name, gk_x, gk_y, own_keeper_advanced) for a shot's freeze frame,
    picking the DEFENDING team's keeper (teammate=False) over the shooting team's own."""
    if not isinstance(freeze_frame, list):
        return None, None, None, False
    gk_entries = [p for p in freeze_frame if p.get("position", {}).get("name") == "Goalkeeper"]
    defending = next((p for p in gk_entries if p.get("teammate") is False), None)
    own_advanced = any(p.get("teammate") is True for p in gk_entries)
    if defending is None:
        return None, None, None, own_advanced
    loc = defending.get("location")
    if not isinstance(loc, list) or len(loc) < 2:
        return None, None, None, own_advanced
    return defending.get("player", {}).get("name"), loc[0], loc[1], own_advanced


def build_shot_positioning(match_ids):
    all_rows = []
    for i, mid in enumerate(match_ids):
        events = sb.events(match_id=mid)
        shots = events[events["type"] == "Shot"].copy()
        if shots.empty or "shot_freeze_frame" not in shots.columns:
            continue

        shots["shot_x"] = shots["location"].apply(lambda l: l[0])
        shots["shot_y"] = shots["location"].apply(lambda l: l[1])
        shots["xg"] = shots.get("shot_statsbomb_xg")
        shots["outcome"] = shots.get("shot_outcome")

        gk_loc = shots["shot_freeze_frame"].apply(get_defending_keeper)
        shots["gk_name"] = gk_loc.apply(lambda t: t[0])
        shots["gk_x"] = gk_loc.apply(lambda t: t[1])
        shots["gk_y"] = gk_loc.apply(lambda t: t[2])
        shots["own_keeper_advanced"] = gk_loc.apply(lambda t: t[3])
        shots["match_id"] = mid

        matched = shots.dropna(subset=["gk_x", "gk_y"])
        all_rows.append(matched[["match_id", "player", "team", "gk_name", "outcome", "xg",
                                  "shot_x", "shot_y", "gk_x", "gk_y", "own_keeper_advanced"]])

        if (i + 1) % 10 == 0 or (i + 1) == len(match_ids):
            print(f"  {i + 1}/{len(match_ids)} matches processed...")

    df = pd.concat(all_rows, ignore_index=True)
    df["dist_off_line"] = GOAL_LINE_X - df["gk_x"]
    df["lateral_offset"] = df["gk_y"] - GOAL_CENTER_Y
    df["dist_to_shot"] = ((df["shot_x"] - df["gk_x"]) ** 2 + (df["shot_y"] - df["gk_y"]) ** 2) ** 0.5
    df["is_goal"] = (df["outcome"] == "Goal").astype(int)
    df["extreme_position"] = df["dist_off_line"] > EXTREME_THRESHOLD
    return df


def build_summary(df):
    summary = df.groupby("gk_name").agg(
        shots=("outcome", "count"),
        goals_conceded=("is_goal", "sum"),
        avg_dist_off_line=("dist_off_line", "mean"),
        avg_abs_lateral_offset=("lateral_offset", lambda x: x.abs().mean()),
        extreme_position_shots=("extreme_position", "sum"),
    ).reset_index()
    summary["avg_dist_off_line"] = summary["avg_dist_off_line"].round(2)
    summary["avg_abs_lateral_offset"] = summary["avg_abs_lateral_offset"].round(2)
    return summary.sort_values("avg_dist_off_line").reset_index(drop=True)


def main():
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    match_ids = matches["match_id"].tolist()
    print(f"Euro 2024: {len(match_ids)} matches")

    df = build_shot_positioning(match_ids)

    qualifying = set(pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")["gk_name"])
    n_before = len(df)
    df = df[df["gk_name"].isin(qualifying)].copy()
    print(f"\nFiltered to {len(qualifying)} qualifying keepers (matches_played >= 2): "
          f"{n_before} -> {len(df)} shots ({n_before - len(df)} dropped)")

    per_shot = df[["match_id", "player", "team", "gk_name", "outcome", "is_goal", "xg",
                   "shot_x", "shot_y", "gk_x", "gk_y", "dist_off_line", "lateral_offset",
                   "dist_to_shot", "extreme_position", "own_keeper_advanced"]].copy()
    for c in ["shot_x", "shot_y", "gk_x", "gk_y", "dist_off_line", "lateral_offset", "dist_to_shot"]:
        per_shot[c] = per_shot[c].round(2)
    per_shot = per_shot.sort_values(["match_id", "shot_x", "shot_y", "player"]).reset_index(drop=True)

    out_path = FINAL_DIR / "gk_360_positioning.csv"
    per_shot.to_csv(out_path, index=False, encoding="utf-8")
    print(f"\nSaved: {out_path} ({len(per_shot)} shots)")

    summary = build_summary(df)
    summary_path = FINAL_DIR / "gk_360_positioning_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8")
    print(f"Saved: {summary_path} ({len(summary)} goalkeepers)")

    print(f"\nExtreme-position shots (> {EXTREME_THRESHOLD} yards off line): {df['extreme_position'].sum()}")
    print(f"Shots where the attacking team's own keeper was also visible: {df['own_keeper_advanced'].sum()}")
    print("\nDone!")


if __name__ == "__main__":
    main()
