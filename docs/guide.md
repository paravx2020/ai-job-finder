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

## Workflows

### 1. CV Analysis

```bash
python -m src.main analyze my_cv.pdf --domain "machine learning"
```

This will:
1. Parse your CV into sections (summary, experience, education, skills)
2. Score it across 4 quality dimensions
3. Rewrite key sections using AI

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
3. Scrape LinkedIn, Indeed, and Glassdoor
4. Rank jobs by semantic match to your CV
5. Save results to the database

### 3. Auto-Apply

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

### 4. User Profiles

```bash
# Create a profile
python -m src.main profile alice@example.com --name "Alice" --domain "data science" --location "NYC"

# List profiles
python -m src.main profile

# Use a profile with other commands
python -m src.main analyze cv.pdf --user alice@example.com
```

## Troubleshooting

### "No module named 'spacy'"
Run: `python -m spacy download en_core_web_sm`

### "Playwright browsers not found"
Run: `playwright install chromium`

### "No AI API key found"
Set `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`

### LinkedIn scraper returns no results
LinkedIn frequently changes its DOM. Update selectors in `config/scraper_selectors.json`.

### Database migration errors
Run: `alembic upgrade head`
