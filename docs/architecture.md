# JobFinder Architecture

## System Overview

JobFinder follows a pipeline architecture where data flows through sequential processing stages:

```
CV File → Parser → Scorer → AI Improver → Job Scraper → Matcher
  → Company Research → Red Flag Check → CV Tailoring
  → Cover Letter Generation → Auto-Applier → Notifications
  → Response Tracking → Reports
```

## Module Responsibilities

### CLI Layer (`src/main.py`)
- Click-based command interface (10 commands)
- Argument parsing, validation, and dispatch
- Progress indication via Rich
- Export handling (JSON/PDF)
- Cross-command handoff via `data/latest_matches.json`

### CV Processor (`src/cv_processor/`)
- **Parser**: Extracts text from PDF/DOCX, identifies sections via flexible regex (handles UPPERCASE headers), extracts skills via taxonomy lookup with word-boundary matching, extracts entities via spaCy NER
- **Scorer**: 4-dimension quality evaluation (keyword_density, quantified_achievements, section_completeness, ats_compatibility)
- **Improver**: AI-powered section rewriting using google.genai SDK (Gemini 3.5 Flash by default, OpenAI fallback)

### Job Scraper (`src/job_scraper/`)
- Plugin architecture via `BaseScraper` ABC (search + source_name interface)
- Three implementations: LinkedIn (list-based, no sign-in), Indeed (Cloudflare detection), Glassdoor (Cloudflare detection)
- Externalized CSS selectors in `config/scraper_selectors.json`
- Retry logic with exponential backoff (3 retries)
- In-memory + DB-level deduplication (URL unique constraint)

### Matcher (`src/matcher/`)
- Uses `sentence-transformers/all-MiniLM-L6-v2` for embeddings
- Cosine similarity between CV profile and job descriptions
- Threshold-based filtering (default: 0.5, auto-apply: 0.6)
- Configurable top-K results

### Company Research (`src/company_research.py`)
- DuckDuckGo HTML web search (no API key required)
- AI-powered summarization into 100-200 word intelligence brief
- Red flag detection via configurable keyword list (lawsuit, layoff, toxic, etc.)
- Graceful fallback when web search or AI is unavailable

### Tailoring (`src/tailoring.py`)
- Structured requirement extraction from job descriptions via AI
- Per-job CV rewriting (reorder experience, emphasize matching skills, insert keywords)
- Cover letter generation (250-350 words, references company research)
- No skill fabrication — only highlights existing experience

### Auto-Applier (`src/auto_applier/`)
- Playwright headless browser automation
- CAPTCHA detection (reCAPTCHA, hCaptcha, Cloudflare) before submission
- Safety confirmation gate (CONFIRM_BEFORE_SUBMIT)
- Retry logic with exponential backoff, iframe awareness
- Per-site success/failure tracking
- Result logging to database

### Daemon (`src/daemon.py`)
- Autonomous pipeline loop: parse → search → match → research → tailor → apply → report
- Three modes: continuous (6h sleep), one-shot (cron-friendly), dry-run (verification)
- 10-application cap per cycle, 0.6 match threshold

### Optimization (`src/optimization.py`)
- Application outcome tracking (rejected, interview, ghosted, offer)
- Auto-ghosted detection after configurable days (default: 14)
- CV version performance analysis by callback rate
- Follow-up suggestions for ghosted applications

### Reporter (`src/reporter.py`)
- HTML report with styled tables and summaries
- JSON structured report for programmatic consumption
- Latest report symlinks (latest.html, latest.json)

### Database (`src/database.py`)
- SQLite via SQLAlchemy ORM
- 7 models: User, UserProfile, JobPosting, Application, CVImprovementLog, CompanyResearch, ApplicationResult
- Alembic for schema migrations (3 migration files)
- Context manager pattern for session handling

## Key Design Decisions

### Why Playwright over Selenium?
Playwright is faster, has better async support, auto-waits for elements, and has a simpler API. Selenium was in requirements but never used.

### Why sentence-transformers over keyword matching?
Semantic embeddings capture meaning rather than keywords. "Python developer" and "software engineer with Python" both match even though they share few keywords.

### Why Gemini over OpenAI as default?
Gemini offers a generous free tier for development and testing. OpenAI is the fallback for production use.

### Why google.genai over google.generativeai?
The new google.genai SDK uses a cleaner client-based API (genai.Client) rather than module-level configuration. google.generativeai is deprecated.

### Why SQLite over PostgreSQL?
SQLite is zero-config and sufficient for single-user CLI usage. PostgreSQL would be unnecessary overhead at this stage.

### Why list-based LinkedIn scraping?
Card-based selectors break frequently with LinkedIn DOM changes. List-based extraction (.jobs-search__results-list) is more stable and doesn't require sign-in.

### Why DuckDuckGo for company research?
No API key required — reduces dependency overhead. Falls back gracefully when blocked.

## Pipeline Flow (Autonomous Mode)

```
1. Parse CV from data/cvs/ (most recent file auto-detected)
2. Score CV across 4 dimensions
3. Improve CV via AI (summary, experience, skills sections)
4. Search jobs across LinkedIn, Indeed, Glassdoor
5. Deduplicate by URL
6. Match via embedding similarity
7. Filter by threshold (0.6 for auto-apply)
8. For each matched job (max 10):
   a. Research company (web search + AI brief)
   b. Check red flags (skip if found)
   c. Tailor CV for the role
   d. Generate cover letter
   e. Submit application (retry + CAPTCHA-aware)
9. Save all results to database
10. Generate HTML + JSON reports
11. Send email summary (if configured)
12. [Continuous mode] Sleep 6h → repeat
```
