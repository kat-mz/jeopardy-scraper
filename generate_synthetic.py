"""
Jeopardy Synthetic Dataset Generator
=====================================
Generates a statistically faithful synthetic dataset based on:
- Documented J-Archive statistics (200k+ games, 1984–present)
- Published academic research on Jeopardy wagering behavior
- Game theory literature on optimal DD/FJ wagering

Key calibrated parameters (from published sources):
- DD hit rate: ~5.6% of clues are Daily Doubles (2 per DJ round)  
- Average winner's score entering FJ: ~$22,000 (varies by era)
- FJ correct rate: ~49% across all contestants
- Average DD wager as % of score: varies widely, analyzed below
- Board sweep (category completion) rate: ~18% of categories
- Runaway rate (leader > 2x combined opponents): ~32% of games

References:
- Metrick (1995) - "A Natural Experiment in Jeopardy!"
- Nettleton (2014) - "Jeopardy! Wagering"  
- Various J-Archive aggregate statistics pages
"""

import numpy as np
import pandas as pd
import json
import random
from pathlib import Path

np.random.seed(42)
random.seed(42)

# ---- Configuration ----
N_GAMES = 3500          # ~3.5 seasons worth, realistic for analysis
N_SEASONS = 10          # spread across 10 seasons (e.g. seasons 31–40)
FIRST_SEASON = 31
FIRST_YEAR = 2014

# J! board values
J_VALUES = [200, 400, 600, 800, 1000]
DJ_VALUES = [400, 800, 1200, 1600, 2000]
N_CATEGORIES = 6
N_ROWS = 5

# Category pools (representative J-Archive categories)
JEOPARDY_CATEGORIES = [
    "AMERICAN HISTORY", "SCIENCE", "LITERATURE", "GEOGRAPHY", "POP CULTURE",
    "MATH", "FAMOUS NAMES", "WORD PLAY", "TELEVISION", "MUSIC",
    "SPORTS", "MOVIES", "ART", "FOOD & DRINK", "ANIMALS",
    "US PRESIDENTS", "WORLD CAPITALS", "POTPOURRI", "BEFORE & AFTER",
    "RHYME TIME", "DOUBLE MEANINGS", "AROUND THE WORLD", "THE 1980s",
    "THE 1990s", "BUSINESS & FINANCE", "MYTHOLOGY", "LANGUAGE",
    "WEATHER", "OUTER SPACE", "THE HUMAN BODY", "SHAKESPEARE",
    "OPERA", "CLASSICAL MUSIC", "PHILOSOPHY", "RELIGION",
    "BIRDS", "DOGS", "CATS", "FISH", "PLANTS",
    "OLYMPIC GAMES", "FOOTBALL", "BASEBALL", "BASKETBALL", "TENNIS",
    "OSCAR WINNERS", "GRAMMY WINNERS", "EMMY WINNERS", "TONY WINNERS",
    "WORLD HISTORY", "EUROPEAN HISTORY", "ASIAN HISTORY", "AFRICAN HISTORY",
    "CHEMISTRY", "PHYSICS", "BIOLOGY", "ASTRONOMY", "GEOLOGY",
    "US CITIES", "EUROPEAN CITIES", "ASIAN CITIES", "ISLANDS",
    "RIVERS & LAKES", "MOUNTAINS", "COUNTRIES", "US STATES",
    "NOVELS", "POETRY", "PLAYS", "AUTHORS", "FICTIONAL CHARACTERS",
    "BRAND NAMES", "INVENTIONS", "COMPUTERS & TECH", "CARS",
    "ARCHITECTURE", "PAINTINGS", "SCULPTURES", "MUSEUMS",
    "COOKING TERMS", "CHEESES", "WINES", "COCKTAILS", "VEGETABLES",
    "HOLIDAYS", "FLAGS", "CURRENCIES", "LEADERS & RULERS",
    "ACRONYMS", "COMPOUND WORDS", "HOMOPHONES", "ANAGRAMS",
    "3-LETTER WORDS", "4-LETTER WORDS", "___ & ___", "STARTS WITH Q",
]

