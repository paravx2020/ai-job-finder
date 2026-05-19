# JobFinder — Implementation Plan

## Phase 1 — MVP (Weeks 1-4)

### Week 1: Foundation
- [x] Project structure & skeleton
- [ ] `src/main.py` — CLI entry point with argparse
- [ ] `config/settings.py` — Load .env, API keys, paths
- [ ] `requirements.txt` — All Python dependencies
- [ ] Database schema (SQLite) & migrations

### Week 2: CV Processing Pipeline
- [ ] `src/cv_processor/parser.py` — Parse PDF/DOCX → structured JSON
  - Extract sections: skills, experience, education, projects, certifications
  - spaCy NER for entity extraction (company names, degrees, technologies)
- [ ] `src/cv_processor/scorer.py` — Score CV quality
  - Keyword density, ATS compatibility, quantified achievements
  - Action verb usage, section completeness
- [ ] `src/cv_processor/improver.py` — AI-powered improvement
  - Call Gemini/OpenAI to rewrite bullet points
  - Add domain-specific keywords
  - Tailor summary to target role
  - Generate before/after diff for user review

### Week 3: Job Scraping & Matching
- [ ] `src/job_scraper/scraper.py` — Base scraper with Playwright
- [ ] `src/job_scraper/linkedin.py` — LinkedIn job search
- [ ] `src/job_scraper/indeed.py` — Indeed job search
- [ ] `src/job_scraper/glassdoor.py` — Glassdoor job search
- [ ] `src/job_scraper/deduplicator.py` — Remove duplicate listings
- [ ] `src/matcher/engine.py` — Embedding-based similarity
  - Encode CV (skills + experience summary) into vector
  - Encode each job description into vector
  - Cosine similarity → ranked list
  - Present top 5 with match percentages & reasoning

### Week 4: Auto-Apply & Notifications
- [ ] `src/auto_applier/applier.py` — Playwright-based form filler
  - Detect form fields (name, email, phone, resume upload, cover letter)
  - Fill with user's data
  - Handle multi-page applications
  - Captcha detection (pause & alert user)
- [ ] `src/notification/email_notifier.py` — Send status via SMTP
- [ ] `src/notification/console_notifier.py` — Terminal notifications
- [ ] Integration tests & end-to-end flow

## Phase 2 — Web UI & Advanced (Weeks 5-8)
- [ ] FastAPI server (`src/api/`)
- [ ] React dashboard for CV management, job tracking
- [ ] Per-job tailored CV generation
- [ ] Interview question generator
- [ ] Salary scraping & insights
- [ ] PostgreSQL migration

## Phase 3 — Marketplace (Weeks 9-12)
- [ ] Employer registration & job posting
- [ ] Bidirectional matching algorithm
- [ ] Interview scheduling system
- [ ] Feedback loop & analytics
- [ ] Multi-tenant architecture

## Architecture Overview
```
┌─────────────────────────────────────────────────────────┐
│                    main.py (CLI / API)                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ CV Processor  │  │ Job Scraper  │  │   Matcher    │  │
│  │  - parser     │  │  - linkedin  │  │  - embedding  │  │
│  │  - scorer     │  │  - indeed    │  │  - ranker    │  │
│  │  - improver   │  │  - glassdoor │  │  - explainer │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
│         └─────────┬───────┴──────────────────┘          │
│                   │                                     │
│  ┌────────────────▼──────────────────────────┐          │
│  │            Auto Applier                   │          │
│  │  (Playwright headless form submission)    │          │
│  └────────────────┬──────────────────────────┘          │
│                   │                                     │
│  ┌────────────────▼──────────────────────────┐          │
│  │           Notification System              │          │
│  │     Email + Console + (Future: SMS)        │          │
│  └────────────────────────────────────────────┘          │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Storage: SQLite (Phase1) → PostgreSQL (Phase2)  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Key Design Decisions
1. **Playwright over Selenium**: Faster, better async support, auto-waits
2. **Sentence embeddings over keyword TF-IDF**: Captures semantic match
3. **User-in-the-loop for auto-apply**: Never submit without explicit approval
4. **Modular scrapers**: Each source is a plugin implementing `BaseScraper`
5. **SQLite first**: Zero config for MVP, easy migration path to PG

## Risk Mitigation
| Risk | Mitigation |
|------|------------|
| LinkedIn blocks scraping | Rotate user agents, use delays, fallback to Google Jobs API |
| Captcha on job portals | Detect + alert user to solve manually |
| API costs (AI) | Local models (sentence-transformers) for embedding; cache AI responses |
| Form variations | Maintain field-mapping config per known site |
