# JobFinder — AI-Powered Career Agent CLI

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**JobFinder** automates the entire job search pipeline — from CV analysis to auto-applying. Parse your CV, get AI-powered improvement suggestions, scrape job listings from LinkedIn, Indeed, and Glassdoor, rank them by match score, and submit applications — all from the command line.

## ✨ Features

- 📄 **CV Parsing** — Extract structured data from PDF/DOCX files with spaCy NER
- 📊 **CV Scoring** — Evaluate quality across 4 dimensions (keywords, achievements, completeness, ATS)
- 🧠 **AI Improvement** — Rewrite CV sections using Gemini (or OpenAI fallback)
- 🔍 **Job Discovery** — Scrape LinkedIn, Indeed, and Glassdoor for matching positions
- 🎯 **Smart Matching** — Semantic similarity ranking using sentence-transformers embeddings
- 🤖 **Auto-Apply** — Headless browser form submission with safety confirmation
- 📧 **Notifications** — Rich terminal output + optional email alerts via SMTP
- 👥 **Multi-User** — Profile management and per-user data isolation
- 📦 **Export Reports** — Save results as JSON or PDF
- 🧩 **Plugin System** — Extensible scraper architecture (add any job site)

## 🚀 Quick Start

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
# Edit .env with your API keys (GEMINI_API_KEY recommended)
```

### Basic Usage

```bash
# Analyze and improve your CV
python -m src.main analyze my_cv.pdf --domain "data science"

# Search for matching jobs
python -m src.main search my_cv.pdf --location "New York" --top-k 10

# List saved applications
python -m src.main list

# View statistics
python -m src.main stats

# Export results as PDF
python -m src.main analyze my_cv.pdf --format pdf --output report.pdf

# Manage user profiles
python -m src.main profile user@example.com --name "Alice"

# Apply to matched jobs
python -m src.main apply --all --cover-letter "I'm excited to apply..."
```

## 📖 Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `analyze <cv>` | Parse, score, improve CV | `--domain`, `--format`, `--output`, `--user` |
| `search <cv>` | Scrape jobs, rank matches | `--query`, `--location`, `--top-k`, `--format`, `--output`, `--user` |
| `apply` | Submit applications | `--index`, `--all`, `--cv`, `--cover-letter`, `--user` |
| `list` | Show saved applications | `--status`, `--limit` |
| `stats` | Display summary statistics | — |
| `profile [email]` | Manage user profiles | `--name`, `--phone`, `--domain`, `--location` |

Global flags: `--verbose`/`-v`, `--quiet`/`-q`, `--db <path>`

## 🏗️ Architecture

```
                   ┌──────────────────────────────────────────────┐
                   │              CLI (src/main.py)               │
                   │  analyze · search · apply · list · stats     │
                   └──────┬───────────────────────────┬───────────┘
                          │                           │
              ┌───────────▼──────────┐    ┌───────────▼──────────┐
              │    CV Processor      │    │     Job Scraper      │
              │  parser · scorer     │    │  LinkedIn · Indeed   │
              │  improver (AI)       │    │  Glassdoor · Engine  │
              └───────────┬──────────┘    └───────────┬──────────┘
                          │                           │
              ┌───────────▼───────────────────────────▼──────────┐
              │               Matcher (sentence-transformers)     │
              │           Embedding-based cosine similarity       │
              └───────────────────────┬───────────────────────────┘
                                      │
              ┌───────────────────────▼───────────────────────────┐
              │              Auto-Applier (Playwright)            │
              │         CAPTCHA detection · Form filling          │
              └───────────────────────┬───────────────────────────┘
                                      │
              ┌───────────────────────▼───────────────────────────┐
              │         Database (SQLite via SQLAlchemy)          │
              │    User · JobPosting · Application · Improvement  │
              └───────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Category | Technologies |
|----------|-------------|
| **CLI** | Click |
| **CV Parsing** | PyPDF2, python-docx, spaCy |
| **AI/NLP** | Gemini (google-generativeai), OpenAI, sentence-transformers |
| **Scraping** | Playwright (headless Chromium) |
| **Storage** | SQLAlchemy + SQLite, Alembic (migrations) |
| **Reports** | fpdf2 (PDF), JSON |
| **Terminal** | Rich (tables, progress bars) |
| **Testing** | pytest, pytest-asyncio |
| **Code Quality** | ruff, black, mypy, pre-commit |

## ⚙️ Configuration

Copy `.env.template` to `.env` and set:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key (preferred) |
| `OPENAI_API_KEY` | ❌ | — | Fallback AI provider |
| `EMAIL_SENDER` | ❌ | — | Gmail address for notifications |
| `EMAIL_PASSWORD` | ❌ | — | Gmail app password |
| `EMAIL_RECEIVER` | ❌ | — | Notification recipient |

See `config/settings.py` for all configurable options and defaults.

## 📁 Project Structure

```
ai-job-finder/
├── alembic/                 # Database migrations
├── config/                  # Settings and scraper selectors
├── data/                    # SQLite DB, CV storage, cache
├── docs/                    # Documentation
├── src/
│   ├── main.py              # CLI entry point
│   ├── database.py          # SQLAlchemy models
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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Install pre-commit hooks: `pre-commit install`
5. Make your changes
6. Run tests: `pytest`
7. Submit a pull request
> New PR workflow: include one of `major`, `minor`, or `patch` in your pull request title or description to auto-apply the matching semantic label.
## ⚠️ Important Notes

- **Scraping**: LinkedIn DOM changes frequently — update selectors in `config/scraper_selectors.json`
- **Rate Limiting**: Built-in delays (2-5s) — do not reduce
- **Auto-Apply**: Requires user confirmation by default (`CONFIRM_BEFORE_SUBMIT=True`)
- **AI Costs**: Caching is implemented (24h TTL) — re-running on same CV won't hit the API
- **No Official API**: LinkedIn/Indeed scraping is the only option without partnership

## 📄 License

MIT