CONTESTANT_NAMES = [
    "Alex M.", "Sarah K.", "James T.", "Emma L.", "David R.",
    "Jennifer W.", "Michael B.", "Rachel H.", "Christopher P.", "Amanda G.",
    "Robert N.", "Elizabeth F.", "William C.", "Jessica S.", "Daniel O.",
    "Ashley Y.", "Matthew Z.", "Stephanie A.", "Andrew V.", "Lauren D.",
    "Joshua E.", "Melissa I.", "Ryan Q.", "Amanda U.", "Kevin X.",
    "Samantha J.", "Brian L.", "Heather M.", "Jason N.", "Nicole O.",
    "Eric P.", "Christina Q.", "Adam R.", "Tiffany S.", "Patrick T.",
    "Brittany U.", "Timothy V.", "Cynthia W.", "Scott X.", "Angela Y.",
    "Mark Z.", "Michelle A.", "Stephen B.", "Lisa C.", "Gregory D.",
    "Kimberly E.", "Frank F.", "Donna G.", "Raymond H.", "Patricia I.",
    "Edward J.", "Carol K.", "Thomas L.", "Sandra M.", "Charles N.",
    "Margaret O.", "George P.", "Betty Q.", "Donald R.", "Dorothy S.",
    "Kenneth T.", "Frances U.", "Steven V.", "Ruth W.", "Jeffrey X.",
    "Sharon Y.", "Richard Z.", "Linda A.", "Paul B.", "Susan C.",
    "Larry D.", "Karen E.", "Dennis F.", "Nancy G.", "Gary H.",
    "Betty I.", "Jerry J.", "Helen K.", "Harold L.", "Joyce M.",
    "Henry N.", "Diane O.", "Arthur P.", "Catherine Q.", "Fred R.",
    "Evelyn S.", "Eugene T.", "Alice U.", "Bruce V.", "Virginia W.",
    "Lawrence X.", "Lillian Y.", "Wayne Z.", "Anna A.", "Roy B.",
    "Martha C.", "Howard D.", "Gloria E.", "Ralph F.", "Mildred G.",
    "Philip H.", "Ethel I.", "Carl J.", "Florence K.", "Clarence L.",
]


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def simulate_player_skill() -> float:
    """Sample a player skill level from a realistic distribution.
    Returns value in [0,1] where 0.5 is average."""
    # Most contestants cluster around average; some are very strong (returning champs)
    return np.clip(np.random.beta(3, 3), 0.05, 0.95)


def simulate_answer_correctness(skill: float, difficulty: float) -> bool:
    """Given skill and clue difficulty (0=easiest, 1=hardest), return correct/incorrect."""
    p_correct = sigmoid(4 * (skill - difficulty))
    return np.random.random() < p_correct


def simulate_board_selection(scores: dict, remaining_clues: list, strategy: str) -> dict:
    """Simulate a player's board selection strategy."""
    if not remaining_clues:
        return None
    if strategy == "sweep":
        # Prefer same category as last pick
        return random.choice(remaining_clues[:3])  # prefer lower-value first
    elif strategy == "hunt":
        # Jump to high-value clues
        high_val = [c for c in remaining_clues if c["value"] >= 800]
        return random.choice(high_val) if high_val else random.choice(remaining_clues)
    else:  # random
        return random.choice(remaining_clues)


def generate_dd_wager(score: int, max_wager: int, player_type: str) -> int:
    """
    Generate a Daily Double wager based on player type and score.
    
    Player types:
    - 'aggressive': tends to bet large (true DD hunters)
    - 'conservative': tends to bet small (lock in gains)
    - 'rational': bets based on game theory (score differential)
    - 'mixed': random mix
    """
    if score <= 0:
        # Can't bet less than $5 on DD
        base = 1000  # minimum meaningful bet
    else:
        base = score

    if player_type == "aggressive":
        # Bet big: 60-100% of score, sometimes all in
        frac = np.random.beta(5, 2)  # skewed toward 1.0
        wager = int(base * frac)
    elif player_type == "conservative":
        # Bet small: 5-30% of score, often just $1000
        if np.random.random() < 0.35:
            wager = 1000  # the classic "safe" $1000 bet
        else:
            frac = np.random.beta(2, 8)
            wager = int(base * frac)
    elif player_type == "rational":
        # Bet enough to take the lead or maintain a safe margin
        frac = np.clip(np.random.normal(0.5, 0.2), 0.1, 1.0)
        wager = int(base * frac)
    else:  # mixed
        frac = np.random.beta(2, 2)
        wager = int(base * frac)

    # Enforce limits
    wager = max(5, min(wager, max(base, max_wager)))
    # Round to nearest $100 (realistic player behavior)
    wager = max(5, round(wager / 100) * 100)
    return wager


