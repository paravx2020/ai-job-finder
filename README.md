# JobFinder — AI-Powered Career Agent CLI

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**JobFinder** automates the entire job search pipeline — from CV analysis to auto-applying. Parse your CV, get AI-powered improvement suggestions, scrape job listings from LinkedIn/Indeed/Glassdoor, research companies, tailor your CV and cover letter for each role, track responses, and run autonomously 24/7 — all from the command line.

## Features

- **CV Parsing** — Extract structured data from PDF/DOCX files with spaCy NER and flexible heading matching
- **CV Scoring** — Evaluate quality across 4 dimensions (keywords, achievements, completeness, ATS)
- **AI Improvement** — Rewrite CV sections using Gemini 3.5 Flash via the google.genai SDK
- **Job Discovery** — Scrape LinkedIn (list-based, no sign-in), Indeed, and Glassdoor for positions
- **Smart Matching** — Semantic similarity ranking using sentence-transformers embeddings
- **Company Research** — Web search + AI summarization + red flag detection before applying
- **CV Tailoring** — Per-job CV generation optimized for each specific role
- **Cover Letter Generation** — 250-350 word letters referencing company intelligence
- **Auto-Apply** — Headless browser form submission with safety confirmation
- **Autonomous Daemon** — 24/7 mode or cron-triggered pipeline: parse/search/match/research/tailor/apply/report
- **Response Tracking** — Track interview/rejected/ghosted/offer outcomes with strategy optimization
- **Daily Reports** — HTML + JSON reports of all activity
- **Email Notifications** — Optional daily summary via SMTP
- **Multi-User** — Profile management and per-user data isolation
- **Export Reports** — Save results as JSON or PDF
- **Plugin Scrapers** — Extensible scraper architecture (add any job site)

## Quick Start

### Prerequisites
- Python 3.10+
- Playwright browsers (see below)
- spaCy model (see below)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/ai-job-finder.git
cd ai-job-finder

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser
playwright install chromium

# 4. Download spaCy model
python -m spacy download en_core_web_sm

# 5. Configure environment
cp .env.template .env
# Edit .env with GEMINI_API_KEY (get from https://aistudio.google.com/apikey)
```

### Basic Usage

```bash
# Analyze and improve your CV
python -m src.main analyze my_cv.pdf --domain "IT support"

# Search for matching jobs
python -m src.main search my_cv.pdf --location "New York" --top-k 10

# Profile management
python -m src.main profile user@example.com --name "Alice"

# List saved applications
python -m src.main list

# View statistics
python -m src.main stats

# Export results as PDF
python -m src.main analyze my_cv.pdf --format pdf --output report.pdf

# Apply to matched jobs
python -m src.main apply --all --cover-letter "I'm excited to apply..."

# Autonomous mode (dry-run first!)
python -m src.main daemon --once --dry-run

# Full autonomous mode
python -m src.main daemon --once

# Track application responses
python -m src.main track-response 1 interview

# View full report
python -m src.main report
```

## Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `analyze <cv>` | Parse, score, improve CV | `--domain`, `--format`, `--output`, `--user` |
| `search <cv>` | Scrape jobs, rank matches | `--query`, `--location`, `--top-k`, `--format`, `--output`, `--user` |
| `apply` | Submit applications | `--index`, `--all`, `--cv`, `--cover-letter`, `--user` |
| `list` | Show saved applications | `--status`, `--limit` |
| `stats` | Display summary statistics | — |
| `profile [email]` | Manage user profiles | `--name`, `--phone`, `--domain`, `--location` |
| `daemon` | Run autonomous loop | `--once`, `--dry-run` |
| `track-response <id> <status>` | Track outcomes | rejected/interview/ghosted/offer |
| `report` | Full activity report | — |
| `migrate` | Run DB migrations | — |

Global flags: `--verbose`/`-v`, `--quiet`/`-q`, `--db <path>`

## Architecture

```
                   ┌──────────────────────────────────────────────────┐
                   │               CLI (src/main.py)                  │
                   │  analyze · search · apply · daemon · track      │
                   │  list · stats · profile · report · migrate      │
                   └──────┬───────────────────────────┬───────────────┘
                          │                           │
              ┌───────────▼──────────┐    ┌───────────▼──────────────┐
              │    CV Processor      │    │     Job Scraper          │
              │  parser · scorer     │    │  LinkedIn · Indeed       │
              │  improver (AI)       │    │  Glassdoor · Engine      │
              └───────────┬──────────┘    └───────────┬──────────────┘
                          │                           │
              ┌───────────▼───────────────────────────▼──────────────┐
              │               Matcher (sentence-transformers)         │
              │           Embedding-based cosine similarity           │
              └───────────────────────┬───────────────────────────────┘
                                      │
              ┌───────────────────────▼───────────────────────────────┐
              │          Pre-Apply (company_research + tailoring)     │
              │  Web search → AI summary → red flag check            │
              │  CV tailoring → cover letter generation               │
              └───────────────────────┬───────────────────────────────┘
                                      │
              ┌───────────────────────▼───────────────────────────────┐
              │              Auto-Applier (Playwright)                │
              │         CAPTCHA detection · Form filling · Retry      │
              └───────────────────────┬───────────────────────────────┘
                                      │
              ┌───────────────────────▼───────────────────────────────┐
              │         Database (SQLite via SQLAlchemy)              │
              │   7 tables: User · UserProfile · JobPosting          │
              │   Application · CVImprovementLog · CompanyResearch    │
              │   ApplicationResult                                   │
              └───────────────────────────────────────────────────────┘
