# JobFinder — Agent Memory

> Persistent knowledge base for AI agents working on this codebase.
> Last updated: 2026-05-27

---

## Quick Start for Agents

**What this is**: AI-powered career agent CLI that automates the entire job search pipeline — from CV analysis to auto-applying, with autonomous daemon mode.

**One-line summary**: Parse a CV → improve with AI → find matching jobs via scraping → rank by embedding similarity → research companies → tailor CV/cover letter → auto-apply → track responses.

**Essential setup** (run once):
```bash
pip install -r requirements.txt
playwright install chromium
python -m spacy download en_core_web_sm
cp .env.template .env  # Set GEMINI_API_KEY
```

**Core commands**:
```bash
python -m src.main analyze <cv.pdf> --domain "IT support"    # Parse + score + improve CV
python -m src.main search <cv.pdf> --location "NYC" --top-k 5 # Scrape + match jobs
python -m src.main daemon --once --dry-run                    # Pipeline preview
```

**Critical rules**:
- NEVER reduce scraper rate-limiting delays (2-5s built-in)
- NEVER disable CONFIRM_BEFORE_SUBMIT without explicit user request
- LinkedIn selectors are fragile — uses list-based extraction (no sign-in)
- LinkedIn scraper works WITHOUT authentication now

---

## Project Overview

| Property | Value |
|----------|-------|
| **Name** | JobFinder |
| **Type** | AI-powered career agent CLI |
| **Language** | Python 3.10+ |
| **Location** | ~/Projects/ai-job-finder (WSL) |
| **Status** | Phase 1+2 partially complete |

### What It Does (9-Step Pipeline)

```
CV → Parse → Score → Improve → Search → Match → Research → Tailor → Apply → Track
```

1. **CV Analysis** — Parse PDF/DOCX, score quality across 4 dimensions, rewrite with AI
2. **Job Discovery** — Scrape LinkedIn, Indeed, Glassdoor; blocked page detection for Indeed/Glassdoor (Cloudflare)
3. **Smart Matching** — Embedding-based cosine similarity (all-MiniLM-L6-v2)
4. **Company Research** — Web search + AI summarization + red flag detection
5. **CV Tailoring** — Per-job CV rewrite matching specific requirements
6. **Cover Letter Generation** — 250-350 word letters referencing company research
7. **Auto-Apply** — Playwright headless browser form submission
8. **Notifications** — Rich terminal + optional Gmail SMTP email
9. **Response Tracking** — Interview/rejected/ghosted tracking with strategy optimization

---

## Project Structure

```
ai-job-finder/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Central config loaded from .env
│   └── scraper_selectors.json   # CSS selectors for LinkedIn, Indeed, Glassdoor
├── data/
│   ├── cvs/                     # Uploaded CVs
│   ├── reports/                 # HTML + JSON daily reports
│   ├── cache/                   # AI API response cache (24h TTL)
│   └── tailored_cvs/            # Per-job tailored CVs
├── src/
│   ├── main.py                  # CLI entry point (10 commands via Click)
│   ├── database.py              # SQLAlchemy models (7 tables) + SQLite engine
│   ├── daemon.py                # Autonomous agent loop
│   ├── tailoring.py             # Per-role CV + cover letter generation
│   ├── company_research.py      # Company intelligence + red flag detection
│   ├── optimization.py          # Response tracking + CV strategy analysis
│   ├── reporter.py              # HTML + JSON report generation
│   ├── cv_processor/
│   │   ├── parser.py            # PDF/DOCX → structured dict (regex + spaCy NER)
│   │   ├── scorer.py            # 4-dimension CV quality scoring
│   │   └── improver.py          # AI-powered CV section rewrites (google.genai SDK)
│   ├── job_scraper/
│   │   ├── base.py              # Abstract BaseScraper + JobPosting dataclass
│   │   ├── engine.py            # search_all() + deduplicate()
│   │   ├── linkedin.py          # Playwright LinkedIn scraper (list-based, no sign-in)
│   │   ├── indeed.py            # Playwright Indeed scraper (with Cloudflare detection)
│   │   └── glassdoor.py         # Playwright Glassdoor scraper (with Cloudflare detection)
│   ├── matcher/
│   │   └── engine.py            # sentence-transformers cosine similarity
│   ├── auto_applier/
│   │   └── applier.py           # Playwright form filler with confirmation
│   ├── notification/
│   │   ├── console_notifier.py  # Rich tables/panels
│   │   └── email_notifier.py    # Gmail SMTP notifications
│   └── utils/
│       ├── exceptions.py        # JobFinderError + 19 subclasses
│       ├── logging.py           # Structured JSON + Rich console logging
│       ├── cache.py             # AI API response cache (disk-based, SHA256)
│       ├── export.py            # JSON + PDF export via fpdf2
│       └── skills.py            # Skills taxonomy loader (cached, 140+ skills)
├── tests/                       # Test suite
├── docs/                        # Documentation
├── alembic/                     # Database migrations
├── .env.template
├── requirements.txt
├── pyproject.toml
├── AGENTS.md / MEMORY.md / PRD.md / PLAN.md
└── goal-autonomous-upgrade.md   # Original upgrade prompt
```

