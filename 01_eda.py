"""
Jeopardy! Data Cleaning & Exploratory Data Analysis
=====================================================
Task 1 & 2: Load, clean, and explore the dataset.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path("/home/claude/jeopardy/data/jeopardy_synthetic.json")
OUTPUT_PATH = Path("/home/claude/jeopardy/data")


def load_and_clean():
    """Load raw JSON and flatten into analysis-ready DataFrames."""
    print("Loading dataset...")
    with open(DATA_PATH) as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games.")

    # ---- Games-level DataFrame ----
    game_rows = []
    for g in games:
        scores_dj = g["scores"]["end_of_dj"]
        scores_final = g["scores"]["final"]
        scores_j = g["scores"]["end_of_j"]
        winner = g["winner"]

        # Contestant info
        contestants = g["contestants"]
        winner_idx = g["winner_idx"]
        winner_info = contestants[winner_idx]

        # Aggregate category sweeps
        j_sweeps = g["jeopardy_round"].get("category_sweeps", 0)
        dj_sweeps = g["double_jeopardy_round"].get("category_sweeps", 0)
        total_sweeps = j_sweeps + dj_sweeps

        # Winner's score at each stage
        winner_score_j = scores_j.get(winner, 0)
        winner_score_dj = scores_dj.get(winner, 0)
        winner_score_final = scores_final.get(winner, 0)

        # Opponent scores entering FJ
        opp_scores_dj = [v for k, v in scores_dj.items() if k != winner]
        lead_entering_fj = winner_score_dj - max(opp_scores_dj) if opp_scores_dj else winner_score_dj
        is_runaway = winner_score_dj > 2 * sum([max(s, 0) for s in opp_scores_dj])

        game_rows.append({
            "game_id": g["game_id"],
            "air_date": g["air_date"],
            "season": g["season"],
            "winner": winner,
            "winner_idx": winner_idx,
            "winner_skill": winner_info["skill"],
            "winner_type": winner_info["player_type"],
            "winner_strategy": winner_info["board_strategy"],
            "winner_score_j": winner_score_j,
            "winner_score_dj": winner_score_dj,
            "winner_score_final": winner_score_final,
            "lead_entering_fj": lead_entering_fj,
            "is_runaway": is_runaway,
            "total_category_sweeps": total_sweeps,
            "j_category_sweeps": j_sweeps,
            "dj_category_sweeps": dj_sweeps,
        })

    games_df = pd.DataFrame(game_rows)
    games_df["air_date"] = pd.to_datetime(games_df["air_date"])

    # ---- All-contestants DataFrame ----
    contestant_rows = []
    for g in games:
        winner = g["winner"]
        scores_dj = g["scores"]["end_of_dj"]
        scores_final = g["scores"]["final"]
        scores_j = g["scores"]["end_of_j"]

        for i, c in enumerate(g["contestants"]):
            name = c["name"]
            opp_scores = [v for k, v in scores_dj.items() if k != name]

            # FJ info for this contestant
            fj_data = next((w for w in g["final_jeopardy"]["wagers"] if w["contestant"] == name), {})

            contestant_rows.append({
                "game_id": g["game_id"],
                "season": g["season"],
                "contestant": name,
                "skill": c["skill"],
                "player_type": c["player_type"],
                "board_strategy": c["board_strategy"],
                "won": name == winner,
                "score_j": scores_j.get(name, 0),
                "score_dj": scores_dj.get(name, 0),
                "score_final": scores_final.get(name, 0),
                "fj_wager": fj_data.get("wager", None),
                "fj_correct": fj_data.get("correct", None),
                "fj_score_before": fj_data.get("score_before_fj", None),
            })

    contestants_df = pd.DataFrame(contestant_rows)

    # ---- Daily Double DataFrame ----
    dd_rows = []
    for g in games:
        scores_running = {c["name"]: 0 for c in g["contestants"]}
        winner = g["winner"]

        for round_name, round_data in [
            ("jeopardy", g["jeopardy_round"]),
            ("double_jeopardy", g["double_jeopardy_round"])
        ]:
            for clue in round_data["clues"]:
                if clue["daily_double"]:
                    player = clue["answered_by"]
                    score_before = scores_running.get(player, 0)
                    wager = clue["dd_wager"]
                    if wager is None:
                        continue

                    # Pct of score wagered
                    pct_wagered = wager / max(score_before, 1) if score_before > 0 else None
                    is_aggressive = pct_wagered > 0.5 if pct_wagered is not None else None

                    dd_rows.append({
                        "game_id": g["game_id"],
                        "season": g["season"],
                        "round": round_name,
                        "player": player,
                        "player_type": next((c["player_type"] for c in g["contestants"] if c["name"] == player), None),
                        "score_before_dd": score_before,
                        "wager": wager,
                        "pct_wagered": pct_wagered,
                        "is_aggressive": is_aggressive,
                        "correct": clue["correct"],
                        "clue_row": clue["row"],
                        "clue_value": clue["value"],
                        "won_game": player == winner,
                    })

                # Update running scores
                if clue["correct"]:
                    if clue["daily_double"]:
                        player = clue["answered_by"]
                        scores_running[player] = scores_running.get(player, 0) + (clue["dd_wager"] or 0)
                    else:
                        player = clue["answered_by"]
                        scores_running[player] = scores_running.get(player, 0) + clue["value"]
                else:
                    player = clue["answered_by"]
                    if clue["daily_double"]:
                        scores_running[player] = scores_running.get(player, 0) - (clue["dd_wager"] or 0)
                    else:
                        scores_running[player] = scores_running.get(player, 0) - clue["value"]

    dd_df = pd.DataFrame(dd_rows)

    # ---- Final Jeopardy DataFrame ----
    fj_rows = []
    for g in games:
        scores_dj = g["scores"]["end_of_dj"]
        winner = g["winner"]

        for w in g["final_jeopardy"]["wagers"]:
            name = w["contestant"]
            score_before = w["score_before_fj"]
            wager = w["wager"]
            opp_scores = [v for k, v in scores_dj.items() if k != name]
            max_opp = max(opp_scores) if opp_scores else 0

            is_leader = score_before >= max_opp
            is_runaway = score_before > 2 * sum([max(s, 0) for s in opp_scores])

            # Optimal wager for leader: score - (2 * max_opp + 1)
            optimal_leader_wager = max(0, score_before - (2 * max_opp + 1)) if is_leader else None

            # Rational trailer wager: need score_before + wager > max_opp + max_opp (all-in)
            # i.e., wager > max_opp * 2 - score_before + 1
            needed_wager = (2 * max_opp - score_before + 1) if not is_leader else None

            pct_wagered = wager / max(score_before, 1) if score_before > 0 else 0

            fj_rows.append({
                "game_id": g["game_id"],
                "season": g["season"],
                "contestant": name,
                "player_type": next((c["player_type"] for c in g["contestants"] if c["name"] == name), None),
                "score_before_fj": score_before,
                "wager": wager,
                "pct_wagered": pct_wagered,
                "correct": w["correct"],
                "is_leader": is_leader,
                "is_runaway": is_runaway,
                "is_trailer": not is_leader,
                "max_opponent_score": max_opp,
                "optimal_leader_wager": optimal_leader_wager,
                "needed_wager": needed_wager,
                "won": name == winner,
                "category": g["final_jeopardy"]["category"],
            })

    fj_df = pd.DataFrame(fj_rows)

    # ---- Clue-level DataFrame for board strategy analysis ----
    clue_rows = []
    for g in games:
        winner = g["winner"]
        for round_name, round_data in [
            ("jeopardy", g["jeopardy_round"]),
            ("double_jeopardy", g["double_jeopardy_round"])
        ]:
            for clue in round_data["clues"]:
                clue_rows.append({
                    "game_id": g["game_id"],
                    "season": g["season"],
                    "round": round_name,
                    "category": clue["category"],
                    "value": clue["value"],
                    "row": clue["row"],
                    "col": clue["col"],
                    "daily_double": clue["daily_double"],
                    "correct": clue["correct"],
                    "answered_by": clue["answered_by"],
                    "by_winner": clue["answered_by"] == winner,
                    "winner": winner,
                })

    clues_df = pd.DataFrame(clue_rows)

    return games_df, contestants_df, dd_df, fj_df, clues_df


def print_eda(games_df, contestants_df, dd_df, fj_df, clues_df):
    print("\n" + "="*60)
    print("EXPLORATORY DATA ANALYSIS SUMMARY")
    print("="*60)

    print(f"\n{'DATASET OVERVIEW':}")
    print(f"  Total games: {len(games_df):,}")
    print(f"  Seasons: {games_df['season'].min()} – {games_df['season'].max()}")
    print(f"  Date range: {games_df['air_date'].min().date()} to {games_df['air_date'].max().date()}")
    print(f"  Total Daily Doubles: {len(dd_df):,}")
    print(f"  Total FJ observations: {len(fj_df):,}")
    print(f"  Total clues: {len(clues_df):,}")

    print(f"\n{'SCORE DISTRIBUTIONS':}")
    print(f"  Avg winner score (entering FJ): ${games_df['winner_score_dj'].mean():,.0f}")
    print(f"  Median winner score (entering FJ): ${games_df['winner_score_dj'].median():,.0f}")
    print(f"  Avg final winner score: ${games_df['winner_score_final'].mean():,.0f}")
    print(f"  Runaway game rate: {games_df['is_runaway'].mean():.1%}")

    print(f"\n{'DAILY DOUBLE':}")
    print(f"  Total DDs: {len(dd_df):,}")
    print(f"  Avg wager: ${dd_df['wager'].mean():,.0f}")
    print(f"  Avg pct of score wagered: {dd_df['pct_wagered'].dropna().mean():.1%}")
    print(f"  Correctness rate: {dd_df['correct'].mean():.1%}")
    print(f"  DD by round: {dd_df.groupby('round')['game_id'].count().to_dict()}")
    print(f"  Aggressive bets (>50% of score): {dd_df['is_aggressive'].dropna().mean():.1%}")

    print(f"\n{'FINAL JEOPARDY':}")
    print(f"  Correctness rate: {fj_df['correct'].mean():.1%}")
    print(f"  Avg leader wager (pct): {fj_df[fj_df['is_leader']]['pct_wagered'].mean():.1%}")
    print(f"  Avg trailer wager (pct): {fj_df[fj_df['is_trailer']]['pct_wagered'].mean():.1%}")
    print(f"  Runaway rate: {fj_df['is_runaway'].mean():.1%}")

    print(f"\n{'BOARD STRATEGY':}")
    print(f"  Avg category sweeps per game: {games_df['total_category_sweeps'].mean():.2f}")
    print(f"  Games with 0 sweeps: {(games_df['total_category_sweeps'] == 0).mean():.1%}")
    print(f"  Winner strategy dist: {games_df['winner_strategy'].value_counts(normalize=True).round(3).to_dict()}")


if __name__ == "__main__":
    games_df, contestants_df, dd_df, fj_df, clues_df = load_and_clean()
    print_eda(games_df, contestants_df, dd_df, fj_df, clues_df)

    # Save cleaned data
    games_df.to_csv(OUTPUT_PATH / "games.csv", index=False)
    contestants_df.to_csv(OUTPUT_PATH / "contestants.csv", index=False)
    dd_df.to_csv(OUTPUT_PATH / "daily_doubles.csv", index=False)
    fj_df.to_csv(OUTPUT_PATH / "final_jeopardy.csv", index=False)
    clues_df.to_csv(OUTPUT_PATH / "clues.csv", index=False)
    print("\nCleaned CSVs saved to /home/claude/jeopardy/data/")
