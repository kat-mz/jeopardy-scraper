# Jeopardy! Strategic Analysis: Game Theory & Wagering Behavior

A comprehensive data analysis project investigating strategic patterns, wagering behavior, and winning correlations in Jeopardy! using the J-Archive dataset.

## Project Overview

This project analyzes thousands of Jeopardy! games to uncover strategic insights through game theory and statistical analysis. The core research questions center on:

1. **Daily Double Wagering Behavior**: Does aggressive vs. conservative wagering correlate with game outcomes?
2. **Board Selection Patterns**: Do winners employ systematic category strategies (sweeping vs. jumping)?
3. **Final Jeopardy Rationality**: Do contestants approximate optimal game-theoretic wagers, and does this predict winning?
4. **Score Distributions & Game Outcomes**: What score thresholds and trajectories distinguish winners from losers?

## Research Goals

### Overarching Goals
1. **Statistical analysis of daily double wagering behavior** and correlation with winning
2. **Board-selection pattern analysis** testing whether winners tend to sweep categories or jump around

### Supporting Goals
3. Exploratory data analysis of score distributions, wager ranges, and game outcomes
4. Model Daily Double wagering as a game-theoretic decision problem
5. Analyze whether aggressive vs. conservative wagering correlates with winning
6. Test whether Final Jeopardy wagers approximate rational/optimal strategies

## Repository Structure

```
jeopardy-scraper/
├── jarchive_scraper.py          # Web scraper for J-Archive.com
├── 01_eda.py                     # Data cleaning & exploratory analysis
├── 02_analysis.py                # Statistical analysis & visualizations
├── requirements.txt              # Python dependencies
├── data/                         # Output directory for raw & processed data
│   ├── jarchive_raw.json        # Raw scraped game data
│   ├── games.csv                # Game-level aggregated data
│   ├── contestants.csv          # Per-contestant statistics
│   ├── daily_doubles.csv        # Daily Double wagers & outcomes
│   ├── final_jeopardy.csv       # Final Jeopardy wagers & analysis
│   └── clues.csv                # Clue-level board strategy data
└── figures/                      # Output directory for visualizations
    ├── 01_score_distributions.png
    ├── 02_daily_double_analysis.png
    ├── 03_final_jeopardy_analysis.png
    ├── 04_board_strategy_analysis.png
    ├── 05_game_theory_models.png
    ├── 06_hypothesis_summary.png
    └── 07_winner_profile.png
```

## Installation & Setup

### Requirements
- **Python 3.9+**
- **pip** (Python package manager)
- Internet connection (for scraping J-Archive)
- ~500MB disk space (for ~1000 games of data)

### Step 1: Clone the Repository
```bash
git clone https://github.com/kat-mz/jeopardy-scraper.git
cd jeopardy-scraper
```

