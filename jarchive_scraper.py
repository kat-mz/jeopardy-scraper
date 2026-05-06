"""
J-Archive Scraper
=================
Scrapes game data from j-archive.com for Jeopardy! analysis.

Usage:
    python jarchive_scraper.py --seasons 1 40 --output ../data/jarchive_raw.json
    python jarchive_scraper.py --games 1000 5000 --output ../data/jarchive_raw.json

Output schema per game:
{
  "game_id": int,
  "air_date": str (YYYY-MM-DD),
  "season": int,
  "contestants": [{"name": str, "home": str}],
  "jeopardy_round": {
    "categories": [str x6],
    "clues": [{"category": str, "value": int, "answer": str, "question": str,
               "daily_double": bool, "dd_wager": int|null,
               "row": int, "col": int}]
  },
  "double_jeopardy_round": { ...same structure... },
  "final_jeopardy": {
    "category": str,
    "answer": str,
    "question": str,
    "wagers": [{"contestant": str, "wager": int, "correct": bool}]
  },
  "scores": {
    "end_of_j": {"contestant_name": int},
    "end_of_dj": {"contestant_name": int},
    "final": {"contestant_name": int}
  },
  "winner": str
}
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import argparse
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://j-archive.com"
HEADERS = {
    "User-Agent": "JeopardyResearchBot/1.0 (academic research; contact: your@email.com)"
}
DELAY = 2.0  # seconds between requests — be polite!


def get_soup(url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    for attempt in range(retries):
        try:
            time.sleep(DELAY)
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            log.warning(f"Attempt {attempt+1}/{retries} failed for {url}: {e}")
            time.sleep(DELAY * (attempt + 1))
    return None


def get_game_ids_for_season(season: int) -> list[int]:
    """Return all game IDs for a given season."""
    url = f"{BASE_URL}/showseason.php?season={season}"
    soup = get_soup(url)
    if not soup:
        return []
    ids = []
    for a in soup.select("td.left_column a[href*='showgame.php']"):
        m = re.search(r"game_id=(\d+)", a["href"])
        if m:
            ids.append(int(m.group(1)))
    log.info(f"Season {season}: found {len(ids)} games")
    return ids


def parse_score(text: str) -> int:
    """Parse a score string like '$12,400' or '-$800' into an integer."""
    text = text.strip().replace(",", "").replace("$", "")
    if not text or text in ["-", "--", "???", ""]:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def parse_game(game_id: int) -> Optional[dict]:
    """Scrape a single game page and return structured data."""
    url = f"{BASE_URL}/showgame.php?game_id={game_id}"
    soup = get_soup(url)
    if not soup:
        return None

    game = {"game_id": game_id, "url": url}

    # --- Air date & season ---
    title = soup.find("title")
    if title:
        m = re.search(r"aired (\d{4}-\d{2}-\d{2})", title.text)
        game["air_date"] = m.group(1) if m else None
        m2 = re.search(r"Season (\d+)", title.text)
        game["season"] = int(m2.group(1)) if m2 else None

    # --- Contestants ---
    contestants = []
    for p in soup.select("#contestants_table td.contestant"):
        name_tag = p.find("a")
        name = name_tag.text.strip() if name_tag else p.text.strip()
        contestants.append({"name": name})
    game["contestants"] = contestants

    # --- Parse a round (J!, DJ!, or FJ) ---
    def parse_round(round_id: str) -> dict:
        round_div = soup.find("div", id=round_id)
        if not round_div:
            return {}

        # Categories
        categories = [td.text.strip() for td in round_div.select("td.category_name")]

        # Clues
        clues = []
        for td in round_div.select("td.clue"):
            clue_text_div = td.find("td", class_="clue_text")
            if not clue_text_div:
                continue  # empty clue

            # Value
            value_td = td.find("td", class_=re.compile("clue_value"))
            value_text = value_td.text.strip() if value_td else ""
            daily_double = "DD" in value_text or "Daily Double" in value_text.lower()
            value_text_clean = re.sub(r"[^0-9]", "", value_text)
            value = int(value_text_clean) if value_text_clean else None

            # DD wager
            dd_wager = None
            if daily_double:
                m = re.search(r"\$([0-9,]+)", value_text)
                if m:
                    dd_wager = int(m.group(1).replace(",", ""))

            # Answer (the clue shown on board)
            answer = clue_text_div.text.strip()

            # Question (what contestant must say) — hidden in mouseover JS
            mouseover = td.get("onmouseover", "") or ""
            q_match = re.search(r'correct_response">(.*?)</em>', mouseover)
            question = q_match.group(1) if q_match else None

            # Grid position
            clue_id = clue_text_div.get("id", "")
            pos_match = re.search(r"clue_(\w+)_(\d+)_(\d+)", clue_id)
            row = int(pos_match.group(3)) if pos_match else None
            col = int(pos_match.group(2)) if pos_match else None

            # Category for this clue
            cat_idx = (col - 1) if col else None
            category = categories[cat_idx] if (cat_idx is not None and cat_idx < len(categories)) else None

            clues.append({
                "category": category,
                "value": value,
                "answer": answer,
                "question": question,
                "daily_double": daily_double,
                "dd_wager": dd_wager,
                "row": row,
                "col": col,
            })

        return {"categories": categories, "clues": clues}

    game["jeopardy_round"] = parse_round("jeopardy_round")
    game["double_jeopardy_round"] = parse_round("double_jeopardy_round")

    # --- Final Jeopardy ---
    fj_div = soup.find("div", id="final_jeopardy_round")
    final_jeopardy = {}
    if fj_div:
        cat = fj_div.find("td", class_="category_name")
        final_jeopardy["category"] = cat.text.strip() if cat else None
        clue_td = fj_div.find("td", class_="clue_text")
        final_jeopardy["answer"] = clue_td.text.strip() if clue_td else None

        # FJ wagers and correctness
        wagers = []
        for row in fj_div.select("tr"):
            tds = row.find_all("td")
            if len(tds) >= 3:
                name = tds[0].text.strip()
                wager_text = tds[1].text.strip()
                correct_text = tds[2].text.strip()
                if name and wager_text:
                    wager_val = parse_score(wager_text)
                    wagers.append({
                        "contestant": name,
                        "wager": wager_val,
                        "correct": "right" in correct_text.lower() or "✓" in correct_text
                    })
        final_jeopardy["wagers"] = wagers

    game["final_jeopardy"] = final_jeopardy

    # --- Scores ---
    scores = {"end_of_j": {}, "end_of_dj": {}, "final": {}}
    # Score tables appear at the bottom of each round
    score_tables = soup.select("table.score_table")
    for i, tbl in enumerate(score_tables):
        round_key = ["end_of_j", "end_of_dj", "final"][min(i, 2)]
        names = [td.text.strip() for td in tbl.select("td.score_player_nickname")]
        vals = [parse_score(td.text) for td in tbl.select("td.score_player_score")]
        scores[round_key] = dict(zip(names, vals))

    game["scores"] = scores

    # --- Winner ---
    winner_td = soup.find("td", class_="winner")
    game["winner"] = winner_td.text.strip() if winner_td else None

    return game


def scrape_seasons(seasons: list[int], output_path: str, max_games: int = None):
    """Scrape all games across given seasons."""
    all_games = []
    game_count = 0

    for season in seasons:
        game_ids = get_game_ids_for_season(season)
        for gid in game_ids:
            if max_games and game_count >= max_games:
                break
            log.info(f"Scraping game {gid} (season {season})")
            game = parse_game(gid)
            if game:
                all_games.append(game)
                game_count += 1
            # Save incrementally every 50 games
            if game_count % 50 == 0:
                with open(output_path, "w") as f:
                    json.dump(all_games, f, indent=2)
                log.info(f"Checkpoint: saved {game_count} games")

    with open(output_path, "w") as f:
        json.dump(all_games, f, indent=2)
    log.info(f"Done. Scraped {game_count} games → {output_path}")


def scrape_game_range(start_id: int, end_id: int, output_path: str):
    """Scrape games by ID range."""
    all_games = []
    for gid in range(start_id, end_id + 1):
        log.info(f"Scraping game {gid}")
        game = parse_game(gid)
        if game:
            all_games.append(game)
        if len(all_games) % 50 == 0 and all_games:
            with open(output_path, "w") as f:
                json.dump(all_games, f, indent=2)
    with open(output_path, "w") as f:
        json.dump(all_games, f, indent=2)
    log.info(f"Done. Scraped {len(all_games)} games → {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape J-Archive Jeopardy data")
    parser.add_argument("--seasons", nargs=2, type=int, metavar=("START", "END"),
                        help="Season range to scrape (e.g. --seasons 1 40)")
    parser.add_argument("--games", nargs=2, type=int, metavar=("START_ID", "END_ID"),
                        help="Game ID range (e.g. --games 1000 5000)")
    parser.add_argument("--output", default="../data/jarchive_raw.json",
                        help="Output JSON file path")
    parser.add_argument("--max", type=int, default=None,
                        help="Max number of games to scrape")
    args = parser.parse_args()

    if args.seasons:
        seasons = list(range(args.seasons[0], args.seasons[1] + 1))
        scrape_seasons(seasons, args.output, args.max)
    elif args.games:
        scrape_game_range(args.games[0], args.games[1], args.output)
    else:
        parser.print_help()