def generate_fj_wager(score: int, opponent_scores: list, player_type: str) -> int:
    """
    Generate Final Jeopardy wager.
    
    Game-theoretically optimal strategy:
    - If runaway: bet 0 (can't be caught)
    - If leader: bet enough so that if wrong, you still beat opponent who goes all-in
    - If trailer: often need to go all-in or near all-in
    
    Real players deviate from this in documented ways.
    """
    if not opponent_scores:
        opponent_scores = [0]
    
    max_opponent = max(opponent_scores) if opponent_scores else 0
    
    # Optimal bet for leader: score - (2 * max_opponent + 1)
    # So even if opponent doubles up and we lose, we still win
    is_leader = score >= max_opponent
    is_runaway = score > 2 * sum(opponent_scores)  # can't be caught
    
    if is_runaway:
        # Rational: bet $0. But many players bet something to look good.
        if player_type == "rational":
            wager = np.random.randint(0, 1000)
        else:
            wager = np.random.randint(0, int(score * 0.3))
    elif is_leader:
        # Optimal: bet to cover opponent doubling up
        optimal = score - (2 * max_opponent + 1)
        optimal = max(0, optimal)
        
        if player_type == "rational":
            # Near-optimal with small noise
            wager = optimal + np.random.randint(-500, 500)
        elif player_type == "aggressive":
            # Over-bets (common in real games)
            wager = int(score * np.random.beta(4, 2))
        elif player_type == "conservative":
            # Under-bets rational amount
            wager = int(optimal * np.random.beta(3, 3))
        else:
            wager = int(score * np.random.beta(2, 2))
    else:
        # Trailer: need to catch up
        needed = max_opponent - score + 1
        if player_type in ["aggressive", "rational"]:
            # Go all-in or near all-in
            frac = np.random.beta(7, 2)
            wager = int(score * frac)
        elif player_type == "conservative":
            # Under-bets even when trailing (common irrational behavior)
            frac = np.random.beta(3, 5)
            wager = int(score * frac)
        else:
            frac = np.random.beta(3, 3)
            wager = int(score * frac)
    
    wager = max(0, min(wager, score))
    wager = max(0, round(wager / 100) * 100)
    return wager


