"""
Step 10: Angle-adjusted goalkeeper positioning -- goal-mouth coverage per shot.
Reads: data/final/gk_360_positioning.csv, data/final/gk_360_positioning_summary.csv (must run after Step 9)
Writes: data/final/gk_360_positioning.csv, data/final/gk_360_positioning_summary.csv (adds columns in place)

Raw distance-off-line (Step 9) treats a keeper standing 3 yards off-line
dead-center the same as one standing 3 yards off-line but badly angled.
This models the keeper's body as a BODY_WIDTH-yard-wide block and projects
it from the shot location onto the goal line, measuring what fraction of
the 8-yard goal mouth it actually shadows -- capturing both depth and
lateral centering relative to the real shot angle.

This step augments Step 9's output with new columns rather than writing a
separate file: gk_360_positioning.csv already has match_id/shot_x/shot_y/
gk_x/gk_y/dist_off_line/etc, and a second file duplicating those columns
just to add 3 more (goal_coverage_pct, open_goal_pct, shot_angle_deg)
would mean two files to keep in sync for the same 1251 shots.
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
FINAL_DIR = ROOT / "data" / "final"

POST1_Y, POST2_Y = 36.0, 44.0  # goal mouth, 8 yards wide, centered on y=40
GOAL_X = 120.0
BODY_WIDTH = 2.0  # yards -- approximate standing goalkeeper blocking width


def goal_mouth_coverage(sx, sy, kx, ky, body_width=BODY_WIDTH):
    """Fraction of the goal mouth (as seen from the shot location) blocked by the
    keeper's body, modeled as a segment of `body_width` centered on the keeper,
    projected forward onto the goal line."""
    if kx <= sx:
        return 0.0  # keeper not between shooter and goal -> blocks nothing in this model
    edge_lo, edge_hi = ky - body_width / 2, ky + body_width / 2
    t = (GOAL_X - sx) / (kx - sx)
    y_lo = sy + t * (edge_lo - sy)
    y_hi = sy + t * (edge_hi - sy)
    shadow_lo, shadow_hi = min(y_lo, y_hi), max(y_lo, y_hi)
    overlap = max(0.0, min(shadow_hi, POST2_Y) - max(shadow_lo, POST1_Y))
    return overlap / (POST2_Y - POST1_Y)


def total_shot_angle(sx, sy):
    """Angle (degrees) subtended by the goal mouth as seen from the shot location --
    raw shot difficulty/openness, independent of the keeper."""
    v1 = np.array([GOAL_X - sx, POST1_Y - sy])
    v2 = np.array([GOAL_X - sx, POST2_Y - sy])
    cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cos_theta = np.clip(cos_theta, -1, 1)
    return np.degrees(np.arccos(cos_theta))


def main():
    positioning_path = FINAL_DIR / "gk_360_positioning.csv"
    summary_path = FINAL_DIR / "gk_360_positioning_summary.csv"

    df = pd.read_csv(positioning_path)
    print(f"Loaded {len(df)} shots from {positioning_path.name}")

    df["goal_coverage_pct"] = df.apply(
        lambda r: goal_mouth_coverage(r["shot_x"], r["shot_y"], r["gk_x"], r["gk_y"]), axis=1
    ).round(4)
    df["open_goal_pct"] = (1 - df["goal_coverage_pct"]).round(4)
    df["shot_angle_deg"] = df.apply(lambda r: total_shot_angle(r["shot_x"], r["shot_y"]), axis=1).round(2)

    df.to_csv(positioning_path, index=False, encoding="utf-8")
    print(f"Updated: {positioning_path} (+goal_coverage_pct, +open_goal_pct, +shot_angle_deg)")

    coverage_summary = df.groupby("gk_name").agg(
        avg_goal_coverage_pct=("goal_coverage_pct", "mean"),
        avg_open_goal_pct=("open_goal_pct", "mean"),
        avg_shot_angle_deg=("shot_angle_deg", "mean"),
    ).round({"avg_goal_coverage_pct": 4, "avg_open_goal_pct": 4, "avg_shot_angle_deg": 2}).reset_index()

    summary = pd.read_csv(summary_path).merge(coverage_summary, on="gk_name", how="left")
    summary.to_csv(summary_path, index=False, encoding="utf-8")
    print(f"Updated: {summary_path} (+avg_goal_coverage_pct, +avg_open_goal_pct, +avg_shot_angle_deg)")

    print(f"\nMean goal_coverage_pct: {df['goal_coverage_pct'].mean():.1%}")
    print("Done!")


if __name__ == "__main__":
    main()
