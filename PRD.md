# JobFinder — Product Requirements Document

## 1. Vision
An intelligent career agent that reads a user's CV, improves it, finds matching job opportunities, researches companies, tailors applications, and auto-applies — evolving into a dual-sided marketplace connecting employers with ideal candidates.

## 2. Core Flow (Phase 1+2)
```
Upload CV → Parse & Score → Improve CV (domain-tailored)
         → Scrape Jobs (LinkedIn, Indeed, Glassdoor)
         → Match Top K → Company Research → Red Flag Check
         → CV Tailoring → Cover Letter Generation
         → Auto-Apply → Track Response → Notify User
```

## 3. Features by Phase

### Phase 1 — MVP (Complete)
| Feature | Description | Status |
|---------|-------------|--------|
| CV Parser | Extract structured data from PDF/DOCX: name, skills, experience, education with flexible heading detection (UPPERCASE, Title Case) | Done |
| CV Scorer | Score sections across 4 dimensions (content, keywords, formatting, ATS) with domain-specific heuristics | Done |
| CV Improver | AI-powered section rewrites via google.genai SDK (Gemini 3.5 Flash default) | Done |
| Job Scraper | Search LinkedIn (list-based, no sign-in), Indeed, Glassdoor — with blocked page detection | Done |
| Job Matcher | Embedding-based similarity (sentence-transformers all-MiniLM-L6-v2) between CV and job descriptions | Done |
| Top-K Recommender | Rank and present best-matching jobs with match percentages and rationale | Done |
| Auto-Apply | Fill forms / submit applications via Playwright headless browser with safety confirmation | Done |
| Notification | Email + terminal notifications on application status | Done |
| Skills Taxonomy | 140+ skills across 8 categories with aliases and related skills | Done |
| Multi-User | UserProfile management with per-user data isolation and anonymous mode | Done |
| Database Migrations | Alembic-managed schema evolution | Done |
| PyPI Packaging | Entry points, wheel/sdist, CI/CD pipeline | Done |
| Documentation | README, user guide, API reference, architecture guide | Done |

### Phase 2 — Enhanced (Partially Complete)
| Feature | Description | Status |
|---------|-------------|--------|
| Autonomous Daemon | 24/7 pipeline: parse → search → match → research → tailor → apply → report → sleep | Done |
| Per-Job CV Tailoring | Generate job-specific CV versions optimized for each role | Done |
| Cover Letter Generation | AI-written cover letters referencing company intelligence | Done |
| Company Research | Web search (DuckDuckGo) + AI summarization for employer intelligence | Done |
| Red Flag Detection | Configurable keyword list to skip problematic companies | Done |
| Response Tracking | Track interview/rejected/ghosted/offer outcomes | Done |
| Auto-Ghosted Detection | Auto-mark after 14 days with no response | Done |
| CV Strategy Optimization | Analyze callback rate per CV version to find best-performing approach | Done |
| Daily Reports | HTML + JSON reports with full activity summary | Done |
| Email Daily Summary | Scheduled email with today's activity | Done |
| Profile Dashboard | Web UI for CV management, job tracking | Not Started |
| Interview Prep | Generate Q&A based on job description | Not Started |
| Salary Insights | Scrape salary data, recommend negotiation ranges | Not Started |

### Phase 3 — Marketplace (Not Started)
| Feature | Description |
|---------|-------------|
| Employer Portal | Companies post jobs, set criteria |
| Smart Matching Engine | Bidirectional matching (candidate job) |
| Interview Scheduler | Coordinate slots between both parties |
| Feedback Loop | Employer feedback → CV improvement |
| Analytics Dashboard | Match rates, time-to-hire, satisfaction scores |

## 4. Technical Requirements

### Stack
- **Language**: Python 3.10+
- **AI/ML**: Gemini 3.5 Flash (google.genai SDK) / OpenAI for CV improvement & matching
- **CV Parsing**: python-docx, PyPDF2, pdfplumber, spaCy (NER)
- **Job Scraping**: Playwright (headless Chromium), beautifulsoup4
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2) for similarity
- **Auto-Apply**: Playwright form automation with retry + CAPTCHA detection
- **Storage**: SQLite (Phase 1) → PostgreSQL (Phase 2+, not started)
- **Frontend** (Phase 3+): FastAPI + React (not started)
- **Background Tasks**: Celery / Redis queue (Phase 3+, not started)

### Data Models (7 tables)
```
User            → id, name, email, raw_cv_path, parsed_cv (JSON)
UserProfile     → id, email, name, phone, domain, location
JobPosting      → id, source, title, company, description, url, salary, location, posted_date
Application     → id, user_id, job_id, status, match_score, applied_at
CVImprovementLog → id, user_id, section, original_text, improved_text, model_used
CompanyResearch → id, application_id, company_name, summary_brief, sources, red_flags
ApplicationResult → id, application_id, cv_path, cover_letter, company_research_id, status
```

### API Integrations
- **LinkedIn**: Playwright scraping (list-based, no sign-in; no official API without partnership)
- **Indeed**: Playwright scraping with Cloudflare detection
- **Glassdoor**: Playwright scraping with Cloudflare detection
- **AI**: Gemini 3.5 Flash (default via google.genai SDK) / OpenAI (fallback)
- **Email**: SMTP (Gmail app password) for notifications
- **Company Research**: DuckDuckGo HTML search (no API key required)
