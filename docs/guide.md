# JobFinder User Guide

## Installation

### Quick Install

```bash
pip install -r requirements.txt
playwright install chromium
python -m spacy download en_core_web_sm
cp .env.template .env
```

### Development Install

```bash
pip install -e ".[dev]"
pre-commit install
```

## Configuration

### API Keys

Get your API key from one of:
- **Gemini**: https://aistudio.google.com/apikey → Set `GEMINI_API_KEY`
- **OpenAI**: https://platform.openai.com/api-keys → Set `OPENAI_API_KEY`

### Email Notifications (Optional)

To enable email notifications:
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password (Google Account > Security > App Passwords)
3. Set `EMAIL_SENDER`, `EMAIL_PASSWORD`, and `EMAIL_RECEIVER` in `.env`

### Key Settings in `.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_MODEL` | `gemini-3.5-flash` | AI model for CV improvement, tailoring, company research |
| `DRY_RUN` | `false` | Enable dry-run to test without actual submissions |
| `CONFIRM_BEFORE_SUBMIT` | `true` | Require user confirmation before applying |
| `MAX_APPLICATIONS_PER_RUN` | `10` | Max applications per daemon cycle |
| `AUTO_APPLY_THRESHOLD` | `0.6` | Minimum match score for auto-apply |
| `DAEMON_SLEEP_HOURS` | `6` | Hours between daemon cycles |

---

## Workflows

### 1. CV Analysis

```bash
python -m src.main analyze my_cv.pdf --domain "IT support"
```

This will:
1. Parse your CV into sections (summary, experience, education, skills, certifications)
2. Extract skills by matching against a 140+ skill taxonomy
3. Score it across 4 quality dimensions (keyword density, quantified achievements, section completeness, ATS compatibility)
4. Rewrite key sections using AI (summary, experience, skills)

Export results:
```bash
python -m src.main analyze my_cv.pdf --format json --output analysis.json
python -m src.main analyze my_cv.pdf --format pdf --output analysis.pdf
```

### 2. Job Search

```bash
python -m src.main search my_cv.pdf --location "San Francisco" --top-k 10
```

This will:
1. Parse your CV to extract skills
2. Auto-generate a search query from your top skills
3. Scrape LinkedIn (list-based, no sign-in), Indeed, and Glassdoor
4. Rank jobs by semantic match to your CV (sentence-transformers embeddings)
5. Save results to the database

### 3. User Profiles

```bash
# Create a profile
python -m src.main profile alice@example.com --name "Alice" --domain "IT support" --location "NYC"

# List profiles
python -m src.main profile

# Use a profile with other commands
python -m src.main analyze cv.pdf --user alice@example.com
```

### 4. Auto-Apply

```bash
# Apply to the best match
python -m src.main apply

# Apply to a specific match
python -m src.main apply --index 3

# Apply to all matches
python -m src.main apply --all --cover-letter "I am excited to apply..."

# Apply with a specific CV and user profile
python -m src.main apply --all --cv resume.pdf --user alice@example.com
```

### 5. Autonomous/Daemon Mode

```bash
# ALWAYS start with dry-run to verify the pipeline
python -m src.main daemon --once --dry-run

# Single cycle (good for cron scheduling)
python -m src.main daemon --once

# Continuous 24/7 mode (runs every 6 hours by default)
python -m src.main daemon
```

The daemon pipeline:
```
CV parse → job search → match → filter by threshold
→ company research → red flag check → CV tailoring
→ cover letter generation → apply → save → report → [sleep]
```

### 6. Response Tracking

```bash
# Track application outcomes
python -m src.main track-response 1 interview
python -m src.main track-response 2 rejected
python -m src.main track-response 3 ghosted
python -m src.main track-response 4 offer

# View full report with performance analysis
python -m src.main report
```

### 7. Listing and Statistics

```bash
# List all applications
python -m src.main list

# List only pending applications
python -m src.main list --status pending

# View summary statistics
python -m src.main stats
```

---

## Daemon Configuration

### Dry-Run Mode
Set `DRY_RUN=true` in `.env` to prevent any actual submissions while testing the pipeline.

### Match Threshold
Set `AUTO_APPLY_THRESHOLD=0.7` to only apply to jobs with a 70%+ match score.

### Sleep Interval
Set `DAEMON_SLEEP_HOURS=12` for twice-daily or `1` for hourly runs.

### Red Flag Keywords
Customize `COMPANY_RED_FLAG_KEYWORDS=lawsuit,layoff,class action,toxic,hostile work,scam`
Companies matching any keyword will be skipped.

---

## Troubleshooting

### "No module named 'spacy'"
Run: `python -m spacy download en_core_web_sm`

### "Playwright browsers not found"
Run: `playwright install chromium`

### "No AI API key found"
Set `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`

### LinkedIn scraper returns no results
LinkedIn frequently changes its DOM. The scraper uses list-based extraction (`.jobs-search__results-list`). Update selectors in `config/scraper_selectors.json`.

### Indeed/Glassdoor return 0 jobs
These sites are often blocked by Cloudflare. The scrapers detect this and return 0 results gracefully. Check `config/scraper_selectors.json` if the DOM changed.

### Database migration errors
Run: `python -m src.main migrate` or `alembic upgrade head`

### CV parsing misses sections
The parser now handles UPPERCASE headings and flexible formatting. If sections are still missed, check the raw text extraction first.

### AI calls are expensive
The system has 24h TTL disk-based caching for AI responses. Repeated analyze runs on the same CV won't hit the API within 24 hours.