### Step 2: Create Directories
```bash
mkdir -p data figures
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

Or manually install required packages:
```bash
pip install requests beautifulsoup4 pandas numpy matplotlib seaborn scipy scikit-learn
```

## Quick Start

### Option A: Full Pipeline (Scrape → Clean → Analyze)

#### 1. Scrape J-Archive Data
Scrape seasons 1–40 (or any range) from J-Archive:
```bash
python jarchive_scraper.py --seasons 1 40 --output data/jarchive_raw.json
```

Or scrape by game ID range:
```bash
python jarchive_scraper.py --games 1000 5000 --output data/jarchive_raw.json
```

**Expected output**: `data/jarchive_raw.json` (JSON file with ~1000+ games)

**Time estimate**: ~8–12 hours for 40 seasons (includes 2-second delays between requests to respect J-Archive servers)

#### 2. Clean & Explore Data
```bash
python 01_eda.py
```

**Input**: `data/jarchive_raw.json` (raw scraped data)

**Outputs**:
- `data/games.csv` — Game-level statistics
- `data/contestants.csv` — Per-contestant performance
- `data/daily_doubles.csv` — Daily Double analysis
- `data/final_jeopardy.csv` — Final Jeopardy wagers & rationality
- `data/clues.csv` — Board-level clue strategy

**Prints**: EDA summary statistics

#### 3. Run Statistical Analysis
```bash
python 02_analysis.py
```

**Input**: CSV files from step 2

**Outputs**: 7 visualization PNG files in `figures/`

**Prints**: Hypothesis test results with significance levels

### Option B: Quick Demo (Using Sample Data)
If you have limited time, you can manually create a small sample JSON file and proceed directly to step 2.

## Data Pipeline Details

### Scraper Output (`jarchive_raw.json`)

Each game record contains:
```json
{
  "game_id": 1234,
  "air_date": "2020-01-15",
  "season": 36,
  "contestants": [
    {"name": "Player A", "home": "City, State"}
  ],
  "jeopardy_round": {
    "categories": ["Category1", "Category2", ...],
    "clues": [
      {
        "category": "Category1",
        "value": 200,
        "answer": "The clue shown to players",
        "question": "What is the correct response",
        "daily_double": false,
        "dd_wager": null,
        "row": 1,
        "col": 1
      }
    ]
  },
  "double_jeopardy_round": { ...same structure... },
  "final_jeopardy": {
    "category": "Final Category",
    "answer": "The final clue",
    "wagers": [
      {"contestant": "Player A", "wager": 5000, "correct": true}
    ]
  },
  "scores": {
    "end_of_j": {"Player A": 5400},
    "end_of_dj": {"Player A": 12300},
    "final": {"Player A": 17300}
  },
  "winner": "Player A"
}
```

### Processed Data Files

#### `games.csv`
Game-level aggregated statistics:
- `game_id`, `air_date`, `season`, `winner`
- `winner_score_j`, `winner_score_dj`, `winner_score_final`
- `lead_entering_fj` (winner's lead over 2nd place)
- `is_runaway` (winner > 2× combined opponent score)
- `total_category_sweeps` (strategy metric)

#### `daily_doubles.csv`
Individual Daily Double observations:
- `game_id`, `round` (Jeopardy or Double Jeopardy)
- `player`, `score_before_dd`, `wager`, `pct_wagered`
- `is_aggressive` (wager > 50% of score)
- `correct`, `won_game`

#### `final_jeopardy.csv`
Final Jeopardy wager analysis:
- `contestant`, `score_before_fj`, `wager`, `pct_wagered`
- `is_leader`, `is_runaway`, `is_trailer`
- `max_opponent_score`, `optimal_leader_wager`, `needed_wager` (game theory)
- `correct`, `won`

#### `clues.csv`
Clue-level board strategy:
- `game_id`, `round`, `category`, `value`
- `row`, `col` (board position)
- `correct`, `answered_by`, `by_winner`

## Analysis & Visualization

### Figure 1: Score Distributions
- Winner score entering Final Jeopardy
- All-contestant score comparison (winners vs. losers)
- Final score earnings distribution
- Score trends by season
- Lead entering Final Jeopardy

### Figure 2: Daily Double Analysis
- DD wager distribution by player type
- Percent wagered vs. score (regression analysis)
- DD correct rate by player type
- Aggressive vs. conservative wagering impact on winning
- DD wager by board position

### Figure 3: Final Jeopardy Game Theory
- Leader actual wager vs. optimal wager (rationality test)
- Trailer coverage of needed wagers
- FJ wager % leaders vs. trailers
- Runaway leader wager patterns
- FJ correctness and winning probability

### Figure 4: Board Strategy
- Winning strategy distribution (sweep vs. hunt)
- Clue difficulty by row (winner advantage)
- Board position heatmap for winners
- Correct answers vs. DJ score (sweep effect)
- J Round to DJ Round score correlation

### Figure 5: Game Theory Models
- DD expected value by wager fraction
- Logistic regression: predictors of winning
- Win probability vs. lead entering Final Jeopardy
- Leader FJ wager deviation from optimal
- Skill vs. score correlation

### Figure 6: Hypothesis Test Summary
- Aggregated significance tests across all hypotheses
- Effect sizes and p-values
- Summary of key findings

### Figure 7: Winner Profile
- Player type distribution (winners vs. all)
- Skill distribution (winners vs. losers)
- Winner score trajectory across rounds
- Leader over-betting vs. under-betting → win rate

## Key Hypotheses Tested

| Hypothesis | Test | Finding |
|-----------|------|---------|
| **H1** | Aggressive DD wagering → higher win rate | Mann-Whitney U test |
| **H2** | Leader FJ wagers approximate optimal | Pearson correlation |
| **H3** | Trailers bet enough to win if correct | Coverage rate analysis |
| **H4** | Leaders wager % differs from trailers | Mann-Whitney U test |
| **H6** | FJ correctness → game winning | Chi-squared test |
| **H8** | Category sweeps correlate with score | Pearson correlation |
| **H9** | J Round score predicts DJ score | Pearson correlation |
| **H13** | Skill predicts DJ score | Pearson correlation |

## Computational Requirements

### Time Estimates
| Stage | Time | System |
|-------|------|--------|
| Scraping 40 seasons | 8–12 hours | Any (respects rate limits) |
| Scraping 500 games | 30–45 min | Any |
| Data cleaning (1000 games) | 5–10 sec | Any |
| Analysis & visualization (1000 games) | 30–60 sec | Any |

### Memory Requirements
- Scraper: ~50 MB
- Cleaned data (1000 games): ~100 MB
- Analysis: ~200 MB peak

**Recommended**: 2GB+ RAM (not a hard requirement)

## Running on Any Computer

This project is designed to run on **any system** with Python 3.9+:

- **macOS**: M1/M2/Intel, standard Python installation
- **Linux**: Any distribution, standard Python
- **Windows**: Windows 10+ with Python from python.org or Windows Store
- **Cloud**: AWS EC2, GCP, Azure, DigitalOcean, etc.

No special dependencies or hardware acceleration required. All computations are CPU-bound.

### Install Python
- **macOS/Linux**: `brew install python3` or use system package manager
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **Cloud**: Use pre-configured images or `apt install python3`

## Customization

### Change Scraping Range
```bash
# Scrape seasons 30–40
python jarchive_scraper.py --seasons 30 40 --output data/jarchive_raw.json