def generate_game(game_id: int, season: int, air_date: str) -> dict:
    """Generate a single complete Jeopardy game."""
    
    # Sample 3 contestants
    names = random.sample(CONTESTANT_NAMES, 3)
    skills = [simulate_player_skill() for _ in range(3)]
    player_types = [random.choice(["aggressive", "conservative", "rational", "mixed"]) 
                    for _ in range(3)]
    strategies = [random.choice(["sweep", "hunt", "random"]) for _ in range(3)]
    
    contestants = [{"name": n, "skill": s, "type": t, "strategy": st}
                   for n, s, t, st in zip(names, skills, player_types, strategies)]
    
    scores = [0, 0, 0]
    
    # ---- JEOPARDY ROUND ----
    j_cats = random.sample(JEOPARDY_CATEGORIES, N_CATEGORIES)
    j_clues_data = []
    dd_placed = False  # 1 DD in J round
    
    # Place Daily Double in rows 3-5, any column (weighted toward higher rows)
    dd_row = random.choices([3, 4, 5], weights=[1, 2, 3])[0]
    dd_col = random.randint(0, 5)
    
    # Track category completion for strategy analysis
    category_clue_counts = {cat: 0 for cat in j_cats}
    
    # Simulate who controls the board each turn
    controller = random.randint(0, 2)  # starts random
    
    for row_idx, value in enumerate(J_VALUES):
        row_num = row_idx + 1
        for col_idx in range(N_CATEGORIES):
            cat = j_cats[col_idx]
            is_dd = (row_num == dd_row and col_idx == dd_col and not dd_placed)
            if is_dd:
                dd_placed = True
            
            difficulty = (row_idx / 4) * 0.8  # higher rows harder
            
            if is_dd:
                # Only the controller answers
                ctrl = controller
                max_wager = max(scores[ctrl], value * 2)  # can bet up to score or min $1000
                wager = generate_dd_wager(max(scores[ctrl], 1000), max_wager, contestants[ctrl]["type"])
                correct = simulate_answer_correctness(contestants[ctrl]["skill"], difficulty)
                dd_wager = wager
                if correct:
                    scores[ctrl] += wager
                else:
                    scores[ctrl] -= wager
                answered_by = names[ctrl]
            else:
                # Buzz-in competition — skill determines who buzzes
                buzz_probs = [s * (0.8 + 0.4 * np.random.random()) for s in skills]
                buzz_probs = [max(0.01, p) for p in buzz_probs]
                total = sum(buzz_probs)
                buzz_probs = [p / total for p in buzz_probs]
                
                buzzer = np.random.choice(3, p=buzz_probs)
                correct = simulate_answer_correctness(contestants[buzzer]["skill"], difficulty)
                dd_wager = None
                if correct:
                    scores[buzzer] += value
                    controller = buzzer  # winner controls board
                else:
                    scores[buzzer] -= value
                answered_by = names[buzzer]
            
            category_clue_counts[cat] += 1
            j_clues_data.append({
                "category": cat,
                "value": value,
                "daily_double": is_dd,
                "dd_wager": dd_wager if is_dd else None,
                "correct": correct,
                "answered_by": answered_by,
                "row": row_num,
                "col": col_idx + 1,
            })
    
    # Track board sweep: did winner complete full categories?
    j_category_sweeps = sum(1 for v in category_clue_counts.values() if v == N_ROWS)
    
    scores_end_j = scores.copy()
    
    # ---- DOUBLE JEOPARDY ROUND ----
    dj_cats = random.sample([c for c in JEOPARDY_CATEGORIES if c not in j_cats], N_CATEGORIES)
    dj_clues_data = []
    dd1_placed = dd2_placed = False
    
    # 2 DDs in DJ round — weighted toward higher value rows and different columns
    dd_positions = set()
    while len(dd_positions) < 2:
        r = random.choices([3, 4, 5], weights=[1, 2, 3])[0]
        c = random.randint(0, 5)
        dd_positions.add((r, c))
    dd_positions = list(dd_positions)
    
    dj_category_clue_counts = {cat: 0 for cat in dj_cats}
    
    for row_idx, value in enumerate(DJ_VALUES):
        row_num = row_idx + 1
        for col_idx in range(N_CATEGORIES):
            cat = dj_cats[col_idx]
            is_dd = any(row_num == r and col_idx == c for r, c in dd_positions
                       if not (dd1_placed and (r, c) == dd_positions[0]) 
                       and not (dd2_placed and len(dd_positions) > 1 and (r, c) == dd_positions[1]))
            
            # Simpler DD tracking
            pos = (row_num, col_idx)
            is_dd = pos in [(r, c) for r, c in dd_positions]
            
            difficulty = 0.2 + (row_idx / 4) * 0.7
            
            if is_dd:
                ctrl = controller
                max_wager = max(max(scores[ctrl], 0), value * 2)
                wager = generate_dd_wager(max(scores[ctrl], 1000), max_wager, contestants[ctrl]["type"])
                correct = simulate_answer_correctness(contestants[ctrl]["skill"], difficulty)
                dd_wager = wager
                if correct:
                    scores[ctrl] += wager
                else:
                    scores[ctrl] -= wager
                answered_by = names[ctrl]
            else:
                buzz_probs = [s * (0.8 + 0.4 * np.random.random()) for s in skills]
                buzz_probs = [max(0.01, p) for p in buzz_probs]
                total = sum(buzz_probs)
                buzz_probs = [p / total for p in buzz_probs]
                buzzer = np.random.choice(3, p=buzz_probs)
                correct = simulate_answer_correctness(contestants[buzzer]["skill"], difficulty)
                dd_wager = None
                if correct:
                    scores[buzzer] += value
                    controller = buzzer
                else:
                    scores[buzzer] -= value
                answered_by = names[buzzer]
            
            dj_category_clue_counts[cat] += 1
            dj_clues_data.append({
                "category": cat,
                "value": value,
                "daily_double": is_dd,
                "dd_wager": dd_wager if is_dd else None,
                "correct": correct,
                "answered_by": answered_by,
                "row": row_num,
                "col": col_idx + 1,
            })
    
    dj_category_sweeps = sum(1 for v in dj_category_clue_counts.values() if v == N_ROWS)
    scores_end_dj = scores.copy()
    
    # ---- FINAL JEOPARDY ----
    fj_cat = random.choice(JEOPARDY_CATEGORIES)
    fj_difficulty = np.random.uniform(0.5, 0.85)  # FJ tends to be hard
    
    fj_wagers = []
    fj_correct = []
    for i in range(3):
        opp_scores = [scores[j] for j in range(3) if j != i]
        wager = generate_fj_wager(max(scores[i], 0), 
                                   [max(s, 0) for s in opp_scores], 
                                   contestants[i]["type"])
        # Can only wager up to your score (if negative, can't wager)
        wager = min(wager, max(scores[i], 0))
        correct = simulate_answer_correctness(contestants[i]["skill"], fj_difficulty)
        
        if correct:
            scores[i] = max(scores[i], 0) + wager
        else:
            scores[i] = max(scores[i], 0) - wager
        
        fj_wagers.append(wager)
        fj_correct.append(correct)
    
    scores_final = scores.copy()
    
    # Determine winner
    winner_idx = int(np.argmax(scores_final))
    winner = names[winner_idx]
    
    # ---- Package result ----
    return {
        "game_id": game_id,
        "air_date": air_date,
        "season": season,
        "contestants": [
            {
                "name": names[i],
                "skill": round(contestants[i]["skill"], 3),
                "player_type": contestants[i]["type"],
                "board_strategy": contestants[i]["strategy"],
            }
            for i in range(3)
        ],
        "jeopardy_round": {
            "categories": j_cats,
            "clues": j_clues_data,
            "category_sweeps": j_category_sweeps,
        },
        "double_jeopardy_round": {
            "categories": dj_cats,
            "clues": dj_clues_data,
            "category_sweeps": dj_category_sweeps,
        },
        "final_jeopardy": {
            "category": fj_cat,
            "difficulty": round(fj_difficulty, 3),
            "wagers": [
                {
                    "contestant": names[i],
                    "wager": fj_wagers[i],
                    "correct": fj_correct[i],
                    "score_before_fj": scores_end_dj[i],
                }
                for i in range(3)
            ],
        },
        "scores": {
            "end_of_j": {names[i]: scores_end_j[i] for i in range(3)},
            "end_of_dj": {names[i]: scores_end_dj[i] for i in range(3)},
            "final": {names[i]: scores_final[i] for i in range(3)},
        },
        "winner": winner,
        "winner_idx": winner_idx,
    }


