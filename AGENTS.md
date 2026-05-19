# JobFinder — Agent Guide

## Essential Commands
- **Install deps**: `pip install -r requirements.txt`
- **Install Playwright browsers**: `playwright install chromium`
- **Download spaCy model**: `python -m spacy download en_core_web_sm`
- **Run CLI**: `python -m src.main analyze <cv.pdf>` or `python -m src.main search <cv.pdf>`
- **Run as package**: `ai-job-finder analyze <cv.pdf>`
- **Run migrations**: `alembic upgrade head`
- **Run tests**: `pytest`
- **Set up**: `cp .env.template .env` and fill in API keys

## Project Structure
```
ai-job-finder/
├── alembic/                 # Database migrations
├── config/                  # Settings + scraper_selectors.json
├── data/                    # SQLite DB, CV storage, cache
├── docs/                    # Documentation
├── src/
│   ├── main.py              # CLI entry point (6 commands)
│   ├── database.py          # 5 SQLAlchemy models
│   ├── auto_applier/        # Playwright form sub + CAPTCHA detection
│   ├── cv_processor/        # Parser, scorer, AI improver
│   ├── job_scraper/         # LinkedIn, Indeed, Glassdoor + engine
│   ├── matcher/             # Embedding-based matching
│   ├── notification/        # Rich console + email
│   └── utils/               # Exceptions, logging, cache, export, skills
├── tests/                   # Test suite
├── .env.template
├── requirements.txt
├── pyproject.toml           # Build config
└── AGENTS.md / MEMORY.md    # Agent knowledge base
```

## CLI Commands
- `analyze <cv>` — Parse, score, improve CV (--domain, --format, --output, --user)
- `search <cv>` — Scrape & match jobs (--query, --location, --top-k, --format, --output, --user)
- `apply` — Submit applications (--index, --all, --cv, --cover-letter, --user)
- `list` — Show saved applications (--status, --limit)
- `stats` — Summary statistics
- `profile [email]` — Manage user profiles (--name, --phone, --domain, --location)

## Key Architecture Changes Since Sprint 1
- ✅ Custom exception hierarchy (JobFinderError + 19 subclasses)
- ✅ Structured JSON logging (Rich console + file output)
- ✅ Database session context manager (session_scope)
- ✅ AI API caching (24h TTL, disk-based, SHA256 keys)
- ✅ Scraper retry logic (exponential backoff, 3 retries)
- ✅ Externalized selectors (config/scraper_selectors.json)
- ✅ CAPTCHA detection (reCAPTCHA, hCaptcha, Cloudflare)
- ✅ Alembic migrations (3 migration files, run_migrations())
- ✅ Skills taxonomy (118 skills, 8 categories, aliases + related)
- ✅ Job persistence + URL dedup (DB-level unique constraint)
- ✅ Rich progress indicators (bars + spinners)
- ✅ Glassdoor scraper (3rd plugin)
- ✅ Export engine (JSON + PDF via fpdf2)
- ✅ Multi-user support (UserProfile, --user flag, profile command)
- ✅ Code quality tooling (pyproject.toml, pre-commit, ruff config)
- ✅ CI/CD pipeline (GitHub Actions: lint, typecheck, test matrix, build, publish)
- ✅ PyPI packaging (entry point, MANIFEST.in, wheel/sdist)
- ✅ Comprehensive documentation (README, user guide, API ref, architecture guide)

## Important Constraints
- **NEVER auto-apply without user confirmation** (`CONFIRM_BEFORE_SUBMIT=True`)
- **LinkedIn scraping is fragile** — update selectors in `config/scraper_selectors.json`
- **Rate limiting**: scrapers have 2-5s delays — do not reduce
- **AI API caching**: 24h TTL — use `--no-cache` for fresh AI calls (not implemented yet)
- **No official LinkedIn API** — scraping is the only option
- **spaCy model required**: `python -m spacy download en_core_web_sm`
- **Playwright browsers required**: `playwright install chromium`
