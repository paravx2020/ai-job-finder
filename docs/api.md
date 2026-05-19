# JobFinder API Reference

## CV Processor

### `src.cv_processor.parser.parse_cv(path)`
Parses a PDF or DOCX CV file into structured data.

- **Args**: `path (Path)` — Path to CV file (.pdf or .docx)
- **Returns**: `dict` — `{raw_text, sections, skills, skill_categories, entities, word_count}`
- **Raises**: `ValueError` — Unsupported file format

### `src.cv_processor.scorer.score_cv(parsed_cv)`
Scores a parsed CV across 4 quality dimensions.

- **Args**: `parsed_cv (dict)` — Output from `parse_cv()`
- **Returns**: `dict` — `{scores: {keyword_density, quantified_achievements, section_completeness, ats_compatibility}, overall, suggestions}`

### `src.cv_processor.improver.improve_cv(parsed_cv, domain)`
AI-powered CV section improvement.

- **Args**: `parsed_cv (dict)`, `domain (str)` — Target industry domain
- **Returns**: `dict` — `{improved_sections, changes}`

## Job Scraper

### `src.job_scraper.engine.search_all(query, location, max_per_source)`
Scrapes all configured job sites.

- **Args**: `query (str)`, `location (str)`, `max_per_source (int)`
- **Returns**: `list[JobPosting]` — Deduplicated job results

### `src.job_scraper.base.BaseScraper`
Abstract base class for job site scrapers.

- Methods: `search(query, location, max_results)`, `source_name()`

## Matcher

### `src.matcher.engine.match_jobs(parsed_cv, jobs, top_k)`
Ranks jobs by semantic similarity to the CV.

- **Args**: `parsed_cv (dict)`, `jobs (list[JobPosting])`, `top_k (int)`
- **Returns**: `list[dict]` — Ranked matches with scores and reasons

## Auto-Applier

### `src.auto_applier.applier.apply_to_job(job_url, user_data, resume_path, cover_letter)`
Submits an application via headless browser.

- **Args**: `job_url (str)`, `user_data (dict)`, `resume_path (str)`, `cover_letter (str)`
- **Returns**: `dict` — `{success, error}`

## Database

### `src.database.session_scope()`
Context manager for database sessions with auto-commit/rollback.

### `src.database.init_db()`
Creates all database tables.