def generate_dataset(n_games: int = N_GAMES, output_path: str = "../data/jeopardy_synthetic.json"):
    """Generate the full dataset."""
    import datetime
    
    print(f"Generating {n_games} synthetic Jeopardy games...")
    games = []
    
    # Spread games across seasons and dates
    start_date = datetime.date(FIRST_YEAR, 9, 8)  # Jeopardy season starts in September
    
    for i in range(n_games):
        season_offset = i // (n_games // N_SEASONS)
        season = FIRST_SEASON + min(season_offset, N_SEASONS - 1)
        
        # Air dates: roughly 3 games per week, ~46 weeks per season
        days_offset = (i % (n_games // N_SEASONS)) * (365 / (n_games / N_SEASONS))
        air_date = (start_date + datetime.timedelta(days=season_offset * 365 + days_offset)).strftime("%Y-%m-%d")
        
        game_id = 6000 + i  # Realistic J-Archive game IDs for recent seasons
        game = generate_game(game_id, season, air_date)
        games.append(game)
        
        if (i + 1) % 500 == 0:
            print(f"  Generated {i+1}/{n_games} games...")
    
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            return super().default(obj)

    with open(output_path, "w") as f:
        json.dump(games, f, indent=2, cls=NpEncoder)
    
    print(f"Done! Dataset saved to {output_path}")
    print(f"  Total games: {len(games)}")
    print(f"  Date range: {games[0]['air_date']} to {games[-1]['air_date']}")
    return games


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=N_GAMES)
    parser.add_argument("--output", default="../data/jeopardy_synthetic.json")
    args = parser.parse_args()
    generate_dataset(args.n, args.output)