---

## Tech Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **CLI** | Click | Command-line interface |
| **CV Parsing** | PyPDF2, python-docx, pdfplumber, spaCy | Extract text + NER from CVs |
| **AI/NLP** | google.genai, openai, sentence-transformers | CV improvement + job matching |
| **Scraping** | Playwright, BeautifulSoup4 | Headless browser job scraping |
| **Storage** | SQLAlchemy + SQLite | Persistent data |
| **Migrations** | Alembic | Database schema migrations |
| **Terminal UI** | Rich | Formatted console output |
| **Testing** | pytest, pytest-asyncio | Unit/integration tests |
| **Linting** | ruff, black, mypy | Code quality |

### Key Models
- **Embedding model**: `all-MiniLM-L6-v2` (sentence-transformers, ~80MB)
- **spaCy model**: `en_core_web_sm` (must be downloaded separately)
- **AI model**: `gemini-3.5-flash` (default, via google.genai SDK)

---

## Database Schema (7 tables)

**Engine**: SQLite via SQLAlchemy

### User
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| name | String | User's name |
| email | String | Contact email (UNIQUE) |
| raw_cv_path | String | Path to uploaded CV file |
| parsed_cv | JSON | Parsed CV data (skills, experience, etc.) |
| created_at | DateTime | Timestamp |
| updated_at | DateTime | Timestamp |

### UserProfile
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| email | String | Unique identifier |
| name | String | Display name |
| phone | String | Phone for applications |
| domain | String | Target job domain |
| location | String | Preferred location |

### JobPosting
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| source | String | "linkedin" or "indeed" or "glassdoor" |
| title | String | Job title |
| company | String | Company name |
| description | Text | Full job description |
| url | String | Job posting URL (UNIQUE) |
| salary | String | Salary range (if available) |
| location | String | Job location |
| posted_date | Date | When posted |
| created_at | DateTime | Timestamp |

### Application
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| user_id | Integer (FK → User) | Who applied |
| job_id | Integer (FK → JobPosting) | Which job |
| status | String | pending/submitted/accepted/rejected |
| match_score | Float | Cosine similarity score |
| match_reason | Text | Why this job matched |
| applied_at | DateTime | When submitted |
| response | Text | Application response |

### CVImprovementLog
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| user_id | Integer (FK → User) | Whose CV |
| section | String | Which section was improved |
| original_text | Text | Before AI rewrite |
| improved_text | Text | After AI rewrite |
| model_used | String | Which AI model was used |
| created_at | DateTime | Timestamp |

### CompanyResearch
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| application_id | Integer (FK → Application) | Which application |
| company_name | String | Company researched |
| summary_brief | Text | AI-generated company intelligence |
| sources | JSON | Web search results (urls, titles, snippets) |
| red_flags | JSON | Red flag keywords detected |
| created_at | DateTime | Timestamp |

### ApplicationResult
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| application_id | Integer (FK → Application) | Which application |
| cv_path | String | Path to tailored CV used |
| cover_letter | Text | Cover letter text |
| company_research_id | Integer (FK → CompanyResearch) | Research context |
| tailored_version | String | CV version identifier |
| status | String | submitted/rejected/interview/ghosted/offer |
| follow_up_date | DateTime | When to follow up |
| notes | Text | Additional context |
| created_at | DateTime | Timestamp |

---

## Configuration

### Required Environment Variables
| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Google Gemini API (preferred AI provider) |

