# JobFinder — Agent Memory

> Persistent knowledge base for AI agents working on this codebase.
> Last updated: 2026-05-16

---

## 🚀 Quick Start for Agents

**What this is**: AI-powered career agent CLI that automates the entire job search pipeline — from CV analysis to auto-applying.

**One-line summary**: Parse a CV → find matching jobs via scraping → rank by embedding similarity → auto-apply with confirmation.

**Essential setup** (run once):
```bash
pip install -r requirements.txt
playwright install chromium
python -m spacy download en_core_web_sm
cp .env.template .env  # then fill in API keys
```

**Core commands**:
```bash
python -m src.main analyze <cv.pdf> --domain "data science"   # Parse + score + improve CV
python -m src.main search <cv.pdf> --location "NYC" --top-k 5  # Scrape + match jobs
python -m src.main apply --all --cover-letter "..."            # Auto-apply (with confirmation)
```

**Critical rules**:
- ⛔ NEVER reduce scraper rate-limiting delays (2-5s built-in)
- ⛔ NEVER disable `CONFIRM_BEFORE_SUBMIT` without explicit user request
- ⚠️ LinkedIn selectors are fragile — update `linkedin.py` if scraping breaks
- 💰 No AI API call caching — repeated runs on same CV cost money

---

## 📋 Project Overview

| Property | Value |
|----------|-------|
| **Name** | JobFinder |
| **Type** | AI-powered career agent CLI |
| **Language** | Python 3.10+ |
| **Size** | ~1300 LOC across 17 Python files |
| **Status** | Phase 1 (MVP) mostly complete |

### What It Does (5-Step Pipeline)

```
CV → Parse → Score → Improve → Search → Match → Apply → Notify
```

1. **CV Analysis** — Parse PDF/DOCX, score quality across 4 dimensions, rewrite sections with AI
2. **Job Discovery** — Scrape LinkedIn and Indeed for relevant positions
3. **Smart Matching** — Embedding-based cosine similarity ranking
4. **Auto-Apply** — Playwright headless browser form submission (with user confirmation)
5. **Notifications** — Rich console tables + optional Gmail SMTP email

---

## 🏗️ Project Structure

```
ai-job-finder/
├── config/
│   ├── __init__.py
│   └── settings.py              # Central config loaded from .env
├── data/
│   └── cvs/.gitkeep             # Uploaded CVs stored here
├── src/
│   ├── main.py                  # CLI entry point (click: analyze, search, apply)
│   ├── database.py              # SQLAlchemy models + SQLite engine
│   ├── cv_processor/
│   │   ├── parser.py            # PDF/DOCX → structured dict (regex + spaCy NER)
│   │   ├── scorer.py            # 4-dimension CV quality scoring
│   │   └── improver.py          # AI-powered CV section rewrites
│   ├── job_scraper/
│   │   ├── base.py              # Abstract BaseScraper + JobPosting dataclass
│   │   ├── engine.py            # search_all() + deduplicate()
│   │   ├── linkedin.py          # Playwright LinkedIn scraper
│   │   └── indeed.py            # Playwright Indeed scraper
│   ├── matcher/
│   │   └── engine.py            # sentence-transformers cosine similarity
│   ├── auto_applier/
│   │   └── applier.py           # Playwright form filler with confirmation
│   ├── notification/
│   │   ├── console_notifier.py  # Rich tables/panels
│   │   └── email_notifier.py    # Gmail SMTP notifications
│   └── utils/                   # ⚠️ Empty placeholder
├── tests/                       # ❌ Empty — no tests written yet
├── docs/                        # ❌ Empty — no documentation yet
├── .env.template                # Environment variable template
├── requirements.txt             # 40 dependencies
├── AGENTS.md                    # Agent quick-reference guide
├── PLAN.md                      # 3-phase implementation roadmap
└── PRD.md                       # Product requirements document
```

---

