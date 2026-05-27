# Autonomous Job-Finding Agent — Upgrade Prompt

Paste this into `/goal` to refactor your existing ai-job-finder into an autonomous agent.

```
Refactor the existing project at /home/paravx/Projects/ai-job-finder from a manual CLI tool into an autonomous, always-on job-finding agent. The current project is a solid foundation (CLI-based: analyze CV, search jobs, manually confirm each application). The goal is to make it run in the background without the user in the loop.

WHAT THE RESULT SHOULD DO:
- The user drops their CV in /home/paravx/Projects/ai-job-finder/data/cvs/ once
- The agent runs nightly (or on demand), finds new matching jobs, researches each company, tailors the CV + cover letter per role, and applies automatically
- It tracks which applications get callbacks, which resume versions perform best, and optimizes its strategy over time
- The user only gets notified of outcomes — never needs to click "confirm" again

DO NOT start from scratch. Refactor the existing code at /home/paravx/Projects/ai-job-finder. Keep all existing CLI commands working (analyze, search, apply, list, stats, profile). Add new capabilities on top.

PHASE 1 — AUTONOMOUS DAEMON MODE:
1. Add a new entry point: `python -m src.daemon` (or `ai-job-finder daemon`) that:
   a. Loads the user's latest CV from data/cvs/latest_cv.pdf (or whichever was most recently analyzed)
   b. Runs the full pipeline: parse CV -> search for jobs -> score matches -> for matches above 0.6 threshold: research company, tailor CV, generate cover letter, apply
   c. Sleeps for 6 hours, then repeats (continuous loop)
   d. Logs all activity to both console and data/daemon.log
   e. Sends a daily summary email to the user (via existing email notifier)
2. Add config flag AUTO_APPLY_THRESHOLD = 0.6 in config.py (only auto-apply above this match score)
3. Add DRY_RUN mode (default=False) that logs what it WOULD do without actually submitting
4. Add a --once flag for one-shot daemon run (useful for cron)

PHASE 2 — PER-ROLE CV TAILORING:
1. Currently CV improvement is generic (improve_section for summary/experience/skills). Refactor it to accept a specific job posting context:
   - Parse the job description, extract key requirements, required skills, preferred skills, company name/industry
   - Generate a tailored version of the CV that emphasizes the skills/experience matching THIS specific job
   - Store each tailored CV variant in data/tailored_cvs/{job_id}_tailored.pdf
   - The cover letter should mention specific company details (not generic)
2. Add a new route in the improver: `tailor_cv_for_job(parsed_cv, job_posting) -> tailored_cv_text`
   This should use an LLM call with the job description as context and the CV as base

PHASE 3 — COMPANY RESEARCH:
1. Before applying to any job, research the company:
   - Use web_search to find: recent news about the company, funding status, company culture reviews, recent product launches
   - Summarize findings into a "company intelligence" brief (100-200 words)
   - Feed this into the cover letter generation so the cover letter references something current/authentic about the company
2. Add CompanyResearch model to database: id, job_id, company_name, summary_brief, sources (JSON), researched_at
3. Skip application for companies with red flags (identified via keyword patterns: lawsuit, layoff, class action, toxic work culture — make this configurable)

PHASE 4 — INTELLIGENT APPLICATION PIPELINE:
1. Refactor the auto_applier to be robust enough for unattended operation:
   - Currently uses CONFIRM_BEFORE_SUBMIT=True — CHANGE THIS to False by default (the whole point is autonomy)
   - Add retry logic: if the apply button isn't found, try alternative navigation paths (scroll to bottom, look for iframes, wait for dynamic content)
   - Add CAPTCHA detection (already exists partially) — if detected, log it and skip that job gracefully
   - Add rate limiting: max 10 applications per daemon run, 3-second min delay between submissions
   - Track application success/failure per site to detect when site layouts change
2. Add ApplicationResult model with fields: job_id, cv_used_path, cover_letter_text, company_research_id, tailored_version_id, status, error_message, applied_at, response_received_at

PHASE 5 — RESPONSE TRACKING & OPTIMIZATION:
1. When an application gets a response (email callback), the agent should detect it:
   - Add a new command `ai-job-finder track-response <application_id> <status>` where status is: rejected, interview, ghosted, offer
   - Maintain a performance log: per resume template version, what's the callback rate?
   - After 20+ applications, analyze which CV version/tailoring approach had the highest interview rate
   - Automatically prefer the best-performing approach for future applications
2. Add a "ghosted" status: if no response after 14 days, mark as ghosted and consider following up with a polite email reminder (optional, configurable)

PHASE 6 — DAILY SUMMARY & NOTIFICATION:
1. After each daemon run, generate a summary report:
   - Jobs found: X
   - Jobs applied to: Y (with company names)
   - Applications failed/skipped: Z (with reasons)
   - Callbacks since last run: W
   - Interview rate trend
2. Deliver via email (existing EmailNotifier) and optionally as a local HTML file in data/reports/
3. Add a CLI command `ai-job-finder report` to view the latest summary

CONFIG CHANGES (update config.py and .env.template):
- AUTO_APPLY_THRESHOLD = 0.6
- DRY_RUN = false
- MAX_APPLICATIONS_PER_RUN = 10
- DAEMON_SLEEP_HOURS = 6
- COMPANY_RESEARCH_ENABLED = true
- COMPANY_RED_FLAG_KEYWORDS = ["lawsuit","layoff","class action","toxic","hostile work"]
- TRACK_OPTIMIZATION_ENABLED = true
- FOLLOW_UP_GHOSTED_AFTER_DAYS = 14
- EMAIL_DAILY_SUMMARY = true
- EMAIL_SUMMARY_TIME = "08:00"

KEEP EVERYTHING THAT WORKS:
- Don't break the existing CLI commands (analyze, search, apply, list, stats, profile)
- Keep all existing database models — add new ones, don't modify existing schemas
- Keep the existing test suite passing
- Keep the existing scraper infrastructure for LinkedIn, Indeed, Glassdoor
- Keep the existing matcher (sentence-transformers) — add the LLM-based tailoring on top

ADD THESE NEW FILES:
- src/daemon.py — autonomous loop
- src/company_research.py — company intelligence gathering
- src/tailoring.py — per-job CV + cover letter generation
- src/optimization.py — response rate tracking and strategy optimization
- src/reporter.py — daily summary report generation
- src/utils/__init__.py already exists, add any helpers there

Commit after each phase with a descriptive message. Update AGENTS.md and README.md as you go. Run the existing test suite to make sure nothing is broken.

After completing, verify with: python -m src.daemon --once --dry-run (should scan jobs, research companies, generate tailored CVs and cover letters, log everything — but not actually submit).
```
