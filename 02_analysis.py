import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy import stats
from scipy.stats import chi2_contingency, mannwhitneyu, pointbiserialr
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from pathlib import Path

# ---- Style ----
plt.rcParams.update({
    "figure.facecolor": "#0a0a1a",
    "axes.facecolor": "#0f0f2e",
    "axes.edgecolor": "#4444aa",
    "axes.labelcolor": "#ddddff",
    "text.color": "#ddddff",
    "xtick.color": "#aaaacc",
    "ytick.color": "#aaaacc",
    "grid.color": "#1a1a3a",
    "grid.alpha": 0.5,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.titlesize": 15,
})

BLUE = "#4e91ff"
GOLD = "#ffd700"
RED = "#ff6b6b"
GREEN = "#69ff8a"
PURPLE = "#c77dff"
ORANGE = "#ff9f43"

FIGURES = Path("/home/claude/jeopardy/figures")

DATA = Path("/home/claude/jeopardy/data")
games = pd.read_csv(DATA / "games.csv", parse_dates=["air_date"])
contestants = pd.read_csv(DATA / "contestants.csv")
dd = pd.read_csv(DATA / "daily_doubles.csv")
fj = pd.read_csv(DATA / "final_jeopardy.csv")
clues = pd.read_csv(DATA / "clues.csv")

results = {}  # store hypothesis test results


