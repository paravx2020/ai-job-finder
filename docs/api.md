# JobFinder API Reference

## CLI Commands

### `analyze <cv>`
Parse, score, and improve a CV.

- **Args**: `cv (str)` — Path to CV file (.pdf, .docx, .doc, .txt)
- **Options**: `--domain`, `--format` (text/json/pdf), `--output`, `--user`
- **Returns**: Parsed CV text + scores + AI improvement suggestions

### `search <cv>`
Scrape job sites and rank matches.

- **Args**: `cv (str)` — Path to CV file
- **Options**: `--query`, `--location`, `--top-k`, `--format` (text/json/pdf), `--output`, `--user`
- **Returns**: Ranked list of job matches with scores

### `apply`
Submit applications to matched jobs.

- **Options**: `--index` (specific job), `--all` (all matches), `--cv`, `--cover-letter`, `--user`
- **Returns**: Application submission results

### `list`
Show saved applications.

- **Options**: `--status` (pending/submitted), `--limit`

### `stats`
Display summary statistics. No options.

### `profile [email]`
Manage user profiles.

- **Args**: `email (str, optional)` — Email to lookup/create
- **Options**: `--name`, `--phone`, `--domain`, `--location`

### `daemon`
Run autonomous job-finding loop.

- **Options**: `--once` (single cycle), `--dry-run` (no actual submissions)

### `track-response <id> <status>`
Track application outcome.

- **Args**: `id (int)` — Application ID, `status (str)` — rejected|interview|ghosted|offer

### `report`
Show full application summary + performance analysis.

### `migrate`
Run database migrations (alembic upgrade head).

---

## CV Processor

### `src.cv_processor.parser.parse_cv(path)`
Parses a PDF, DOCX, or TXT CV file into structured data.

- **Args**: `path (Path)` — Path to CV file
- **Returns**: `ParsedCV` — `{raw_text, sections{}, skills[], skill_categories{}, entities{}, word_count}`
- **Raises**: `ValueError` — Unsupported file format
- **Notes**: Flexible heading matching detects UPPERCASE, Title Case, lowercase section headers. Skill extraction uses word-boundary regex against 140+ skill taxonomy.

### `src.cv_processor.scorer.score_cv(parsed_cv)`
Scores a parsed CV across 4 quality dimensions.

- **Args**: `parsed_cv (dict)` — Output from `parse_cv()`
- **Returns**: `dict` — `{scores: {keyword_density (0.0-1.0), quantified_achievements (0.0-1.0), section_completeness (0.0-1.0), ats_compatibility (0.0-1.0)}, overall: float, suggestions[]}`

### `src.cv_processor.improver.CVImprover`
AI-powered CV section improvement.

- **Constructor**: `CVImprover(domain: str, model: str | None = None)`
- **Method**: `improve(parsed_cv: dict)` → ImprovedCV with per-section original/improved text
- **AI SDK**: Uses `google.genai` (not deprecated `google.generativeai`)
- **Fallback chain**: Gemini → OpenAI

---

## Job Scraper

### `src.job_scraper.engine.search_all(query, location, max_per_source)`
Scrapes all configured job sites.

- **Args**: `query (str)`, `location (str)`, `max_per_source (int)`
- **Returns**: `list[JobPosting]` — Deduplicated job results
- **Sites**: LinkedIn (list-based, no sign-in), Indeed (Cloudflare detection), Glassdoor (Cloudflare detection)
- **Selectors**: Externalized in `config/scraper_selectors.json`

### `src.job_scraper.base.BaseScraper`
Abstract base class for job site scrapers.

- Methods: `search(query, location, max_results)`, `source_name()`
- Retry logic: exponential backoff, 3 retries
- CAPTCHA detection before scraping

---

## Matcher

### `src.matcher.engine.match_jobs(parsed_cv, jobs, top_k)`
Ranks jobs by semantic similarity to the CV.

- **Args**: `parsed_cv (dict/ParsedCV)`, `jobs (list[JobPosting])`, `top_k (int)`
- **Returns**: `list[dict]` — Ranked matches with `{title, company, score, reason, url}`
- **Embedding model**: sentence-transformers/all-MiniLM-L6-v2