# Scrape first 100 games
python jarchive_scraper.py --games 1 100 --output data/jarchive_raw.json

# Limit total games
python jarchive_scraper.py --seasons 1 40 --output data/jarchive_raw.json --max 500
```

### Adjust Analysis
Modify `01_eda.py` and `02_analysis.py` to:
- Change output paths
- Filter by season range
- Modify visualization styles
- Add custom statistics

## Troubleshooting

### Scraper Issues
- **Connection timeout**: Increase `DELAY` in `jarchive_scraper.py` (default: 2.0 sec)
- **Missing clues**: Some games may have incomplete data on J-Archive; check `game_id` URL directly
- **Rate-limited**: The 2-second delay respects J-Archive; further slowing is needed for aggressive scraping

### Data Issues
- **Missing CSV columns**: Ensure you ran `01_eda.py` with complete `jarchive_raw.json`
- **Empty dataframes**: Check that at least 10 games were scraped successfully

### Visualization Issues
- **No figures generated**: Verify `figures/` directory exists and is writable

## Output Examples

### EDA Summary (from `01_eda.py`)
```
DATASET OVERVIEW
  Total games: 1,234
  Seasons: 1 – 40
  Date range: 2004-09-13 to 2023-12-29
  Total Daily Doubles: 3,702
  Total FJ observations: 3,702

SCORE DISTRIBUTIONS
  Avg winner score (entering FJ): $14,523
  Runaway game rate: 23.4%

DAILY DOUBLE
  Avg wager: $6,234
  Aggressive bets (>50% of score): 38.2%
  Correctness rate: 64.1%

FINAL JEOPARDY
  Correctness rate: 52.3%
  Leader wager (pct): 23.4%
  Trailer wager (pct): 68.9%
```

### Test Results (from `02_analysis.py`)
```
H1_dd_aggression_winrate: p_value=0.0234
  → Aggressive DD wagering significantly predicts winning

H2_leader_optimal_r: r=0.456, p=0.0001
  → Leaders' wagers weakly correlate with optimal (not perfectly rational)

H6_fj_correct_wins: χ²=892.5, p<0.0001
  → FJ correctness strongly predicts game winning
```

## File Descriptions

| File | Purpose | Input | Output |
|------|---------|-------|--------|
| `jarchive_scraper.py` | Web scraper | Command-line args | `jarchive_raw.json` |
| `01_eda.py` | Data cleaning & EDA | `jarchive_raw.json` | 5× CSV files, console output |
| `02_analysis.py` | Statistical analysis | 5× CSV files | 7× PNG figures, hypothesis results |

## Citation & Data Source

All data is from **J-Archive** (https://j-archive.com), a fan-maintained archive of Jeopardy! games.

**Citation for J-Archive**: J-Archive contributors, https://j-archive.com

**Jeopardy!** is a registered trademark of Sony Pictures Entertainment.

## License

This project is provided as-is for research and educational purposes. See any game data restrictions from J-Archive.

## Future Enhancements

- [ ] Final Jeopardy optimal wager calculator
- [ ] Daily Double strategy recommendations
- [ ] Category difficulty regression model
- [ ] Player-level skill inference from betting behavior
- [ ] Real-time game analysis tool
- [ ] Web dashboard for interactive exploration

## Contributing

Contributions welcome! Areas for improvement:
- Additional statistical tests
- Enhanced visualizations
- Performance optimizations
- Error handling refinements
- Documentation expansions

## Contact

For questions, issues, or suggestions, please open a GitHub issue.

---

**Last Updated**: 2026-05-06  
**Python Version**: 3.9+  
**Status**: Active