### Optional (with defaults)
| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | Fallback AI provider |
| `AI_MODEL` | `gemini-3.5-flash` | Primary AI model (via google.genai SDK) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `MATCH_TOP_K` | `5` | Max jobs to return per search |
| `SIMILARITY_THRESHOLD` | `0.5` | Minimum match score |
| `CONFIRM_BEFORE_SUBMIT` | `True` | Require user confirmation before applying |
| `MAX_APPLICATIONS_PER_RUN` | `10` | Cap on auto-applications per run |
| `DRY_RUN` | `false` | Enable dry-run mode (no actual submission) |
| `AUTO_APPLY_THRESHOLD` | `0.6` | Minimum match score for auto-apply |
| `APPLY_RATE_LIMIT_DELAY` | `3` | Seconds between submissions |
| `APPLY_MAX_RETRIES` | `2` | Retry attempts on failure |
| `DAEMON_SLEEP_HOURS` | `6` | Hours between daemon cycles |
| `COMPANY_RESEARCH_ENABLED` | `true` | Enable company intelligence step |
| `COMPANY_RED_FLAG_KEYWORDS` | `lawsuit,layoff,class action,toxic,hostile work` | Red flag detection list |
| `TRACK_OPTIMIZATION_ENABLED` | `true` | Enable response tracking + analysis |
| `FOLLOW_UP_GHOSTED_AFTER_DAYS` | `14` | Days before marking as ghosted |
| `EMAIL_DAILY_SUMMARY` | `true` | Send daily email report |
| `EMAIL_SUMMARY_TIME` | `08:00` | When to send daily summary |
| `EMAIL_SENDER` | — | Gmail address for notifications |
| `EMAIL_PASSWORD` | — | Gmail app password |
| `EMAIL_RECEIVER` | — | Notification recipient |
| `DATABASE_URL` | `sqlite:///data/ai-job-finder.db` | Database connection string |

### Setup
```bash
cp .env.template .env
# Edit .env with your API keys
```

---

## Architecture Patterns

### 1. Pipeline Architecture
Sequential flow: `CV → Parse → Score → Improve → Search → Match → Research → Tailor → Apply → Track`
Each stage is a separate module with clear input/output contracts.

### 2. Plugin Scrapers
```
BaseScraper (ABC)
├── LinkedInScraper    (list-based, no sign-in needed)
├── IndeedScraper      (blocked page detection for Cloudflare)
└── GlassdoorScraper   (blocked page detection for Cloudflare)
```
Engine orchestrates `search_all()` and `deduplicate()` via DB-level URL unique constraint.

### 3. AI Provider Chain
```
google.genai (preferred, default) → openai (fallback)
```
Both use the same `AI_MODEL` env var. New SDK uses `genai.Client(api_key=...)` pattern.

### 4. NLP-First Matching
Uses `sentence-transformers` to encode CV and job descriptions into embeddings, then ranks by cosine similarity. No keyword-based matching.

### 5. Safety-by-Default
- `CONFIRM_BEFORE_SUBMIT=True` in interactive mode
- `DRY_RUN=true` for testing
- Rate limiting built into scrapers (2-5s delays)
- `MAX_APPLICATIONS_PER_RUN=10` — prevents runaway applications

### 6. Lazy Model Loading
- `SentenceTransformer` loaded once, reused across calls
- `spaCy` model loaded once, cached
- Skills taxonomy loaded once, cached in memory (`_taxonomy_cache`)

### 7. Cross-Command Handoff
- `search` command writes results to `data/latest_matches.json`
- `apply` command reads from `data/latest_matches.json`
- Enables the pipeline: `search` → review → `apply`

### 8. Autonomous Daemon
- Daemon cycles: parse → search → match → research → tailor → generate cover letter → apply → report → sleep
- Cron mode (`--once`) for system scheduler integration
- Dry-run (`--dry-run`) for pipeline verification without side effects

---

## CV Scoring System

The scorer evaluates CVs across **4 dimensions** (0-100 each):

| Dimension | What It Measures |
|-----------|-----------------|
| `keyword_density` | Presence of domain-relevant keywords (matched against skills taxonomy) |
| `quantified_achievements` | Use of metrics/numbers in experience |
| `section_completeness` | Presence of key sections (summary, skills, experience, education) |
| `ats_compatibility` | ATS-friendly formatting (no images, standard sections) |

### Parsing Improvements
- Flexible heading matching: detects UPPERCASE, Title Case, and lowercase headers
- Word-boundary regex for skill extraction eliminates false positives
- 140+ skills in taxonomy across 8 categories with aliases and related skills

---

## Known Gaps & Technical Debt

### Missing (Not Implemented)
- **Web UI** — Phase 2, not started
- **PostgreSQL migration** — Phase 2, not started
- **Official LinkedIn API** — requires partnership
- **Parallel daemon mode** — currently single-threaded per cycle
- **AI response streaming** — not used in CLI

### Fragile / Risky
- **LinkedIn DOM selectors** — break on UI changes; uses list-based extraction which is more stable than card-based
- **Indeed/Glassdoor** — frequently Cloudflare-blocked; scrapers degrade gracefully with detection
- **Scraper selectors** stored in `config/scraper_selectors.json` — update when sites change
- **PDF parsing** — some PDF formats may not extract cleanly

