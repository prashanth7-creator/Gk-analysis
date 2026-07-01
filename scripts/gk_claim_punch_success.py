"""
Step 11: Claim/punch success-rate breakdown per goalkeeper.
Reads: data/processed/gk_events.csv, data/processed/goalkeepers_clean.csv
Writes: data/final/gk_claim_punch_success.csv

The pipeline only ever counted claim/punch actions (Step 1), never their
outcomes. gk_events.csv already carries a gk_outcome field per action;
this breaks Collected (claim) and Punch actions down by outcome instead
of just counting attempts.
"""
import sys
import pandas as pd
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
FINAL_DIR = ROOT / "data" / "final"


def claim_stats(events):
    claims = events[events["gk_action"] == "Collected"].copy()
    claims["success"] = claims["gk_outcome"].isin(["Success", "Collected Twice"])
    stats = claims.groupby("player_name").agg(
        claims_total=("success", "count"),
        claims_success=("success", "sum"),
    ).reset_index().rename(columns={"player_name": "gk_name"})
    stats["claim_success_rate"] = (stats["claims_success"] / stats["claims_total"]).round(4)
    return stats


def punch_stats(events):
    punches = events[events["gk_action"] == "Punch"].copy()
    punches["safe"] = punches["gk_outcome"] == "In Play Safe"
    punches["contact"] = punches["gk_outcome"].isin(["In Play Safe", "In Play Danger"])
    stats = punches.groupby("player_name").agg(
        punches_total=("gk_outcome", "count"),
        punches_safe=("safe", "sum"),
        punches_contact=("contact", "sum"),
    ).reset_index().rename(columns={"player_name": "gk_name"})
    stats["punch_success_rate"] = (stats["punches_safe"] / stats["punches_total"]).round(4)
    stats["punch_contact_rate"] = (stats["punches_contact"] / stats["punches_total"]).round(4)
    return stats


def main():
    events = pd.read_csv(PROC_DIR / "gk_events.csv")
    clean = pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")
    qualifying = set(clean["gk_name"])  # matches_played >= 2 filter, applied upstream in clean_data.py

    events = events[events["player_name"].isin(qualifying)].copy()
    print(f"Loaded {len(events)} GK events for {len(qualifying)} qualifying goalkeepers")

    c_stats = claim_stats(events)
    p_stats = punch_stats(events)

    summary = clean[["gk_name", "matches_played"]].merge(c_stats, on="gk_name", how="left") \
                                                    .merge(p_stats, on="gk_name", how="left")
    for c in ["claims_total", "claims_success", "punches_total", "punches_safe", "punches_contact"]:
        summary[c] = summary[c].fillna(0).astype(int)
    summary = summary.sort_values("matches_played", ascending=False).reset_index(drop=True)

    out_path = FINAL_DIR / "gk_claim_punch_success.csv"
    summary.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Saved: {out_path} ({len(summary)} goalkeepers)")

    total_claims = c_stats["claims_total"].sum()
    total_claims_ok = c_stats["claims_success"].sum()
    total_punches = p_stats["punches_total"].sum()
    total_punches_safe = p_stats["punches_safe"].sum()
    print(f"\nTournament-wide: {total_claims_ok}/{total_claims} claims successful "
          f"({total_claims_ok / total_claims:.1%}), "
          f"{total_punches_safe}/{total_punches} punches cleared safely "
          f"({total_punches_safe / total_punches:.1%})")
    print("Done!")


if __name__ == "__main__":
    main()
