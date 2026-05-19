# JobFinder — Product Requirements Document

## 1. Vision
An intelligent career agent that reads a user's CV, improves it, finds matching job opportunities, and auto-applies — evolving into a dual-sided marketplace connecting employers with ideal candidates.

## 2. Core Flow
```
Upload CV → Parse & Score → Improve CV (domain-tailored)
         → Scrape Jobs (LinkedIn, Indeed, etc.)
         → Match Top 5 → User Review → Auto-Apply → Notify User
```

## 3. Features by Phase

### Phase 1 (MVP)
| Feature | Description |
|---------|-------------|
| CV Parser | Extract structured data from PDF/DOCX: name, skills, experience, education |
| CV Scorer | Score sections (content, keywords, formatting, ATS-friendliness) |
| CV Improver | Rewrite bullet points, add domain keywords, tailor summary |
| Job Scraper | Search LinkedIn, Indeed, Glassdoor for matching roles |
| Job Matcher | Embedding-based similarity between CV skills + experience and job descriptions |
| Top-5 Recommender | Rank and present best-matching jobs with rationale |
| Auto-Apply | Fill forms / submit applications via headless browser (with user approval) |
| Notification | Email + terminal notifications on application status |

### Phase 2 (Enhanced)
| Feature | Description |
|---------|-------------|
| Profile Dashboard | Web UI for CV management, job tracking |
| Tailored CV per Job | Generate job-specific CV versions |
| Interview Prep | Generate Q&A based on job description |
| Salary Insights | Scrape salary data, recommend negotiation ranges |

### Phase 3 (Marketplace)
| Feature | Description |
|---------|-------------|
| Employer Portal | Companies post jobs, set criteria |
| Smart Matching Engine | Bidirectional matching (candidate ↔ job) |
| Interview Scheduler | Coordinate slots between both parties |
| Feedback Loop | Employer feedback → CV improvement |
| Analytics Dashboard | Match rates, time-to-hire, satisfaction scores |

## 4. Technical Requirements

### Stack
- **Language**: Python 3.10+
- **AI/ML**: OpenAI / Gemini API for CV improvement & matching
- **CV Parsing**: `python-docx`, `PyPDF2`, `pdfplumber`, `spaCy` (NER)
- **Job Scraping**: `playwright` (headless), `beautifulsoup4`
- **Embeddings**: `sentence-transformers` (all-MiniLM-L6-v2) for similarity
- **Auto-Apply**: `playwright` form automation
- **Storage**: SQLite (Phase 1) → PostgreSQL (Phase 2+)
- **Frontend** (Phase 2+): FastAPI + React
- **Background Tasks**: Celery / Redis queue for scraping + applying

### Data Models
```
User          → id, name, email, raw_cv_path, parsed_cv (JSON)
ParsedCV      → skills[], experience[], education[], projects[], certs[]
JobPosting    → id, source, title, company, description, url, salary, location
Application   → id, user_id, job_id, status, applied_at, response
ImprovementLog → id, user_id, original_section, improved_text, model_used
```

### API Integrations
- **LinkedIn**: Playwright scraping (no official API without partnership)
- **Indeed**: RSS feed + scraping fallback
- **Glassdoor**: Scraping
- **AI**: OpenAI GPT-4 / Gemini 2.0 Flash for CV rewriting + matching scores
- **Email**: SMTP (Gmail app password) for notifications
