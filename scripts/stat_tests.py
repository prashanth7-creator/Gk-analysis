"""
Statistical analysis: descriptive statistics, Z-scores, and significance tests (p-values).
Reads: data/processed/goalkeepers_clean.csv, data/final/goalkeeper_analysis.csv
Writes: data/final/descriptive_stats.csv, data/final/correlation_pvalues.csv, reports/statistical_analysis.md
"""
import sys
import pandas as pd
from scipy import stats
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
FINAL_DIR = ROOT / "data" / "final"
REPORTS_DIR = ROOT / "reports"

DESC_METRICS = {
    "shots_faced": "Shots Faced",
    "xg_faced": "xG Faced",
    "goals_conceded": "Goals Conceded",
    "save_pct": "Save %",
    "goals_prevented": "Goals Prevented (GSaE)",
    "sweeper_per_match": "Sweeper Actions / Match",
    "claims_per_match": "Claims / Match",
    "punches_per_match": "Punches / Match",
    "goal_kicks_per_match": "Goal Kicks / Match",
    "avg_gk_length": "Avg. Goal Kick Length (m)",
}

Z_METRICS = {
    "z_save_pct": "Save %",
    "z_goals_prevented": "Goals Prevented",
    "z_sweeper_per_match": "Sweeper/Match",
    "z_claims_per_match": "Claims/Match",
    "z_goals_conceded": "Goals Conceded",
    "z_xg_faced": "xG Faced",
    "z_gp_per_match": "Goals Prev./Match",
    "z_avg": "Overall Avg Z",
}

# (metric_a, metric_b, human-readable hypothesis)
CORR_PAIRS = [
    ("save_pct", "goals_prevented", "Save % vs. Goals Prevented (GSaE)"),
    ("xg_faced", "goals_conceded", "xG Faced vs. Goals Conceded"),
    ("shots_faced", "save_pct", "Shots Faced vs. Save %"),
    ("sweeper_per_match", "claims_per_match", "Sweeper Actions/Match vs. Claims/Match"),
    ("goal_kicks_per_match", "avg_gk_length", "Goal Kicks/Match vs. Avg. Kick Length"),
    ("matches_played", "save_pct", "Matches Played vs. Save % (sample-size bias check)"),
]


def descriptive_stats(gk: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, label in DESC_METRICS.items():
        s = gk[col]
        rows.append({
            "Metric": label,
            "n": int(s.count()),
            "Mean": s.mean(),
            "Median": s.median(),
            "Std Dev": s.std(),
            "Min": s.min(),
            "25%": s.quantile(0.25),
            "75%": s.quantile(0.75),
            "Max": s.max(),
        })
    return pd.DataFrame(rows)


def correlation_pvalues(gk: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for a, b, label in CORR_PAIRS:
        mask = gk[a].notna() & gk[b].notna()
        r, p = stats.pearsonr(gk.loc[mask, a], gk.loc[mask, b])
        rows.append({
            "Comparison": label,
            "Pearson r": r,
            "p-value": p,
            "Significant (α=0.05)": "Yes" if p < 0.05 else "No",
        })
    return pd.DataFrame(rows)


def one_sample_ttest_gsae(gk: pd.DataFrame) -> dict:
    """Tests whether mean Goals Prevented (GSaE) differs significantly from 0,
    i.e. whether keepers collectively over/under-perform their xG faced."""
    t_stat, p_val = stats.ttest_1samp(gk["goals_prevented"], popmean=0)
    return {
        "n": int(gk["goals_prevented"].count()),
        "mean_gsae": gk["goals_prevented"].mean(),
        "t_stat": t_stat,
        "p_value": p_val,
        "significant": p_val < 0.05,
    }


def fmt(v, nd=2):
    if isinstance(v, (int,)):
        return str(v)
    return f"{v:.{nd}f}"


def build_markdown(desc_df, z_df, corr_df, ttest, n_gk):
    lines = []
    lines.append("## Statistical Analysis — Euro 2024 Goalkeepers\n")
    lines.append(f"Sample: {n_gk} goalkeepers (≥ 2 matches played).\n")

    lines.append("### Descriptive Statistics\n")
    lines.append("| Metric | n | Mean | Median | Std Dev | Min | 25% | 75% | Max |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for _, r in desc_df.iterrows():
        lines.append(
            f"| {r['Metric']} | {r['n']} | {fmt(r['Mean'])} | {fmt(r['Median'])} | "
            f"{fmt(r['Std Dev'])} | {fmt(r['Min'])} | {fmt(r['25%'])} | {fmt(r['75%'])} | {fmt(r['Max'])} |"
        )
    lines.append("")

    lines.append("### Z-Scores by Goalkeeper\n")
    lines.append("Z = (x − μ) ÷ σ, computed per metric across all qualifying goalkeepers. "
                  "Metrics where lower is better (Goals Conceded, xG Faced) are sign-flipped "
                  "so positive always means better-than-average.\n")
    z_cols = list(Z_METRICS.keys())
    header = "| Goalkeeper | " + " | ".join(Z_METRICS[c] for c in z_cols) + " |"
    sep = "|---|" + "---|" * len(z_cols)
    lines.append(header)
    lines.append(sep)
    for _, r in z_df.sort_values("z_avg", ascending=False).iterrows():
        vals = " | ".join(f"{r[c]:+.2f}" for c in z_cols)
        lines.append(f"| {r['gk_name']} | {vals} |")
    lines.append("")

    lines.append("### Correlation & Significance Testing (p-values)\n")
    lines.append("Pearson correlation between metric pairs, tested for significance at α = 0.05.\n")
    lines.append("| Comparison | Pearson r | p-value | Significant (α=0.05) |")
    lines.append("|---|---|---|---|")
    for _, r in corr_df.iterrows():
        lines.append(f"| {r['Comparison']} | {r['Pearson r']:.3f} | {r['p-value']:.4f} | {r['Significant (α=0.05)']} |")
    lines.append("")

    lines.append("### One-Sample t-Test — Goals Prevented (GSaE) vs. 0\n")
    lines.append("Tests whether goalkeepers, as a group, saved significantly more or fewer goals "
                  "than expected by xG (i.e. whether mean GSaE differs from 0).\n")
    lines.append(f"- n = {ttest['n']}")
    lines.append(f"- Mean GSaE = {ttest['mean_gsae']:+.3f}")
    lines.append(f"- t-statistic = {ttest['t_stat']:.3f}")
    lines.append(f"- p-value = {ttest['p_value']:.4f}")
    verdict = "statistically significant" if ttest["significant"] else "not statistically significant"
    lines.append(f"- Result: difference from 0 is **{verdict}** at α = 0.05.\n")

    return "\n".join(lines)


def main():
    gk = pd.read_csv(PROC_DIR / "goalkeepers_clean.csv")
    gk_z = pd.read_csv(FINAL_DIR / "goalkeeper_analysis.csv")

    print(f"Loaded {len(gk)} goalkeepers")

    desc_df = descriptive_stats(gk)
    desc_df.to_csv(FINAL_DIR / "descriptive_stats.csv", index=False)
    print(f"Saved: {FINAL_DIR / 'descriptive_stats.csv'}")

    corr_df = correlation_pvalues(gk)
    corr_df.to_csv(FINAL_DIR / "correlation_pvalues.csv", index=False)
    print(f"Saved: {FINAL_DIR / 'correlation_pvalues.csv'}")

    ttest = one_sample_ttest_gsae(gk)

    md = build_markdown(desc_df, gk_z, corr_df, ttest, len(gk))
    out_path = REPORTS_DIR / "statistical_analysis.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"Saved: {out_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
