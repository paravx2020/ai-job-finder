# JobFinder Architecture

## System Overview

JobFinder follows a pipeline architecture where data flows through sequential processing stages:

```
CV File → Parser → Scorer → AI Improver → Job Scraper → Matcher → Auto-Applier → Notifications
                                                              │
                                                              ▼
                                                         Database (SQLite)
```

## Module Responsibilities

### CLI Layer (`src/main.py`)
- Click-based command interface
- Argument parsing, validation, and dispatch
- Progress indication via Rich
- Export handling (JSON/PDF)

### CV Processor (`src/cv_processor/`)
- **Parser**: Extracts text from PDF/DOCX, identifies sections via regex, extracts skills via taxonomy lookup, extracts entities via spaCy NER
- **Scorer**: 4-dimension quality evaluation with domain-specific heuristics
- **Improver**: AI-powered section rewriting with Gemini/OpenAI fallback

### Job Scraper (`src/job_scraper/`)
- Plugin architecture via `BaseScraper` ABC
- Three implementations: LinkedIn, Indeed, Glassdoor
- Externalized CSS selectors in `config/scraper_selectors.json`
- Retry logic with exponential backoff
- In-memory + DB-level deduplication

### Matcher (`src/matcher/`)
- Uses `sentence-transformers/all-MiniLM-L6-v2` for embeddings
- Cosine similarity between CV profile and job descriptions
- Threshold-based filtering (default: 0.5)
- Configurable top-K results

### Auto-Applier (`src/auto_applier/`)
- Playwright headless browser automation
- CAPTCHA detection before form submission
- Safety confirmation gate (`CONFIRM_BEFORE_SUBMIT`)
- Common form field selectors
- Result logging to database

### Database (`src/database.py`)
- SQLite via SQLAlchemy ORM
- 5 models: User, JobPosting, Application, CVImprovementLog, UserProfile
- Alembic for schema migrations
- Context manager pattern for session handling

## Key Design Decisions

### Why Playwright over Selenium?
Playwright is faster, has better async support, auto-waits for elements, and has a simpler API. Selenium was in requirements but never used.

### Why sentence-transformers over keyword matching?
Semantic embeddings capture meaning rather than keywords. "Python developer" and "software engineer with Python" both match even though they share few keywords.

### Why Gemini over OpenAI as default?
Gemini offers a generous free tier for development and testing. OpenAI is the fallback for production use.

### Why SQLite over PostgreSQL?
SQLite is zero-config and sufficient for single-user CLI usage. PostgreSQL would be unnecessary overhead at this stage.
