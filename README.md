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
├── jarchive_scraper.py          # Web scraper for J-Archive.com (optimized)
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
- ~100MB disk space (for ~200 games of data)

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

## Quick Start — 2-5 Minute Pipeline

### Option A: Fastest (100 games, ~2-3 minutes)

#### 1. Scrape 100 Recent Games
```bash
python jarchive_scraper.py --games 6000 6100 --output data/jarchive_raw.json
```

#### 2. Clean & Explore
```bash
python 01_eda.py
```

#### 3. Generate Visualizations
```bash
python 02_analysis.py
```

**Total time: ~3-5 minutes** ⏱️

### Option B: Medium (Recent season, ~5 minutes)

```bash
# Scrape season 40 (~200 games)
python jarchive_scraper.py --seasons 40 40 --output data/jarchive_raw.json

# Clean & analyze
python 01_eda.py
python 02_analysis.py
```

**Total time: ~7-10 minutes**

### Option C: Full Dataset (Seasons 35-40, ~10-15 minutes)

```bash
# Scrape with optimizations
python jarchive_scraper.py --seasons 35 40 --output data/jarchive_raw.json \
  --delay 0.3 --threads 5

# Clean & analyze
python 01_eda.py
python 02_analysis.py
```

**Total time: ~15-20 minutes** (much faster than 8-12 hours!)

## Performance Optimization

### What Changed
✅ **Threaded scraping** (3-5 concurrent requests)  
✅ **Reduced delays** (0.5s → 0.3s between requests)  
✅ **Better rate limiting** (thread-safe implementation)  
✅ **Incremental saves** (every 25 games)  
✅ **Smart retries** (fewer retry attempts)

### Time Estimates

| Dataset | Games | Time (threads=3, delay=0.5) | Time (threads=5, delay=0.3) |
|---------|-------|----------------------------|---------------------------|
| 100 recent | 100 | ~2-3 min | ~1-2 min |
| Last season | 200 | ~5-7 min | ~3-5 min |
| Recent 3 seasons | 600 | ~15-20 min | ~8-12 min |
| All 40 seasons | 5000+ | ~2-3 hours | ~1-1.5 hours |

### Command Reference

```bash
# Fast scraping (aggressive settings)
python jarchive_scraper.py --seasons 35 40 --output data/jarchive_raw.json \
  --delay 0.3 --threads 5

# Conservative scraping (respectful of J-Archive)
python jarchive_scraper.py --seasons 35 40 --output data/jarchive_raw.json \
  --delay 1.0 --threads 2

# Custom: specific game range
python jarchive_scraper.py --games 5500 6500 --output data/jarchive_raw.json \
  --delay 0.5 --threads 3

# Limit total games
python jarchive_scraper.py --seasons 1 40 --output data/jarchive_raw.json \
  --max 500 --delay 0.3 --threads 5  # Only first 500 games
```

## Data Pipeline Details

### Scraper Output (`jarchive_raw.json`)