## 🛠️ Tech Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **CLI** | Click | Command-line interface |
| **CV Parsing** | PyPDF2, python-docx, pdfplumber, spaCy | Extract text + NER from CVs |
| **AI/NLP** | google-genai, openai, sentence-transformers | CV improvement + job matching |
| **Scraping** | Playwright, BeautifulSoup4 | Headless browser job scraping |
| **Storage** | SQLAlchemy + SQLite | Persistent data |
| **Migrations** | Alembic | Database schema migrations |
| **Terminal UI** | Rich | Formatted console output |
| **Validation** | Pydantic | Data validation |
| **Testing** | pytest, pytest-asyncio | Unit/integration tests |
| **Linting** | ruff, black, mypy | Code quality |

### Key Models/Embeddings
- **Embedding model**: `all-MiniLM-L6-v2` (sentence-transformers)
- **spaCy model**: `en_core_web_sm` (must be downloaded separately)
- **AI model**: `gemini-2.0-flash` (default), OpenAI as fallback

---

## 🗄️ Database Schema

**Engine**: SQLite via SQLAlchemy

### User
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| name | String | User's name |
| email | String | Contact email |
| raw_cv_path | String | Path to uploaded CV file |
| parsed_cv | JSON | Parsed CV data (skills, experience, etc.) |
| created_at | DateTime | Timestamp |
| updated_at | DateTime | Timestamp |

### JobPosting
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto-increment |
| source | String | "linkedin" or "indeed" |
| title | String | Job title |
| company | String | Company name |
| description | Text | Full job description |
| url | String | Job posting URL |
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
| status | String | "pending", "submitted", "accepted", "rejected" |
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

---

## ⚙️ Configuration

### Required Environment Variables
| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Google Gemini API (preferred AI provider) |
| `EMAIL_SENDER` | Gmail address for notifications |
| `EMAIL_PASSWORD` | Gmail app password |
| `EMAIL_RECEIVER` | Where to send notification emails |

### Optional (with defaults)
| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | Fallback AI provider |
| `AI_MODEL` | `gemini-2.0-flash` | Primary AI model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `MATCH_TOP_K` | `5` | Max jobs to return per search |
| `SIMILARITY_THRESHOLD` | `0.5` | Minimum match score |
| `CONFIRM_BEFORE_SUBMIT` | `True` | Require user confirmation before applying |
| `MAX_APPLICATIONS_PER_RUN` | `5` | Cap on auto-applications per run |
| `DATABASE_URL` | `sqlite:///data/ai-job-finder.db` | Database connection string |

### Setup Template
```bash
cp .env.template .env
# Edit .env with your API keys
```

---

## 🔄 Architecture Patterns

### 1. Pipeline Architecture
Sequential flow: `CV → Parse → Score → Improve → Search → Match → Apply → Notify`
Each stage is a separate module with clear input/output contracts.

### 2. Plugin Scrapers
```
BaseScraper (ABC)
├── LinkedInScraper
└── IndeedScraper
```
Each scraper implements the same interface. `engine.py` orchestrates `search_all()` and `deduplicate()`.

### 3. AI Fallback Chain
```
Gemini (preferred) → OpenAI (fallback)
```
If Gemini fails or is unavailable, the system falls back to OpenAI.

### 4. NLP-First Matching
Uses `sentence-transformers` to encode CV and job descriptions into embeddings, then ranks by cosine similarity. No keyword-based matching.

### 5. Safety-by-Default
- `CONFIRM_BEFORE_SUBMIT=True` — browser becomes visible for user to review before submission
- Rate limiting built into scrapers (2-5s delays)
- `MAX_APPLICATIONS_PER_RUN=5` — prevents runaway applications

### 6. Lazy Model Loading
Singleton pattern for expensive models:
- `SentenceTransformer` loaded once, reused across calls
- `spaCy` model loaded once, cached

### 7. Cross-Command Handoff
- `search` command writes results to `data/latest_matches.json`
- `apply` command reads from `data/latest_matches.json`
- This enables the pipeline: `search` → review → `apply`

---

## 📊 CV Scoring System

The scorer evaluates CVs across **4 dimensions** (0-100 each):

| Dimension | What It Measures |
|-----------|-----------------|
| `keyword_density` | Presence of domain-relevant keywords |
| `quantified_achievements` | Use of metrics/numbers in experience |
| `section_completeness` | Presence of key sections (summary, skills, experience, education) |
| `ats_compatibility` | ATS-friendly formatting (no images, standard sections) |

