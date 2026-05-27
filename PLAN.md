# JobFinder — Implementation Plan

## Phase 1 — MVP (Complete)

### Foundation
- [x] Project structure & skeleton
- [x] `src/main.py` — CLI entry point with Click (10 commands)
- [x] `config/settings.py` — Load .env, API keys, paths (25+ config vars)
- [x] `requirements.txt` — All Python dependencies
- [x] Database schema (SQLite) & Alembic migrations (3 migrations)

### CV Processing Pipeline
- [x] `src/cv_processor/parser.py` — Parse PDF/DOCX → structured JSON
  - Extract sections: summary, skills, experience, education, certifications
  - spaCy NER for entity extraction (company names, degrees, technologies)
  - Flexible heading matching (UPPERCASE, Title Case, lowercase)
  - Word-boundary regex for accurate skill extraction
- [x] `src/cv_processor/scorer.py` — Score CV quality
  - Keyword density, ATS compatibility, quantified achievements
  - Action verb usage, section completeness
  - Domain-specific skill matching against taxonomy
- [x] `src/cv_processor/improver.py` — AI-powered improvement
  - Call Gemini/OpenAI to rewrite bullet points (google.genai SDK)
  - Add domain-specific keywords
  - Tailor summary to target role
  - Generate before/after diff for user review

### Job Scraping & Matching
- [x] `src/job_scraper/base.py` — Base scraper with Playwright (ABC)
- [x] `src/job_scraper/linkedin.py` — LinkedIn job search (list-based, no sign-in)
- [x] `src/job_scraper/indeed.py` — Indeed job search (Cloudflare detection)
- [x] `src/job_scraper/glassdoor.py` — Glassdoor job search (Cloudflare detection)
- [x] `src/job_scraper/engine.py` — Scraper orchestration + deduplication
- [x] `src/matcher/engine.py` — Embedding-based similarity
  - Encode CV (skills + experience summary) into vector
  - Encode each job description into vector
  - Cosine similarity → ranked list
  - Present top K with match percentages & reasoning

### Auto-Apply & Notifications
- [x] `src/auto_applier/applier.py` — Playwright-based form filler
  - Detect form fields (name, email, phone, resume upload, cover letter)
  - Fill with user's data
  - Handle multi-page applications
  - CAPTCHA detection (reCAPTCHA, hCaptcha, Cloudflare)
  - Retry logic with exponential backoff
- [x] `src/notification/email_notifier.py` — Send status via SMTP
- [x] `src/notification/console_notifier.py` — Terminal notifications
- [x] Integration tests & end-to-end flow

### Infrastructure
- [x] Skills taxonomy (data/skills_taxonomy.json, 140+ skills, 8 categories)
- [x] Externalized scraper selectors (config/scraper_selectors.json)
- [x] AI API caching (24h TTL, disk-based, SHA256 keys)
- [x] Structured JSON logging (Rich console + file output)
- [x] Custom exception hierarchy (JobFinderError + 19 subclasses)
- [x] PyPI packaging (pyproject.toml, entry points, MANIFEST.in)
- [x] CI/CD pipeline (GitHub Actions: lint, typecheck, test, build, publish)
- [x] Code quality tooling (ruff, black, mypy, pre-commit)
- [x] Multi-user support (UserProfile, --user flag, profile command)
- [x] Anonymous user mode (no --user flag required)
- [x] Documentation (README, user guide, API reference, architecture guide)

## Phase 2 — Enhanced (Partially Complete)

### Autonomous Mode
- [x] `src/daemon.py` — Autonomous job-finding loop
  - 24/7 background mode: `ai-job-finder daemon`
  - One-shot/cron mode: `ai-job-finder daemon --once`
  - Dry-run preview: `ai-job-finder daemon --once --dry-run`
- [x] `src/tailoring.py` — Per-job CV tailoring
  - Extract structured requirements from job descriptions
  - Generate role-specific CV emphasizing matching skills
  - AI-powered cover letter generation (250-350 words)
  - Company research integration in cover letters