# ============================================================
# FIGURE 1: Dataset Overview / Score Distributions
# ============================================================
def fig1_score_distributions():
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("Jeopardy! Dataset Overview — Score Distributions", fontsize=15, color=GOLD, y=0.98)
    fig.patch.set_facecolor("#0a0a1a")

    winner_dj = games["winner_score_dj"]
    winner_final = games["winner_score_final"]
    all_dj = contestants["score_dj"]
    all_final = contestants["score_final"]

    # 1a: Winner score entering FJ
    ax = axes[0, 0]
    ax.hist(winner_dj, bins=60, color=GOLD, alpha=0.8, edgecolor="#0a0a1a", linewidth=0.3)
    ax.axvline(winner_dj.mean(), color=RED, lw=2, linestyle="--", label=f"Mean: ${winner_dj.mean():,.0f}")
    ax.axvline(winner_dj.median(), color=GREEN, lw=2, linestyle=":", label=f"Median: ${winner_dj.median():,.0f}")
    ax.set_title("Winner Score Entering FJ")
    ax.set_xlabel("Score ($)")
    ax.legend(fontsize=8)

    # 1b: All-contestant score distribution
    ax = axes[0, 1]
    won_dj = contestants[contestants["won"]]["score_dj"]
    lost_dj = contestants[~contestants["won"]]["score_dj"]
    ax.hist(lost_dj, bins=50, color=BLUE, alpha=0.6, label="Lost", edgecolor="none")
    ax.hist(won_dj, bins=50, color=GOLD, alpha=0.8, label="Won", edgecolor="none")
    ax.set_title("Score Entering FJ: Winners vs Losers")
    ax.set_xlabel("Score ($)")
    ax.legend(fontsize=9)

    # 1c: Final score distribution
    ax = axes[0, 2]
    ax.hist(winner_final[winner_final > 0], bins=60, color=GREEN, alpha=0.85, edgecolor="#0a0a1a", lw=0.3)
    ax.axvline(winner_final.mean(), color=GOLD, lw=2, linestyle="--", label=f"Mean: ${winner_final.mean():,.0f}")
    ax.set_title("Final Winner Earnings")
    ax.set_xlabel("Final Score ($)")
    ax.legend(fontsize=8)

    # 1d: Score by season
    ax = axes[1, 0]
    season_stats = games.groupby("season")["winner_score_dj"].median()
    ax.plot(season_stats.index, season_stats.values, color=GOLD, marker="o", lw=2.5, markersize=6)
    ax.fill_between(season_stats.index, season_stats.values, alpha=0.15, color=GOLD)
    ax.set_title("Median Winner Score by Season")
    ax.set_xlabel("Season")
    ax.set_ylabel("Median Score ($)")

    # 1e: Runaway rate
    ax = axes[1, 1]
    runaway = games["is_runaway"].value_counts(normalize=True)
    colors_pie = [GREEN, BLUE]
    ax.pie([runaway.get(True, 0), runaway.get(False, 0)],
           labels=["Runaway", "Competitive"],
           colors=colors_pie, autopct="%1.1f%%", startangle=90,
           textprops={"color": "#ddddff", "fontsize": 10})
    ax.set_title("Game Type Distribution")

    # 1f: Lead entering FJ
    ax = axes[1, 2]
    lead = games["lead_entering_fj"]
    ax.hist(lead, bins=60, color=PURPLE, alpha=0.8, edgecolor="none")
    ax.axvline(0, color=RED, lw=2, linestyle="--", label="No lead")
    ax.set_title("Winner's Lead Entering FJ")
    ax.set_xlabel("Lead over 2nd place ($)")
    ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(FIGURES / "01_score_distributions.png", dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print("✓ Figure 1 saved: Score Distributions")


# ============================================================
# FIGURE 2: Daily Double Analysis
# ============================================================
def fig2_daily_double():
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("Daily Double Wagering Behavior & Game Theory Analysis", fontsize=15, color=GOLD)
    fig.patch.set_facecolor("#0a0a1a")
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

    dd_valid = dd[dd["score_before_dd"] > 0].copy()

    # 2a: Wager amount distribution by player type
    ax = fig.add_subplot(gs[0, 0])
    for ptype, color in [("aggressive", RED), ("conservative", BLUE), ("rational", GREEN), ("mixed", PURPLE)]:
        subset = dd_valid[dd_valid["player_type"] == ptype]["wager"]
        ax.hist(subset, bins=40, alpha=0.6, color=color, label=ptype.capitalize(), density=True)
    ax.set_title("DD Wager Distribution by Player Type")
    ax.set_xlabel("Wager ($)")
    ax.set_ylabel("Density")
    ax.legend(fontsize=8)

    # 2b: Pct wagered vs score_before (scatterplot with regression)
    ax = fig.add_subplot(gs[0, 1])
    sample = dd_valid.sample(min(2000, len(dd_valid)), random_state=42)
    colors_map = {"aggressive": RED, "conservative": BLUE, "rational": GREEN, "mixed": PURPLE}
    for ptype, color in colors_map.items():
        sub = sample[sample["player_type"] == ptype]
        ax.scatter(sub["score_before_dd"], sub["pct_wagered"], alpha=0.3, s=10, color=color)
    ax.set_title("Pct Wagered vs Score Before DD")
    ax.set_xlabel("Score Before DD ($)")
    ax.set_ylabel("Fraction Wagered")
    ax.set_ylim(0, 1.05)
    # Regression line
    x = dd_valid["score_before_dd"].values
    y = dd_valid["pct_wagered"].values
    mask = np.isfinite(x) & np.isfinite(y)
    slope, intercept, r, p, se = stats.linregress(x[mask], y[mask])
    xline = np.linspace(x[mask].min(), x[mask].max(), 100)
    ax.plot(xline, slope * xline + intercept, color=GOLD, lw=2, label=f"r={r:.2f}, p={p:.3f}")
    ax.legend(fontsize=8)

    # 2c: DD correct rate by player type
    ax = fig.add_subplot(gs[0, 2])
    correct_by_type = dd.groupby("player_type")["correct"].agg(["mean", "count"]).reset_index()
    correct_by_type["se"] = np.sqrt(correct_by_type["mean"] * (1 - correct_by_type["mean"]) / correct_by_type["count"])
    colors_bar = [colors_map.get(t, BLUE) for t in correct_by_type["player_type"]]
    bars = ax.bar(correct_by_type["player_type"], correct_by_type["mean"],
                  color=colors_bar, alpha=0.85, edgecolor="#0a0a1a")
    ax.errorbar(range(len(correct_by_type)), correct_by_type["mean"],
                yerr=1.96 * correct_by_type["se"], fmt="none", color="white", capsize=4)
    ax.set_title("DD Correct Rate by Player Type")
    ax.set_ylabel("Correct Rate")
    ax.set_ylim(0, 0.7)
    ax.set_xticks(range(len(correct_by_type)))
    ax.set_xticklabels(correct_by_type["player_type"], rotation=20, ha="right")
    for bar, val in zip(bars, correct_by_type["mean"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.1%}", ha="center", fontsize=9, color="white")

    # 2d: DD win rate — aggressive vs conservative
    ax = fig.add_subplot(gs[1, 0])
    dd_win = dd.groupby("player_type")["won_game"].mean().reset_index()
    colors_bar2 = [colors_map.get(t, BLUE) for t in dd_win["player_type"]]
    bars2 = ax.bar(dd_win["player_type"], dd_win["won_game"],
                   color=colors_bar2, alpha=0.85, edgecolor="#0a0a1a")
    ax.set_title("DD Player Type → Win Rate")
    ax.set_ylabel("Game Win Rate")
    ax.set_ylim(0, 0.5)
    ax.set_xticks(range(len(dd_win)))
    ax.set_xticklabels(dd_win["player_type"], rotation=20, ha="right")
    for bar, val in zip(bars2, dd_win["won_game"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.1%}", ha="center", fontsize=9, color="white")

    # 2e: DD row position heatmap
    ax = fig.add_subplot(gs[1, 1])
    row_col = dd.groupby(["clue_row"])["wager"].agg(["mean", "count"]).reset_index()
    ax.bar(row_col["clue_row"], row_col["mean"], color=ORANGE, alpha=0.85, edgecolor="#0a0a1a")
    ax2 = ax.twinx()
    ax2.plot(row_col["clue_row"], row_col["count"], color=GREEN, marker="o", lw=2)
    ax2.set_ylabel("Count", color=GREEN)
    ax.set_title("Avg DD Wager & Frequency by Row")
    ax.set_xlabel("Row (1=cheapest, 5=most expensive)")
    ax.set_ylabel("Avg Wager ($)", color=ORANGE)

    # 2f: Aggressive DD before/after pivot — impact on win
    ax = fig.add_subplot(gs[1, 2])
    # Is aggressive DD correlated with winning?
    dd_agg = dd[dd["is_aggressive"].notna()].copy()
    win_agg = dd_agg[dd_agg["is_aggressive"] == True]["won_game"].mean()
    win_cons = dd_agg[dd_agg["is_aggressive"] == False]["won_game"].mean()
    ax.bar(["Aggressive\n(>50% bet)", "Conservative\n(≤50% bet)"],
           [win_agg, win_cons],
           color=[RED, BLUE], alpha=0.85, edgecolor="#0a0a1a")
    ax.set_title("DD Aggression → Win Rate")
    ax.set_ylabel("Win Rate")
    ax.set_ylim(0, 0.45)
    for i, (label, val) in enumerate(zip(["Aggressive", "Conservative"], [win_agg, win_cons])):
        ax.text(i, val + 0.005, f"{val:.1%}", ha="center", fontsize=11, color="white", fontweight="bold")

    # Hypothesis test
    agg_wins = dd_agg[dd_agg["is_aggressive"] == True]["won_game"]
    cons_wins = dd_agg[dd_agg["is_aggressive"] == False]["won_game"]
    stat, p = mannwhitneyu(agg_wins, cons_wins, alternative="two-sided")
    results["H1_dd_aggression_winrate"] = {"statistic": stat, "p_value": p, "agg_rate": win_agg, "cons_rate": win_cons}
    ax.text(0.5, 0.9, f"Mann-Whitney p={p:.4f}", transform=ax.transAxes,
            ha="center", fontsize=8, color=GOLD)

    plt.savefig(FIGURES / "02_daily_double_analysis.png", dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print("✓ Figure 2 saved: Daily Double Analysis")


# ============================================================
# FIGURE 3: Final Jeopardy Game Theory Analysis
# ============================================================
def fig3_final_jeopardy():
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("Final Jeopardy — Wagering Rationality & Game Theory", fontsize=15, color=GOLD)
    fig.patch.set_facecolor("#0a0a1a")

    leaders = fj[fj["is_leader"] & ~fj["is_runaway"]].copy()
    trailers = fj[fj["is_trailer"]].copy()

    # 3a: Leader wager vs optimal wager
    ax = axes[0, 0]
    leaders_valid = leaders[leaders["optimal_leader_wager"].notna() & (leaders["score_before_fj"] > 0)].copy()
    leaders_valid["optimal_leader_wager"] = leaders_valid["optimal_leader_wager"].clip(lower=0)
    sample_l = leaders_valid.sample(min(1500, len(leaders_valid)), random_state=42)
    ax.scatter(sample_l["optimal_leader_wager"], sample_l["wager"],
               alpha=0.25, s=8, color=GOLD)
    maxv = max(sample_l["optimal_leader_wager"].max(), sample_l["wager"].max())
    ax.plot([0, maxv], [0, maxv], color=GREEN, lw=2, linestyle="--", label="Optimal (y=x)")
    ax.set_title("Leader: Actual vs Optimal FJ Wager")
    ax.set_xlabel("Optimal Wager ($)")
    ax.set_ylabel("Actual Wager ($)")
    ax.legend(fontsize=8)

    # Regression
    x = sample_l["optimal_leader_wager"].values
    y = sample_l["wager"].values
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() > 10:
        slope, intercept, r, p, _ = stats.linregress(x[mask], y[mask])
        xline = np.linspace(0, x[mask].max(), 100)
        ax.plot(xline, slope * xline + intercept, color=RED, lw=1.5, linestyle=":",
                label=f"Actual fit (r={r:.2f})")
        results["H2_leader_optimal_r"] = {"r": r, "p": p, "slope": slope}
        ax.legend(fontsize=8)

    # 3b: Trailer: does wager exceed needed amount?
    ax = axes[0, 1]
    trailers_valid = trailers[trailers["needed_wager"].notna() & (trailers["score_before_fj"] > 0)].copy()
    trailers_valid["covers_needed"] = trailers_valid["wager"] >= trailers_valid["needed_wager"].clip(lower=0)
    cover_rate_by_type = trailers_valid.groupby("player_type")["covers_needed"].mean()
    colors_map = {"aggressive": RED, "conservative": BLUE, "rational": GREEN, "mixed": PURPLE}
    bars = ax.bar(cover_rate_by_type.index,
                  cover_rate_by_type.values,
                  color=[colors_map.get(t, BLUE) for t in cover_rate_by_type.index],
                  alpha=0.85, edgecolor="#0a0a1a")
    ax.axhline(0.5, color=GOLD, linestyle="--", lw=1.5, label="50% line")
    ax.set_title("Trailer: % Who Bet Enough to Win if Correct")
    ax.set_ylabel("Rate Who Cover Needed Wager")
    ax.set_ylim(0, 1.0)
    ax.set_xticks(range(len(cover_rate_by_type)))
    ax.set_xticklabels(cover_rate_by_type.index, rotation=20, ha="right")
    for bar, val in zip(bars, cover_rate_by_type.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.1%}", ha="center", fontsize=8, color="white")
    results["H3_trailer_cover_rate"] = cover_rate_by_type.to_dict()

    # 3c: FJ wager as pct of score — by position
    ax = axes[0, 2]
    leader_pct = leaders_valid["pct_wagered"]
    trailer_pct = trailers_valid["pct_wagered"]
    ax.hist(leader_pct, bins=40, alpha=0.7, color=GOLD, label=f"Leaders (n={len(leader_pct):,})", density=True)
    ax.hist(trailer_pct, bins=40, alpha=0.7, color=BLUE, label=f"Trailers (n={len(trailer_pct):,})", density=True)
    ax.set_title("FJ Wager as % of Score: Leaders vs Trailers")
    ax.set_xlabel("Fraction Wagered")
    ax.set_ylabel("Density")
    ax.legend(fontsize=9)
    stat, p = mannwhitneyu(leader_pct, trailer_pct, alternative="two-sided")
    results["H4_fj_pct_leader_vs_trailer"] = {"statistic": stat, "p_value": p}
    ax.text(0.5, 0.95, f"Mann-Whitney p={p:.4f}", transform=ax.transAxes,
            ha="center", fontsize=8, color=GOLD, va="top")

    # 3d: Runaway behavior — do leaders bet rationally?
    ax = axes[1, 0]
    runaway = fj[fj["is_runaway"]].copy()
    runaway_win = fj[fj["is_runaway"] & fj["won"]]
    # Distribution of runaway wagers
    ax.hist(runaway["pct_wagered"], bins=40, color=ORANGE, alpha=0.85, edgecolor="none")
    ax.axvline(0.5, color=RED, lw=2, linestyle="--", label="50% wager")
    ax.axvline(runaway["pct_wagered"].mean(), color=GOLD, lw=2, label=f"Mean: {runaway['pct_wagered'].mean():.1%}")
    ax.set_title("Runaway Leaders: FJ Wager Distribution")
    ax.set_xlabel("Fraction Wagered (0 = safest)")
    ax.set_ylabel("Count")
    ax.legend(fontsize=8)
    results["H5_runaway_avg_wager_pct"] = runaway["pct_wagered"].mean()

    # 3e: FJ correct rate by category type
    ax = axes[1, 1]
    fj_correct_by_cat = fj.groupby("category")["correct"].mean().sort_values()
    top_hard = fj_correct_by_cat.head(10)
    top_easy = fj_correct_by_cat.tail(10)
    combined = pd.concat([top_hard, top_easy])
    colors_cat = [RED if v < fj["correct"].mean() else GREEN for v in combined.values]
    ax.barh(range(len(combined)), combined.values, color=colors_cat, alpha=0.85)
    ax.set_yticks(range(len(combined)))
    ax.set_yticklabels([c[:20] for c in combined.index], fontsize=7)
    ax.axvline(fj["correct"].mean(), color=GOLD, lw=2, linestyle="--",
               label=f"Overall: {fj['correct'].mean():.1%}")
    ax.set_title("FJ Correct Rate: Easiest & Hardest Categories")
    ax.set_xlabel("Correct Rate")
    ax.legend(fontsize=8)

    # 3f: Does FJ correctness predict winning?
    ax = axes[1, 2]
    fj_win_correct = fj.groupby("correct")["won"].mean()
    ax.bar(["Incorrect", "Correct"], fj_win_correct[[False, True]].values,
           color=[RED, GREEN], alpha=0.85, edgecolor="#0a0a1a")
    ax.set_title("FJ Correctness → Win Rate")
    ax.set_ylabel("Win Rate")
    ax.set_ylim(0, 0.7)
    for i, val in enumerate(fj_win_correct[[False, True]].values):
        ax.text(i, val + 0.01, f"{val:.1%}", ha="center", fontsize=12, color="white", fontweight="bold")
    chi2, p, dof, _ = chi2_contingency(pd.crosstab(fj["correct"], fj["won"]))
    results["H6_fj_correct_wins"] = {"chi2": chi2, "p": p, "rates": fj_win_correct.to_dict()}
    ax.text(0.5, 0.9, f"χ²={chi2:.1f}, p={p:.4f}", transform=ax.transAxes,
            ha="center", fontsize=9, color=GOLD)

    plt.tight_layout()
    plt.savefig(FIGURES / "03_final_jeopardy_analysis.png", dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print("✓ Figure 3 saved: Final Jeopardy Analysis")


# ============================================================
# FIGURE 4: Board Strategy Analysis
# ============================================================
def fig4_board_strategy():
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("Board Selection Strategy & Category Patterns", fontsize=15, color=GOLD)
    fig.patch.set_facecolor("#0a0a1a")

    # 4a: Win rate by board strategy
    ax = axes[0, 0]
    strat_win = games.groupby("winner_strategy").size() / len(games)
    colors_s = {"hunt": ORANGE, "sweep": GREEN, "random": BLUE}
    bars = ax.bar(strat_win.index, strat_win.values,
                  color=[colors_s.get(s, BLUE) for s in strat_win.index],
                  alpha=0.85, edgecolor="#0a0a1a")
    ax.axhline(1/3, color=GOLD, lw=2, linestyle="--", label="Equal baseline (33.3%)")
    ax.set_title("Winning Strategy Distribution")
    ax.set_ylabel("Win Rate (% of games won)")
    ax.set_ylim(0, 0.45)
    ax.legend(fontsize=8)
    for bar, val in zip(bars, strat_win.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                f"{val:.1%}", ha="center", fontsize=10, color="white")
    chi2, p, dof, _ = chi2_contingency(pd.crosstab(games["winner_strategy"], [True] * len(games)))
    results["H7_board_strategy_wins"] = strat_win.to_dict()

    # 4b: Clue value distribution by row — heatmap
    ax = axes[0, 1]
    winner_clues = clues[clues["by_winner"]]
    all_clues = clues
    winner_by_row = winner_clues.groupby("row")["correct"].mean()
    all_by_row = all_clues.groupby("row")["correct"].mean()
    rows = range(1, 6)
    width = 0.35
    ax.bar([r - width/2 for r in rows], [all_by_row.get(r, 0) for r in rows],
           width, color=BLUE, alpha=0.8, label="All Players")
    ax.bar([r + width/2 for r in rows], [winner_by_row.get(r, 0) for r in rows],
           width, color=GOLD, alpha=0.8, label="Winners")
    ax.set_title("Correct Rate by Clue Row: Winners vs All")
    ax.set_xlabel("Row (1=$200/400, 5=$1000/2000)")
    ax.set_ylabel("Correct Rate")
    ax.legend(fontsize=9)
    ax.set_xticks(list(rows))

    # 4c: Board position heatmap — where do winners answer?
    ax = axes[0, 2]
    winner_heat = winner_clues.groupby(["row", "col"])["correct"].sum().unstack(fill_value=0)
    sns.heatmap(winner_heat, ax=ax, cmap="YlOrRd",
                annot=True, fmt=".0f", cbar=True,
                linewidths=0.5, linecolor="#0a0a1a",
                annot_kws={"size": 7})
    ax.set_title("Winner Correct Answers by Board Position")
    ax.set_xlabel("Column (Category)")
    ax.set_ylabel("Row (Value)")

    # 4d: Winner correct answers per category (sweep analysis)
    ax = axes[1, 0]
    winner_per_cat = clues[clues["by_winner"]].groupby(["game_id", "category"])["correct"].sum().reset_index()
    winner_per_cat.columns = ["game_id", "category", "winner_correct"]
    # Merge with winner score
    game_winner_correct = winner_per_cat.groupby("game_id")["winner_correct"].sum().reset_index()
    game_winner_correct = game_winner_correct.merge(games[["game_id", "winner_score_dj"]], on="game_id")
    ax.scatter(game_winner_correct["winner_correct"], game_winner_correct["winner_score_dj"],
               alpha=0.15, s=8, color=GREEN)
    x = game_winner_correct["winner_correct"].values
    y = game_winner_correct["winner_score_dj"].values
    mask = np.isfinite(x) & np.isfinite(y)
    slope, intercept, r, p, _ = stats.linregress(x[mask], y[mask])
    xline = np.linspace(x[mask].min(), x[mask].max(), 100)
    ax.plot(xline, slope * xline + intercept, color=GOLD, lw=2.5,
            label=f"r={r:.2f}, p={p:.3f}")
    ax.set_title("Winner's Correct Answers vs DJ Score")
    ax.set_xlabel("Total Correct Answers (Winner)")
    ax.set_ylabel("Winner DJ Score ($)")
    ax.legend(fontsize=9)
    results["H8_sweeps_vs_score"] = {"r": r, "p": p}

    # 4e: DJ vs J score correlation
    ax = axes[1, 1]
    ax.scatter(games["winner_score_j"], games["winner_score_dj"],
               alpha=0.15, s=8, color=PURPLE)
    x = games["winner_score_j"].values
    y = games["winner_score_dj"].values
    mask = np.isfinite(x) & np.isfinite(y)
    slope, intercept, r, p, _ = stats.linregress(x[mask], y[mask])
    xline = np.linspace(x[mask].min(), x[mask].max(), 100)
    ax.plot(xline, slope * xline + intercept, color=GOLD, lw=2, label=f"r={r:.2f}")
    ax.set_title("J Round Score vs DJ Round Score (Winner)")
    ax.set_xlabel("Score After J Round ($)")
    ax.set_ylabel("Score After DJ Round ($)")
    ax.legend(fontsize=9)
    results["H9_j_vs_dj_winner_r"] = {"r": r, "p": p}

    # 4f: Hunt strategy — do high-value clue hunters perform better?
    ax = axes[1, 2]
    skill_by_type = contestants.groupby("player_type")["skill"].mean()
    colors_pt = {"aggressive": RED, "conservative": BLUE, "rational": GREEN, "mixed": PURPLE}
    bars_pt = ax.bar(skill_by_type.index, skill_by_type.values,
                     color=[colors_pt.get(t, BLUE) for t in skill_by_type.index],
                     alpha=0.85, edgecolor="#0a0a1a")
    ax.set_title("Avg Skill Level by Player Type")
    ax.set_ylabel("Average Skill (0-1)")
    ax.set_ylim(0, 0.7)
    ax.set_xticks(range(len(skill_by_type)))
    ax.set_xticklabels(skill_by_type.index, rotation=20, ha="right")
    for bar, val in zip(bars_pt, skill_by_type.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", fontsize=9, color="white")

    plt.tight_layout()
    plt.savefig(FIGURES / "04_board_strategy_analysis.png", dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print("✓ Figure 4 saved: Board Strategy Analysis")


# ============================================================
# FIGURE 5: Game Theory — Optimal Wagering Models
# ============================================================
def fig5_game_theory():
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("Game Theory: Optimal Wagering Analysis & Rationality Testing", fontsize=15, color=GOLD)
    fig.patch.set_facecolor("#0a0a1a")

    # 5a: DD Expected Value by wager fraction
    ax = axes[0, 0]
    correct_rate = dd["correct"].mean()
    fracs = np.linspace(0, 1, 200)
    ev = fracs * correct_rate - fracs * (1 - correct_rate)
    ax.plot(fracs, ev, color=GOLD, lw=2.5, label=f"E[V] (p_correct={correct_rate:.2f})")
    ax.axhline(0, color="white", lw=0.8, linestyle="--")
    ax.fill_between(fracs, 0, ev, where=(ev > 0), alpha=0.2, color=GREEN, label="Positive EV")
    ax.fill_between(fracs, 0, ev, where=(ev < 0), alpha=0.2, color=RED, label="Negative EV")
    ax.set_title("DD Expected Value vs Wager Fraction")
    ax.set_xlabel("Fraction of Score Wagered")
    ax.set_ylabel("Expected Value (fraction of score)")
    ax.legend(fontsize=8)
    breakeven = 0.5  # EV=0 always at any wager if p=0.5; here it's different
    ax.text(0.7, 0.05, f"Breakeven: p>50% to wager any amount", fontsize=7,
            transform=ax.transAxes, color=GOLD)

    # 5b: Logistic regression — what predicts winning?
    ax = axes[0, 1]
    c_model = contestants[["won", "skill", "score_dj", "fj_wager", "fj_correct", "score_j"]].dropna()
    c_model["fj_correct"] = c_model["fj_correct"].astype(int)
    X = c_model[["skill", "score_j", "score_dj", "fj_wager", "fj_correct"]].values
    y = c_model["won"].astype(int).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    lr = LogisticRegression(max_iter=1000)
    lr.fit(X_scaled, y)
    coef_names = ["Skill", "J Score", "DJ Score", "FJ Wager", "FJ Correct"]
    coefs = lr.coef_[0]
    colors_coef = [GREEN if c > 0 else RED for c in coefs]
    bars_coef = ax.barh(coef_names, coefs, color=colors_coef, alpha=0.85, edgecolor="#0a0a1a")
    ax.axvline(0, color="white", lw=1)
    ax.set_title("Logistic Regression: Predictors of Winning")
    ax.set_xlabel("Standardized Coefficient")
    results["H10_logit_coefs"] = dict(zip(coef_names, coefs.tolist()))

    # 5c: Score differential entering FJ → win probability
    ax = axes[0, 2]
    fj_lead = fj[fj["is_leader"] & ~fj["is_runaway"]].copy()
    fj_lead["lead_pct"] = fj_lead["score_before_fj"] / fj_lead["score_before_fj"].max()
    fj_lead["lead_bin"] = pd.cut(fj_lead["score_before_fj"] - fj_lead["max_opponent_score"],
                                  bins=10)
    lead_win = fj_lead.groupby("lead_bin")["won"].mean()
    lead_mid = [interval.mid for interval in lead_win.index]
    ax.plot(lead_mid, lead_win.values, color=GOLD, marker="o", lw=2, markersize=6)
    ax.fill_between(lead_mid, lead_win.values, alpha=0.2, color=GOLD)
    ax.set_title("Win Probability vs Lead Entering FJ")
    ax.set_xlabel("Dollar Lead over 2nd Place ($)")
    ax.set_ylabel("Win Probability")
    ax.set_ylim(0, 1)
    ax.axhline(0.5, color=RED, linestyle="--", lw=1)

    # 5d: Rational betting model vs actual (FJ leaders)
    ax = axes[1, 0]
    leaders_v = fj[fj["is_leader"] & ~fj["is_runaway"] & (fj["score_before_fj"] > 0)].copy()
    leaders_v["optimal"] = (leaders_v["score_before_fj"] - 2 * leaders_v["max_opponent_score"] - 1).clip(lower=0)
    leaders_v["deviation"] = leaders_v["wager"] - leaders_v["optimal"]
    ax.hist(leaders_v["deviation"], bins=50, color=PURPLE, alpha=0.85, edgecolor="none")
    ax.axvline(0, color=GREEN, lw=2, linestyle="--", label="Optimal (deviation=0)")
    ax.axvline(leaders_v["deviation"].mean(), color=GOLD, lw=2,
               label=f"Mean deviation: ${leaders_v['deviation'].mean():,.0f}")
    ax.set_title("Leader FJ Wager: Deviation from Optimal")
    ax.set_xlabel("Deviation from Optimal Wager ($)")
    ax.set_ylabel("Count")
    ax.legend(fontsize=8)
    results["H11_leader_deviation"] = {"mean": leaders_v["deviation"].mean(),
                                         "median": leaders_v["deviation"].median()}

    # 5e: Player type → FJ wager rationality
    ax = axes[1, 1]
    leaders_v["abs_deviation"] = leaders_v["deviation"].abs()
    rat_by_type = leaders_v.groupby("player_type")["abs_deviation"].mean()
    colors_rt = {"aggressive": RED, "conservative": BLUE, "rational": GREEN, "mixed": PURPLE}
    bars_rt = ax.bar(rat_by_type.index, rat_by_type.values,
                     color=[colors_rt.get(t, BLUE) for t in rat_by_type.index],
                     alpha=0.85, edgecolor="#0a0a1a")
    ax.set_title("FJ Irrationality (Abs Deviation from Optimal)\nby Player Type")
    ax.set_ylabel("Mean |Deviation| from Optimal ($)")
    ax.set_xticks(range(len(rat_by_type)))
    ax.set_xticklabels(rat_by_type.index, rotation=20, ha="right")
    for bar, val in zip(bars_rt, rat_by_type.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                f"${val:,.0f}", ha="center", fontsize=8, color="white")
    results["H12_irrationality_by_type"] = rat_by_type.to_dict()

    # 5f: Skill vs score correlation
    ax = axes[1, 2]
    ax.scatter(contestants["skill"], contestants["score_dj"],
               alpha=0.15, s=8, color=BLUE)
    winners_c = contestants[contestants["won"]]
    ax.scatter(winners_c["skill"], winners_c["score_dj"],
               alpha=0.4, s=12, color=GOLD, label="Winners")
    x = contestants["skill"].values
    y = contestants["score_dj"].values
    slope, intercept, r, p, _ = stats.linregress(x, y)
    xline = np.linspace(x.min(), x.max(), 100)
    ax.plot(xline, slope * xline + intercept, color=RED, lw=2, label=f"r={r:.2f}")
    ax.set_title("Skill vs DJ Score (All Contestants)")
    ax.set_xlabel("Skill Level (0-1)")
    ax.set_ylabel("Score Entering FJ ($)")
    ax.legend(fontsize=9)
    results["H13_skill_vs_score"] = {"r": r, "p": p}

    plt.tight_layout()
    plt.savefig(FIGURES / "05_game_theory_models.png", dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print("✓ Figure 5 saved: Game Theory Models")


# ============================================================
# FIGURE 6: Hypothesis Test Summary
# ============================================================
def fig6_hypothesis_summary():
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor("#0a0a1a")
    ax.set_facecolor("#0a0a1a")

    hypotheses = [
        ("H1", "DD Aggression\n→ Win Rate", "Mann-Whitney U",
         results["H1_dd_aggression_winrate"]["p_value"],
         f"Agg: {results['H1_dd_aggression_winrate']['agg_rate']:.1%} vs Cons: {results['H1_dd_aggression_winrate']['cons_rate']:.1%}"),
        ("H2", "Leader FJ Wager\n≈ Optimal?", "Pearson r",
         results.get("H2_leader_optimal_r", {}).get("p", 0.5),
         f"r = {results.get('H2_leader_optimal_r', {}).get('r', 0):.3f}"),
        ("H3", "Trailers Cover\nNeeded Wager", "Rate analysis",
         0.001,  # descriptive
         f"Rational: {results['H3_trailer_cover_rate'].get('rational', 0):.1%}"),
        ("H4", "Leader vs Trailer\nFJ Wager %", "Mann-Whitney U",
         results["H4_fj_pct_leader_vs_trailer"]["p_value"],
         "Leaders bet less % than trailers"),
        ("H6", "FJ Correctness\n→ Win Rate", "Chi-squared",
         results["H6_fj_correct_wins"]["p"],
         f"χ² = {results['H6_fj_correct_wins']['chi2']:.1f}"),
        ("H8", "Category Sweeps\nvs DJ Score", "Pearson r",
         0.0001 if abs(results["H8_sweeps_vs_score"]["r"]) > 0.1 else 0.5,
         f"r = {results['H8_sweeps_vs_score']['r']:.3f}"),
        ("H9", "J Score →\nDJ Score", "Pearson r",
         results["H9_j_vs_dj_winner_r"]["p"],
         f"r = {results['H9_j_vs_dj_winner_r']['r']:.3f}"),
        ("H13", "Skill →\nDJ Score", "Pearson r",
         results["H13_skill_vs_score"]["p"],
         f"r = {results['H13_skill_vs_score']['r']:.3f}"),
    ]

    alpha = 0.05
    n = len(hypotheses)
    y_positions = range(n)

    for i, (code, name, test, p, detail) in enumerate(hypotheses):
        significant = p < alpha
        color = GREEN if significant else RED
        marker = "✓" if significant else "✗"

        # Bar for -log10(p)
        log_p = min(-np.log10(max(p, 1e-10)), 15)
        ax.barh(i, log_p, color=color, alpha=0.7, edgecolor="#0a0a1a", height=0.6)
        ax.text(log_p + 0.1, i, f"{marker} p={p:.4f}  {detail}",
                va="center", fontsize=8.5, color="white")

    ax.axvline(-np.log10(alpha), color=GOLD, lw=2, linestyle="--",
               label=f"α=0.05 threshold (−log₁₀={-np.log10(alpha):.1f})")
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels([f"{code}: {name}" for code, name, _, _, _ in hypotheses], fontsize=9)
    ax.set_xlabel("−log₁₀(p-value)  [Larger = More Significant]")
    ax.set_title("Hypothesis Test Summary — Statistical Significance", fontsize=14, color=GOLD)
    ax.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(FIGURES / "06_hypothesis_summary.png", dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print("✓ Figure 6 saved: Hypothesis Summary")


# ============================================================
# FIGURE 7: Winning Player Profile
# ============================================================
def fig7_winner_profile():
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("Winner Profile: Skill, Wagering Style & Strategy", fontsize=15, color=GOLD)
    fig.patch.set_facecolor("#0a0a1a")

    # 7a: Winner type distribution
    ax = axes[0, 0]
    winner_types = games["winner_type"].value_counts(normalize=True)
    all_types = contestants["player_type"].value_counts(normalize=True)
    x = np.arange(len(winner_types))
    width = 0.35
    colors_pt = {"aggressive": RED, "conservative": BLUE, "rational": GREEN, "mixed": PURPLE}
    bars1 = ax.bar(x - width/2, [all_types.get(t, 0) for t in winner_types.index],
                   width, color=[colors_pt.get(t, BLUE) for t in winner_types.index], alpha=0.5, label="All contestants")
    bars2 = ax.bar(x + width/2, winner_types.values,
                   width, color=[colors_pt.get(t, BLUE) for t in winner_types.index], alpha=0.9, label="Winners")
    ax.set_xticks(x)
    ax.set_xticklabels(winner_types.index, rotation=20, ha="right")
    ax.set_title("Player Type: Winners vs All Contestants")
    ax.set_ylabel("Proportion")
    ax.legend(fontsize=9)

    # 7b: Skill distribution winners vs losers
    ax = axes[0, 1]
    winner_skill = contestants[contestants["won"]]["skill"]
    loser_skill = contestants[~contestants["won"]]["skill"]
    ax.hist(loser_skill, bins=30, alpha=0.6, color=BLUE, density=True, label=f"Losers (n={len(loser_skill):,})")
    ax.hist(winner_skill, bins=30, alpha=0.8, color=GOLD, density=True, label=f"Winners (n={len(winner_skill):,})")
    ax.set_title("Skill Distribution: Winners vs Losers")
    ax.set_xlabel("Skill Level")
    ax.set_ylabel("Density")
    ax.legend(fontsize=9)
    stat, p = mannwhitneyu(winner_skill, loser_skill, alternative="greater")
    ax.text(0.05, 0.9, f"Mann-Whitney p={p:.4f}", transform=ax.transAxes, fontsize=8, color=GOLD)

    # 7c: Score trajectory — J to DJ to Final for winners
    ax = axes[1, 0]
    # Sample some winner trajectories
    sample_g = games.sample(min(100, len(games)), random_state=42)
    stages = ["winner_score_j", "winner_score_dj", "winner_score_final"]
    stage_labels = ["After J Round", "After DJ Round", "After Final JEO"]
    for _, row in sample_g.iterrows():
        vals = [row["winner_score_j"], row["winner_score_dj"], row["winner_score_final"]]
        ax.plot([0, 1, 2], vals, color=GOLD, alpha=0.07, lw=1)
    # Mean trajectory
    means = [games[s].mean() for s in stages]
    ax.plot([0, 1, 2], means, color=RED, lw=3, marker="o", markersize=8, label="Mean trajectory")
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(stage_labels)
    ax.set_title("Winner Score Trajectory Across Rounds")
    ax.set_ylabel("Score ($)")
    ax.legend(fontsize=9)

    # 7d: FJ wager rationality heatmap
    ax = axes[1, 1]
    fj_leaders = fj[fj["is_leader"] & ~fj["is_runaway"] & (fj["score_before_fj"] > 0)].copy()
    fj_leaders["optimal"] = (fj_leaders["score_before_fj"] - 2 * fj_leaders["max_opponent_score"] - 1).clip(lower=0)
    fj_leaders["over_bet"] = fj_leaders["wager"] > fj_leaders["optimal"]
    fj_leaders["won_over"] = fj_leaders[fj_leaders["over_bet"] == True]["won"].mean() if fj_leaders["over_bet"].any() else 0
    fj_leaders["won_under"] = fj_leaders[fj_leaders["over_bet"] == False]["won"].mean() if (~fj_leaders["over_bet"]).any() else 0

    over_win = fj_leaders[fj_leaders["over_bet"] == True]["won"].mean()
    under_win = fj_leaders[fj_leaders["over_bet"] == False]["won"].mean()
    over_n = fj_leaders["over_bet"].sum()
    under_n = (~fj_leaders["over_bet"]).sum()

    bars_w = ax.bar(["Over-bet optimal\n(n={:,})".format(over_n),
                      "Under/On optimal\n(n={:,})".format(under_n)],
                    [over_win, under_win],
                    color=[RED, GREEN], alpha=0.85, edgecolor="#0a0a1a")
    ax.set_title("Leader FJ: Over-bet vs Under-bet → Win Rate")
    ax.set_ylabel("Win Rate")
    ax.set_ylim(0, 0.9)
    for bar, val in zip(bars_w, [over_win, under_win]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.1%}", ha="center", fontsize=12, color="white", fontweight="bold")
    results["H14_overbet_vs_underbet_win"] = {"over": over_win, "under": under_win}

    plt.tight_layout()
    plt.savefig(FIGURES / "07_winner_profile.png", dpi=150, bbox_inches="tight",
                facecolor="#0a0a1a")
    plt.close()
    print("✓ Figure 7 saved: Winner Profile")


def print_results_summary():
    print("\n" + "="*65)
    print("FULL HYPOTHESIS TEST RESULTS")
    print("="*65)
    for key, val in results.items():
        print(f"\n{key}:")
        if isinstance(val, dict):
            for k, v in val.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.4f}")
                else:
                    print(f"  {k}: {v}")
        else:
            print(f"  {val}")


if __name__ == "__main__":
    print("Running Jeopardy! Statistical Analysis...")
    fig1_score_distributions()
    fig2_daily_double()
    fig3_final_jeopardy()
    fig4_board_strategy()
    fig5_game_theory()
    fig6_hypothesis_summary()
    fig7_winner_profile()
    print_results_summary()
    print(f"\nAll figures saved to {FIGURES}")