---

## 🚫 Known Gaps & Technical Debt

### ❌ Missing (Not Implemented)
- **No tests** — `tests/` directory is empty
- **Glassdoor scraper** — planned but not built
- **Alembic migrations** — in requirements but no migration files exist
- **Documentation** — `docs/` directory is empty
- **Utility functions** — `src/utils/` is an empty placeholder

### ⚠️ Fragile / Risky
- **LinkedIn DOM selectors** — break on UI changes; requires manual updates to `linkedin.py`
- **No AI API caching** — repeated runs on same CV incur API costs
- **No CAPTCHA detection** — auto-applier doesn't handle CAPTCHAs
- **Minimal rate limiting** — only basic 2-5s delays in scrapers

### 🧹 Cleanup Needed
- `selenium` + `webdriver-manager` in `requirements.txt` but unused (Playwright is used instead)
- Empty directories: `tests/`, `docs/`, `src/utils/`

---

## 📅 Development Phases

### ✅ Phase 1 — MVP (Current)
- [x] CLI tool with Click
- [x] CV parsing (PDF/DOCX)
- [x] CV scoring (4 dimensions)
- [x] CV improvement (AI rewrites)
- [x] Job scraping (LinkedIn + Indeed)
- [x] Embedding-based matching
- [x] Auto-apply with confirmation
- [x] Console + email notifications
- [ ] Tests
- [ ] Documentation

### 🔲 Phase 2 — Enhanced (Not Started)
- Web UI
- Real-time notifications
- Advanced matching algorithms
- Auto-apply improvements (CAPTCHA handling, better form detection)

### 🔲 Phase 3 — Marketplace (Not Started)
- Bidirectional matching
- Employer dashboard
- Analytics and reporting

---

## 🔑 Key Files Reference

| File | Purpose | Edit When |
|------|---------|-----------|
| `src/main.py` | CLI commands | Adding new commands |
| `src/database.py` | SQLAlchemy models | Changing DB schema |
| `config/settings.py` | Config from .env | Adding new config options |
| `src/cv_processor/parser.py` | CV text extraction | Improving parsing accuracy |
| `src/cv_processor/scorer.py` | CV quality scoring | Adjusting scoring criteria |
| `src/cv_processor/improver.py` | AI CV rewrites | Changing AI prompts/providers |
| `src/job_scraper/linkedin.py` | LinkedIn scraper | Fixing broken selectors |
| `src/job_scraper/indeed.py` | Indeed scraper | Fixing broken selectors |
| `src/job_scraper/engine.py` | Scraper orchestration | Adding new scrapers |
| `src/matcher/engine.py` | Job matching | Changing matching algorithm |
| `src/auto_applier/applier.py` | Form submission | Improving form detection |

---

## 🧪 Testing Strategy (When Implemented)

Recommended test priorities:
1. **CV parser** — test with various PDF/DOCX formats
2. **CV scorer** — verify scoring dimensions produce reasonable scores
3. **Matcher** — test cosine similarity with known inputs
4. **Scrapers** — mock Playwright responses (avoid real network calls)
5. **Auto-applier** — mock browser interactions

Use `pytest` + `pytest-asyncio` for async tests.

---

## 📝 Notes for Agents

### Before Making Changes
1. Read `AGENTS.md` for workflow conventions
2. Check if the file you're editing has existing tests
3. Verify `.env` is configured before running commands
4. Don't reduce scraper delays — they prevent rate limiting

### Common Pitfalls
- **Forgetting spaCy model**: Run `python -m spacy download en_core_web_sm` before first use
- **Missing Playwright browsers**: Run `playwright install chromium` after pip install
- **LinkedIn breaks frequently**: Selectors need periodic updates as LinkedIn changes their DOM
- **AI costs add up**: No caching means every `analyze` call hits the API

### Debugging Tips
- Set `CONFIRM_BEFORE_SUBMIT=True` to see the browser during apply
- Check `data/ai-job-finder.db` with any SQLite viewer for stored data
- Check `data/latest_matches.json` for search results between commands
- Rich console output is verbose — look for error panels in red
