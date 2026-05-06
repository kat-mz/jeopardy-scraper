"""
Jeopardy! Data Cleaning & Exploratory Data Analysis
=====================================================
Load raw J-Archive scraped JSON and flatten into analysis-ready DataFrames.
Automatically detects data path and processes all games.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Find data directory
def find_data_path():
    """Locate jarchive_raw.json in data/ subdirectory."""
    cwd = Path.cwd()
    data_dir = cwd / "data"
    raw_file = data_dir / "jarchive_raw.json"
    
    if raw_file.exists():
        return raw_file, data_dir
    
    # Fallback: check parent directory
    parent_data = cwd.parent / "data"
    parent_raw = parent_data / "jarchive_raw.json"
    if parent_raw.exists():
        return parent_raw, parent_data
    
    print(f"❌ ERROR: Cannot find jarchive_raw.json")
    print(f"   Expected: {raw_file}")
    print(f"\n   First, run: python jarchive_scraper.py --seasons 1 40 --output data/jarchive_raw.json")
    sys.exit(1)

DATA_PATH, OUTPUT_PATH = find_data_path()

print(f"📂 Data path: {DATA_PATH}")
print(f"📂 Output path: {OUTPUT_PATH}")


def load_and_clean():
    """Load raw JSON from J-Archive and flatten into analysis-ready DataFrames."""
    print("\n🔍 Loading dataset...")
    with open(DATA_PATH) as f:
        games = json.load(f)

    print(f"✓ Loaded {len(games)} games from J-Archive\n")

    # ---- Games-level DataFrame ----
    game_rows = []
    for g in games:
        if not g.get("scores") or not g.get("winner"):
            continue  # Skip incomplete games
            
        scores_dj = g["scores"].get("end_of_dj", {})
        scores_final = g["scores"].get("final", {})
        scores_j = g["scores"].get("end_of_j", {})
        winner = g["winner"]

        # Winner's score at each stage
        winner_score_j = scores_j.get(winner, 0)
        winner_score_dj = scores_dj.get(winner, 0)
        winner_score_final = scores_final.get(winner, 0)

        # Opponent scores entering FJ
        opp_scores_dj = [v for k, v in scores_dj.items() if k != winner]
        lead_entering_fj = winner_score_dj - max(opp_scores_dj) if opp_scores_dj else winner_score_dj
        is_runaway = winner_score_dj > 2 * sum([max(s, 0) for s in opp_scores_dj])

        game_rows.append({
            "game_id": g.get("game_id"),
            "air_date": g.get("air_date"),
            "season": g.get("season"),
            "winner": winner,
            "winner_score_j": winner_score_j,
            "winner_score_dj": winner_score_dj,
            "winner_score_final": winner_score_final,
            "lead_entering_fj": lead_entering_fj,
            "is_runaway": is_runaway,
        })

    games_df = pd.DataFrame(game_rows)
    games_df["air_date"] = pd.to_datetime(games_df["air_date"], errors='coerce')

    # ---- All-contestants DataFrame ----
    contestant_rows = []
    for g in games:
        if not g.get("scores") or not g.get("contestants"):
            continue
            
        winner = g["winner"]
        scores_dj = g["scores"].get("end_of_dj", {})
        scores_final = g["scores"].get("final", {})
        scores_j = g["scores"].get("end_of_j", {})

        for i, c in enumerate(g["contestants"]):
            name = c.get("name", f"Player_{i}")
            
            # FJ info for this contestant
            fj_data = {}
            if g.get("final_jeopardy", {}).get("wagers"):
                fj_data = next((w for w in g["final_jeopardy"]["wagers"] 
                              if w.get("contestant") == name), {})

            contestant_rows.append({
                "game_id": g.get("game_id"),
                "season": g.get("season"),
                "contestant": name,
                "won": name == winner,
                "score_j": scores_j.get(name, 0),
                "score_dj": scores_dj.get(name, 0),
                "score_final": scores_final.get(name, 0),
                "fj_wager": fj_data.get("wager"),
                "fj_correct": fj_data.get("correct"),
            })

    contestants_df = pd.DataFrame(contestant_rows)

    # ---- Daily Double DataFrame ----
    dd_rows = []
    for g in games:
        if not g.get("jeopardy_round") and not g.get("double_jeopardy_round"):
            continue
            
        winner = g["winner"]
        
        for round_name, round_data in [
            ("jeopardy", g.get("jeopardy_round", {})),
            ("double_jeopardy", g.get("double_jeopardy_round", {}))
        ]:
            if not round_data.get("clues"):
                continue
                
            for clue in round_data["clues"]:
                if clue.get("daily_double"):
                    wager = clue.get("dd_wager")
                    if wager is None:
                        continue
                    
                    # For real J-Archive data, we only have the wager amount,
                    # not which player won the DD (that info isn't in HTML)
                    dd_rows.append({
                        "game_id": g.get("game_id"),
                        "season": g.get("season"),
                        "round": round_name,
                        "wager": wager,
                        "clue_row": clue.get("row"),
                        "clue_value": clue.get("value"),
                        "category": clue.get("category"),
                    })

    dd_df = pd.DataFrame(dd_rows) if dd_rows else pd.DataFrame()

    # ---- Final Jeopardy DataFrame ----
    fj_rows = []
    for g in games:
        if not g.get("final_jeopardy") or not g.get("final_jeopardy", {}).get("wagers"):
            continue
            
        scores_dj = g["scores"].get("end_of_dj", {})
        winner = g["winner"]

        for w in g["final_jeopardy"]["wagers"]:
            name = w.get("contestant")
            if not name:
                continue
                
            score_before = w.get("score_before_fj", scores_dj.get(name, 0))
            wager = w.get("wager", 0)
            opp_scores = [v for k, v in scores_dj.items() if k != name]
            max_opp = max(opp_scores) if opp_scores else 0

            is_leader = score_before >= max_opp
            is_runaway = score_before > 2 * sum([max(s, 0) for s in opp_scores])

            # Optimal wager for leader: score - (2 * max_opp + 1)
            optimal_leader_wager = max(0, score_before - (2 * max_opp + 1)) if is_leader else None

            # Rational trailer wager: need score_before + wager > max_opp + max_opp (all-in)
            needed_wager = (2 * max_opp - score_before + 1) if not is_leader else None

            pct_wagered = wager / max(score_before, 1) if score_before > 0 else 0

            fj_rows.append({
                "game_id": g.get("game_id"),
                "season": g.get("season"),
                "contestant": name,
                "score_before_fj": score_before,
                "wager": wager,
                "pct_wagered": pct_wagered,
                "correct": w.get("correct"),
                "is_leader": is_leader,
                "is_runaway": is_runaway,
                "is_trailer": not is_leader,
                "max_opponent_score": max_opp,
                "optimal_leader_wager": optimal_leader_wager,
                "needed_wager": needed_wager,
                "won": name == winner,
                "category": g.get("final_jeopardy", {}).get("category"),
            })

    fj_df = pd.DataFrame(fj_rows) if fj_rows else pd.DataFrame()

    # ---- Clue-level DataFrame for board strategy analysis ----
    clue_rows = []
    for g in games:
        if not g.get("jeopardy_round") and not g.get("double_jeopardy_round"):
            continue
            
        winner = g["winner"]
        for round_name, round_data in [
            ("jeopardy", g.get("jeopardy_round", {})),
            ("double_jeopardy", g.get("double_jeopardy_round", {}))
        ]:
            if not round_data.get("clues"):
                continue
                
            for clue in round_data["clues"]:
                clue_rows.append({
                    "game_id": g.get("game_id"),
                    "season": g.get("season"),
                    "round": round_name,
                    "category": clue.get("category"),
                    "value": clue.get("value"),
                    "row": clue.get("row"),
                    "col": clue.get("col"),
                    "daily_double": clue.get("daily_double", False),
                    "winner": winner,
                })

    clues_df = pd.DataFrame(clue_rows) if clue_rows else pd.DataFrame()

    return games_df, contestants_df, dd_df, fj_df, clues_df


def print_eda(games_df, contestants_df, dd_df, fj_df, clues_df):
    print("\n" + "="*70)
    print("EXPLORATORY DATA ANALYSIS SUMMARY")
    print("="*70)

    print(f"\n{'DATASET OVERVIEW'}")
    print(f"  Total games: {len(games_df):,}")
    if len(games_df) > 0:
        print(f"  Seasons: {games_df['season'].min():.0f} – {games_df['season'].max():.0f}")
        print(f"  Date range: {games_df['air_date'].min().date() if pd.notna(games_df['air_date'].min()) else 'N/A'} to {games_df['air_date'].max().date() if pd.notna(games_df['air_date'].max()) else 'N/A'}")
    print(f"  Total Daily Doubles: {len(dd_df):,}")
    print(f"  Total FJ observations: {len(fj_df):,}")
    print(f"  Total clues: {len(clues_df):,}")

    if len(games_df) > 0:
        print(f"\n{'SCORE DISTRIBUTIONS'}")
        print(f"  Avg winner score (entering FJ): ${games_df['winner_score_dj'].mean():,.0f}")
        print(f"  Median winner score (entering FJ): ${games_df['winner_score_dj'].median():,.0f}")
        print(f"  Avg final winner score: ${games_df['winner_score_final'].mean():,.0f}")
        print(f"  Runaway game rate: {games_df['is_runaway'].mean():.1%}")

    if len(dd_df) > 0:
        print(f"\n{'DAILY DOUBLE'}")
        print(f"  Total DDs: {len(dd_df):,}")
        print(f"  Avg wager: ${dd_df['wager'].mean():,.0f}")
        print(f"  Median wager: ${dd_df['wager'].median():,.0f}")
        print(f"  DD by round: {dd_df.groupby('round')['game_id'].count().to_dict()}")

    if len(fj_df) > 0:
        print(f"\n{'FINAL JEOPARDY'}")
        print(f"  Total FJ wagers: {len(fj_df):,}")
        print(f"  Avg wager: ${fj_df['wager'].mean():,.0f}")
        print(f"  Correctness rate: {fj_df['correct'].mean():.1%}")
        if (fj_df['is_leader']).any():
            print(f"  Avg leader wager (pct): {fj_df[fj_df['is_leader']]['pct_wagered'].mean():.1%}")
        if (fj_df['is_trailer']).any():
            print(f"  Avg trailer wager (pct): {fj_df[fj_df['is_trailer']]['pct_wagered'].mean():.1%}")

    if len(clues_df) > 0:
        print(f"\n{'BOARD STRATEGY'}")
        print(f"  Total clues: {len(clues_df):,}")
        print(f"  Daily Doubles: {clues_df['daily_double'].sum():,}")

    print()


if __name__ == "__main__":
    games_df, contestants_df, dd_df, fj_df, clues_df = load_and_clean()
    print_eda(games_df, contestants_df, dd_df, fj_df, clues_df)

    # Save cleaned data
    games_df.to_csv(OUTPUT_PATH / "games.csv", index=False)
    contestants_df.to_csv(OUTPUT_PATH / "contestants.csv", index=False)
    dd_df.to_csv(OUTPUT_PATH / "daily_doubles.csv", index=False)
    fj_df.to_csv(OUTPUT_PATH / "final_jeopardy.csv", index=False)
    clues_df.to_csv(OUTPUT_PATH / "clues.csv", index=False)
    
    print(f"✓ Cleaned CSVs saved to {OUTPUT_PATH}/")
    print(f"\nNext: python 02_analysis.py")