```

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **CLI** | Click |
| **CV Parsing** | PyPDF2, python-docx, spaCy |
| **AI/NLP** | Gemini 3.5 Flash (google.genai SDK), OpenAI (fallback), sentence-transformers |
| **Scraping** | Playwright (headless Chromium), BeautifulSoup4 |
| **Storage** | SQLAlchemy + SQLite, Alembic (migrations) |
| **Reports** | fpdf2 (PDF), JSON, HTML |
| **Terminal** | Rich (tables, progress bars, panels) |
| **Testing** | pytest, pytest-asyncio |
| **Code Quality** | ruff, black, mypy, pre-commit |

## Configuration

Copy `.env.template` to `.env` and set:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key (preferred) |
| `OPENAI_API_KEY` | No | — | Fallback AI provider |
| `AI_MODEL` | No | `gemini-3.5-flash` | Primary AI model |
| `DRY_RUN` | No | `false` | Enable dry-run mode |
| `CONFIRM_BEFORE_SUBMIT` | No | `true` | Require user confirmation before applying |
| `MAX_APPLICATIONS_PER_RUN` | No | `10` | Cap on auto-applications per run |
| `AUTO_APPLY_THRESHOLD` | No | `0.6` | Minimum match score for auto-apply |
| `DAEMON_SLEEP_HOURS` | No | `6` | Hours between daemon cycles |
| `EMAIL_SENDER` | No | — | Gmail address for notifications |
| `EMAIL_PASSWORD` | No | — | Gmail app password |
| `EMAIL_RECEIVER` | No | — | Notification recipient |

See `config/settings.py` for all 25+ configurable options and defaults.

## Project Structure

```
ai-job-finder/
├── alembic/                 # Database migrations
├── config/                  # Settings and scraper selectors
├── data/                    # SQLite DB, CV storage, cache, reports
├── docs/                    # Documentation
├── src/
│   ├── main.py              # CLI entry point (10 commands)
│   ├── database.py          # SQLAlchemy models (7 tables)
│   ├── daemon.py            # Autonomous agent loop
│   ├── tailoring.py         # Per-job CV + cover letter generation
│   ├── company_research.py  # Company intelligence + red flags
│   ├── optimization.py      # Response tracking + strategy opt.
│   ├── reporter.py          # HTML/text report generation
│   ├── auto_applier/        # Playwright form submission
│   ├── cv_processor/        # Parsing, scoring, improvement
│   ├── job_scraper/         # LinkedIn, Indeed, Glassdoor
│   ├── matcher/             # Embedding-based matching
│   ├── notification/        # Console + email output
│   └── utils/               # Cache, export, logging, skills, exceptions
├── tests/                   # Test suite
├── .env.template            # Environment template
├── requirements.txt         # Python dependencies
└── pyproject.toml           # Package configuration
```

## Important Notes

- **Scraping**: LinkedIn uses list-based extraction (no sign-in). Indeed/Glassdoor have Cloudflare detection and graceful degradation. Update selectors in `config/scraper_selectors.json`
- **Rate Limiting**: Built-in delays (2-5s) — do not reduce
- **AI SDK**: Uses `google.genai` (not deprecated `google.generativeai`)
- **AI Caching**: 24h TTL disk-based cache — re-running on same CV won't hit the API
- **Auto-Apply**: Requires user confirmation by default (`CONFIRM_BEFORE_SUBMIT=True`)
- **Dry-Run**: Always test with `daemon --once --dry-run` before live autonomous mode
- **No Official API**: LinkedIn/Indeed scraping is the only option without partnership

## License

MIT