- [x] `src/company_research.py` — Company intelligence
  - DuckDuckGo web search (no API key needed)
  - AI-powered summarization into 100-200 word brief
  - Red flag keyword detection (configurable)
  - Graceful fallback when web search unavailable
- [x] `src/optimization.py` — Response tracking
  - Application outcome tracking (rejected/interview/ghosted/offer)
  - Auto-ghosted detection after configurable days
  - CV version performance analysis (callback rate)
  - Follow-up suggestions for ghosted applications
- [x] `src/reporter.py` — Daily reports
  - HTML report with full activity summary
  - JSON structured report for programmatic use
  - Email daily summary (configurable)
- [ ] `src/database.py` — PostgreSQL migration (not started)

### Web UI (Not Started)
- [ ] FastAPI server
- [ ] React dashboard for CV management, job tracking
- [ ] Per-job tailored CV generation (via web)
- [ ] Interview question generator
- [ ] Salary scraping & insights

## Phase 3 — Marketplace (Not Started)
- [ ] Employer registration & job posting
- [ ] Bidirectional matching algorithm
- [ ] Interview scheduling system
- [ ] Feedback loop & analytics
- [ ] Multi-tenant architecture

## Architecture Overview

```mermaid
flowchart TB
    subgraph CLI["main.py (CLI / API)"]
        direction TB
        
        subgraph Process[" "]
            direction LR
            P1["CV Processor<br/>parser · scorer · improver"]
            P2["Job Scraper<br/>linkedin · indeed · glassdoor"]
            P3["Matcher<br/>embedding · ranker · explainer"]
        end
        
        subgraph PreApply["Pre-Apply Pipeline"]
            direction LR
            CR["Company Research"]
            CT["CV Tailoring"]
            CL["Cover Letter"]
            CR --> CT --> CL
        end
        
        AA["Auto Applier<br/>(Playwright headless)"]
        NS["Notification System<br/>Email · Console · Reports · Response Track"]
        
        P1 --> P3
        P2 --> P3
        P3 --> PreApply
        PreApply --> AA
        AA --> NS
    end
    
    DB[("Storage<br/>SQLite (7 tables)<br/>→ PostgreSQL Phase 2)"] -.-> CLI
    
    style CLI fill:#1a1a2e,stroke:#e94560,color:#fff
    style DB fill:#16213e,stroke:#0f3460,color:#fff
    style Process fill:transparent,stroke:#e94560,stroke-dasharray: 5 5
    style PreApply fill:transparent,stroke:#e94560,stroke-dasharray: 5 5
```

## Key Design Decisions
1. **Playwright over Selenium**: Faster, better async support, auto-waits
2. **Sentence embeddings over keyword TF-IDF**: Captures semantic match
3. **User-in-the-loop for auto-apply**: Never submit without explicit approval
4. **Modular scrapers**: Each source is a plugin implementing BaseScraper
5. **SQLite first**: Zero config for MVP, easy migration path to PG
6. **google.genai over google.generativeai**: New SDK, cleaner client-based API
7. **List-based LinkedIn scraping**: More stable than card selectors, no sign-in
8. **Blocked page detection**: Indeed/Glassdoor degrade gracefully when blocked
9. **Autonomous daemon**: Self-contained loop, cron-friendly, dry-run safe
10. **Anonymous users**: No --user flag required for simple workflows

## Risk Mitigation
| Risk | Mitigation |
|------|------------|
| LinkedIn blocks scraping | List-based extraction, no sign-in, 2-5s delays |
| Captcha on job portals | Detect + alert user; graceful skip |
| API costs (AI) | sentence-transformers for local embedding; cache AI responses |
| Form variations | Maintain field-mapping config in auto-applier |
| Indeed/Glassdoor blocked | Cloudflare detection; graceful 0-result return |
| LinkedIn DOM changes | Externalized selectors in JSON config file |