---

## Company Research

### `src.company_research.research_company(company_name, job_title="")`
Research a company before applying.

- **Args**: `company_name (str)`, `job_title (str, optional)`
- **Returns**: `dict` — `{summary_brief (str), sources (list[dict]), red_flags (list[str])}`
- **Web search**: DuckDuckGo HTML endpoint (no API key)
- **AI summary**: 100-200 word intelligence brief via Gemini/OpenAI
- **Red flags**: Configurable via COMPANY_RED_FLAG_KEYWORDS env var

---

## Tailoring

### `src.tailoring.extract_job_requirements(job_data)`
Extract structured requirements from a job posting.

- **Args**: `job_data (dict)` — `{title, company, description (optional), salary, location}`
- **Returns**: `dict` — `{required_skills[], preferred_skills[], key_responsibilities[], industry, seniority}`

### `src.tailoring.generate_tailored_cv(parsed_cv, job_data)`
Generate a CV optimized for a specific job posting.

- **Args**: `parsed_cv (ParsedCV)`, `job_data (dict)` — Job details
- **Returns**: `str` — Tailored CV text (markdown format)
- **Behavior**: Reorders experience, emphasizes matching skills, inserts job keywords naturally

### `src.tailoring.generate_cover_letter(parsed_cv, job_data, company_research="")`
Generate a cover letter for a specific job.

- **Args**: `parsed_cv (ParsedCV)`, `job_data (dict)`, `company_research (str, optional)`
- **Returns**: `str` — 250-350 word cover letter

---

## Daemon

### `src.daemon.run_daemon(dry_run=False, once=False)`
Run the autonomous job-finding loop.

- **Args**: `dry_run (bool)` — Skip actual submissions, `once (bool)` — Single cycle
- **Pipeline**: parse → search → match → research → tailor → cover letter → apply → report
- **Config**: DAEMON_SLEEP_HOURS, MAX_APPLICATIONS_PER_RUN, AUTO_APPLY_THRESHOLD

---

## Optimization

### `src.optimization.OptimizationTracker`
Track and analyze application outcomes.

- Methods:
  - `track_response(application_id, status)` — Record outcome
  - `get_ghosted_applications()` — Find apps without response after threshold days
  - `analyze_cv_strategies()` — Compare callback rates per CV version
  - `get_follow_up_suggestions()` — List ghosted apps ready for follow-up

---

## Reporter

### `src.reporter.generate_report(session=None)`
Generate a full activity report.

- **Returns**: `tuple(str, str)` — (html_content, json_content)
- **Content**: Applications by status, top matches, company research, performance analysis

---

## Auto-Applier

### `src.auto_applier.applier.apply_to_job(job_url, user_data, resume_path, cover_letter)`
Submits an application via headless browser.

- **Args**: `job_url (str)`, `user_data (dict)`, `resume_path (str)`, `cover_letter (str)`
- **Returns**: `dict` — `{success (bool), error (str, optional)}`
- **CAPTCHA**: Detects reCAPTCHA, hCaptcha, Cloudflare
- **Retry**: Exponential backoff, iframe awareness
- **Confirmation**: Controlled by CONFIRM_BEFORE_SUBMIT env var

---

## Database

### Models (7 total)
- **User** — name, email, raw_cv_path, parsed_cv (JSON)
- **UserProfile** — email, name, phone, domain, location
- **JobPosting** — source, title, company, description, url (UNIQUE), salary, location, posted_date
- **Application** — user_id, job_id, status, match_score, match_reason, applied_at
- **CVImprovementLog** — user_id, section, original/improved text, model_used
- **CompanyResearch** — application_id, company_name, summary_brief, sources (JSON), red_flags (JSON)
- **ApplicationResult** — application_id, cv_path, cover_letter, company_research_id, status, notes

### `src.database.session_scope()`
Context manager for database sessions with auto-commit/rollback.

### `src.database.init_db()`
Creates all database tables.