Each game record contains:
```json
{
  "game_id": 1234,
  "air_date": "2020-01-15",
  "season": 36,
  "contestants": [
    {"name": "Player A"}
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

#### `daily_doubles.csv`
Individual Daily Double observations:
- `game_id`, `round`, `wager`, `clue_row`, `clue_value`, `category`

#### `final_jeopardy.csv`
Final Jeopardy wager analysis:
- `contestant`, `score_before_fj`, `wager`, `pct_wagered`
- `is_leader`, `is_runaway`, `is_trailer`
- `max_opponent_score`, `optimal_leader_wager`, `needed_wager` (game theory)
- `correct`, `won`

#### `clues.csv`
Clue-level board strategy:
- `game_id`, `round`, `category`, `value`, `row`, `col`, `daily_double`, `winner`

## Analysis & Visualization

### Figure 1: Score Distributions
- Winner score entering Final Jeopardy
- All-contestant score comparison (winners vs. losers)
- Final score earnings distribution
- Score trends by season
- Lead entering Final Jeopardy

### Figure 2: Daily Double Analysis
- DD wager distribution
- Percent wagered vs. score (regression analysis)
- DD correct rate patterns
- Aggressive vs. conservative wagering impact on winning
- DD wager by board position

### Figure 3: Final Jeopardy Game Theory
- Leader actual wager vs. optimal wager (rationality test)
- Trailer coverage of needed wagers
- FJ wager % leaders vs. trailers
- Runaway leader wager patterns
- FJ correctness and winning probability

### Figure 4: Board Strategy
- Winning strategy distribution
- Clue difficulty by row (winner advantage)
- Board position heatmap for winners
- Correct answers vs. score (sweep effect)

### Figure 5: Game Theory Models
- DD expected value by wager fraction
- Logistic regression: predictors of winning
- Win probability vs. lead entering FJ
- Leader FJ wager deviation from optimal
- Skill vs. score correlation

### Figure 6: Hypothesis Test Summary
- Aggregated significance tests
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

## Running on Any Computer

This project is designed to run on **any system** with Python 3.9+:

- **macOS**: M1/M2/Intel, standard Python installation
- **Linux**: Any distribution, standard Python
- **Windows**: Windows 10+ with Python from python.org
- **Cloud**: AWS EC2, GCP, Azure, DigitalOcean, etc.

No special dependencies or hardware acceleration required.

### Install Python
- **macOS/Linux**: `brew install python3` or use system package manager
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **Cloud**: Use pre-configured images

## Customization

### Scraper Parameters

```bash
# Scrape with custom delay (0.3 = faster, 1.0 = slower/safer)
python jarchive_scraper.py --seasons 35 40 --delay 0.3

# Adjust thread count (3 = default, 5 = max parallelism)
python jarchive_scraper.py --seasons 35 40 --threads 5

# Combine: aggressive scraping
python jarchive_scraper.py --seasons 35 40 \
  --delay 0.3 --threads 5 --max 500
```

### Analysis

Modify `01_eda.py` and `02_analysis.py` to:
- Change output paths
- Filter by season range
- Modify visualization styles
- Add custom statistics

## Troubleshooting

### Scraper Issues
- **Connection timeout**: Increase `--delay` (e.g., `--delay 1.0`)
- **Rate-limited**: Reduce `--threads` (e.g., `--threads 2`)
- **Incomplete games**: Some games on J-Archive have missing data; script handles gracefully

### Data Issues
- **Missing CSV columns**: Ensure you ran `01_eda.py` with complete `jarchive_raw.json`
- **Empty dataframes**: Check that at least 10 games were scraped successfully

### Visualization Issues
- **No figures generated**: Verify `figures/` directory exists and is writable

## Output Examples

### EDA Summary (from `01_eda.py`)
```
DATASET OVERVIEW
  Total games: 234
  Seasons: 35 – 40
  Date range: 2018-09-24 to 2024-05-06
  Total Daily Doubles: 702
  Total FJ observations: 702
  Total clues: 16,848

SCORE DISTRIBUTIONS
  Avg winner score (entering FJ): $14,523
  Runaway game rate: 23.4%

DAILY DOUBLE
  Total DDs: 702
  Avg wager: $6,234
```

## File Descriptions

| File | Purpose | Input | Output |
|------|---------|-------|--------|
| `jarchive_scraper.py` | Web scraper | Command-line args | `jarchive_raw.json` |
| `01_eda.py` | Data cleaning & EDA | `jarchive_raw.json` | 5× CSV files |
| `02_analysis.py` | Statistical analysis | 5× CSV files | 7× PNG figures |

## Citation & Data Source

All data is from **J-Archive** (https://j-archive.com), a fan-maintained archive of Jeopardy! games.

**Citation for J-Archive**: J-Archive contributors, https://j-archive.com

**Jeopardy!** is a registered trademark of Sony Pictures Entertainment.

## License

This project is provided as-is for research and educational purposes.

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
**Typical Execution Time**: 2-5 minutes (100 games) to 15-20 minutes (600 games)