### Cleanup
- `selenium` + `webdriver-manager` in `requirements.txt` but unused (Playwright is used instead)
- `google-generativeai` in `requirements.txt` but deprecated (google-genai is used instead)

---

## Development Phases

### Phase 1 — MVP (Complete)
- [x] CLI tool with Click
- [x] CV parsing (PDF/DOCX) with flexible heading matching
- [x] CV scoring (4 dimensions)
- [x] CV improvement (AI rewrites via google.genai SDK)
- [x] Job scraping (LinkedIn + Indeed + Glassdoor with blocked page detection)
- [x] Embedding-based matching
- [x] Auto-apply with confirmation
- [x] Console + email notifications
- [x] Database migrations (Alembic)
- [x] Skills taxonomy (140+ skills, 8 categories)
- [x] Multi-user support
- [x] Anonymous user mode
- [x] PyPI packaging
- [x] CI/CD pipeline
- [x] Documentation

### Phase 2 — Enhanced (Partially Complete)
- [x] Autonomous daemon mode (24/7 auto-apply)
- [x] Per-job CV tailoring
- [x] Cover letter generation
- [x] Company intelligence research
- [x] Red flag detection
- [x] Response tracking + ghosted detection
- [x] CV strategy optimization
- [x] Daily reports (HTML + JSON)
- [x] Email daily summary
- [ ] Web UI
- [ ] PostgreSQL migration
- [ ] Interview prep generator
- [ ] Salary scraping

### Phase 3 — Marketplace (Not Started)
- [ ] Employer portal
- [ ] Bidirectional matching
- [ ] Interview scheduler
- [ ] Analytics dashboard

---

## Key Files Reference

| File | Purpose | Edit When |
|------|---------|-----------|
| `src/main.py` | CLI commands (10 total) | Adding new commands |
| `src/database.py` | SQLAlchemy models (7 tables) | Changing DB schema |
| `config/settings.py` | Config from .env | Adding new config options |
| `src/cv_processor/parser.py` | CV text extraction | Improving parsing accuracy |
| `src/cv_processor/scorer.py` | CV quality scoring | Adjusting scoring criteria |
| `src/cv_processor/improver.py` | AI CV rewrites | Changing AI prompts/providers (uses google.genai) |
| `src/job_scraper/linkedin.py` | LinkedIn scraper | Fixing broken selectors |
| `src/job_scraper/indeed.py` | Indeed scraper | Fixing broken selectors |
| `src/job_scraper/glassdoor.py` | Glassdoor scraper | Fixing broken selectors |
| `src/job_scraper/engine.py` | Scraper orchestration | Adding new scrapers |
| `src/matcher/engine.py` | Job matching | Changing matching algorithm |
| `src/auto_applier/applier.py` | Form submission | Improving form detection |
| `src/daemon.py` | Autonomous loop | Changing pipeline flow |
| `src/tailoring.py` | CV/cover letter generation | Changing per-job tailoring logic |
| `src/company_research.py` | Company intelligence | Adding new research sources |
| `src/optimization.py` | Response tracking | Adding optimization strategies |
| `src/reporter.py` | Report generation | Changing report format |
| `config/scraper_selectors.json` | CSS selectors for all sites | Updating on DOM changes |
| `data/skills_taxonomy.json` | Skills database | Adding new skills |
| `.env.template` | Environment variable template | Adding new config vars |

---

## Notes for Agents

### Before Making Changes
1. Read `AGENTS.md` for workflow conventions
2. Check if the file you're editing has existing tests
3. Verify `.env` is configured before running commands
4. Don't reduce scraper delays — they prevent rate limiting
5. The AI SDK is `google.genai` (not the deprecated `google.generativeai`)

### Common Pitfalls
- **Forgetting spaCy model**: Run `python -m spacy download en_core_web_sm` before first use
- **Missing Playwright browsers**: Run `playwright install chromium` after pip install
- **LinkedIn breaks frequently**: Uses list-based extraction (`.jobs-search__results-list`) — more stable than card selectors
- **Indeed/Glassdoor often blocked**: Scrapers have graceful degradation — check `scraper_selectors.json` if they return 0 jobs
- **AI model**: Set `AI_MODEL` in `.env` (default: gemini-3.5-flash)

### Debugging Tips
- Set `CONFIRM_BEFORE_SUBMIT=True` to see the browser during apply
- Set `DRY_RUN=true` to test without actual submissions
- Check `data/ai-job-finder.db` with any SQLite viewer
- Check `data/reports/` for daily HTML reports
- Check `data/latest_matches.json` for search results between commands
- Rich console output is verbose — look for error panels in red
- Use `python -m src.main daemon --once --dry-run` to preview the full pipeline
