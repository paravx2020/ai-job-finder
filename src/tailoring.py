"""Per-role CV tailoring — generates customized CVs and cover letters.

Unlike the generic improver (improve_cv), these functions take a specific
job posting as context and tailor the output for that exact role.
"""

from src.utils.models import ParsedCV

from config import AI_MODEL


# ── AI Client ────────────────────────────────────────────────────────────────


def _get_client():
    """Get the AI client (reuses the improver's client setup)."""
    from src.cv_processor.improver import _get_client as improver_get_client

    return improver_get_client()


def _call_ai(prompt: str, model: str | None = None) -> str:
    """Make a non-cached AI call (tailoring should always be fresh for each job)."""
    from config import AI_MODEL, GEMINI_API_KEY, OPENAI_API_KEY

    model_name = model or AI_MODEL

    if GEMINI_API_KEY:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        resp = client.models.generate_content(model=model_name, contents=prompt)
        return resp.text.strip()

    elif OPENAI_API_KEY:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume writer and career coach who tailors applications for specific job postings.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()

    raise RuntimeError("No AI API key found. Set GEMINI_API_KEY or OPENAI_API_KEY in .env")


# ── Job Description Parsing ──────────────────────────────────────────────────


def extract_job_requirements(job_data: dict) -> dict:
    """Extract structured requirements from a job posting.

    Args:
        job_data: Dict with keys: title, company, description (optional), salary, location

    Returns:
        Dict with: required_skills, preferred_skills, key_responsibilities, industry, seniority
    """
    description = job_data.get("description", "")
    title = job_data.get("title", "")
    company = job_data.get("company", "")

    if not description or len(description) < 50:
        # No description available — use what we have
        return {
            "required_skills": [],  # noqa: RUF005
            "preferred_skills": [],
            "key_responsibilities": [f"Role: {title}"],
            "industry": "Unknown",
            "seniority": "Mid-level",
        }

    prompt = f"""Analyze this job posting and extract structured information.

Job Title: {title}
Company: {company}

Description:
{description[:3000]}

Return a JSON object with these fields:
- required_skills: list of must-have skills/technologies mentioned
- preferred_skills: list of nice-to-have skills mentioned
- key_responsibilities: list of 3-5 main responsibilities
- industry: the industry/domain (e.g., "FinTech", "Healthcare", "E-commerce")
- seniority: junior / mid-level / senior / lead / manager

JSON only, no other text."""

    import json

    try:
        response = _call_ai(prompt)
        # Try to extract JSON from the response
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return json.loads(response.strip())
    except Exception:
        return {
            "required_skills": [],
            "preferred_skills": [],
            "key_responsibilities": [f"Role: {title}"],
            "industry": "Unknown",
            "seniority": "Mid-level",
        }


# ── CV Tailoring ─────────────────────────────────────────────────────────────


def generate_tailored_cv(parsed_cv: ParsedCV, job_data: dict) -> str:
    """Generate a tailored CV text optimized for a specific job posting.

    Args:
        parsed_cv: The parsed CV with sections and skills
        job_data: Dict with title, company, description (optional)

    Returns:
        Tailored CV text (markdown/plain text format)
    """
    requirements = extract_job_requirements(job_data)
    title = job_data.get("title", "the position")
    company = job_data.get("company", "the company")

    cv_text = _build_cv_text(parsed_cv)

    prompt = f"""You are an expert resume writer. Tailor this CV for a specific job application.

JOB DETAILS:
- Title: {title}
- Company: {company}
- Required skills: {', '.join(requirements.get('required_skills', []))}
- Preferred skills: {', '.join(requirements.get('preferred_skills', []))}
- Key responsibilities: {'; '.join(requirements.get('key_responsibilities', []))}
- Industry: {requirements.get('industry', 'Technology')}
- Seniority: {requirements.get('seniority', 'Mid-level')}

ORIGINAL CV:
{cv_text}

INSTRUCTIONS:
1. Reorder experience bullet points to highlight the most relevant achievements first
2. Emphasize skills that match the job's required and preferred skills
3. Add specific keywords from the job description naturally into the summary and experience
4. Keep all factual information (dates, titles, companies) unchanged
5. If you lack certain skills mentioned in the job, do NOT fabricate them
6. Format as a clean CV with sections: Summary, Skills, Experience, Education

Return the complete tailored CV."""

    return _call_ai(prompt)


def generate_cover_letter(parsed_cv: ParsedCV, job_data: dict, company_research: str = "") -> str:
    """Generate a tailored cover letter for a specific job.

    Args:
        parsed_cv: The parsed CV
        job_data: Dict with title, company, description (optional)
        company_research: Optional company intelligence brief to reference

    Returns:
        Cover letter text
    """
    requirements = extract_job_requirements(job_data)
    title = job_data.get("title", "the position")
    company = job_data.get("company", "the company")
    description = job_data.get("description", "")

    cv_text = _build_cv_text(parsed_cv)

    research_section = ""
    if company_research:
        research_section = f"\nCOMPANY RESEARCH (reference this naturally in the letter):\n{company_research}\n"

    prompt = f"""Write a professional cover letter for a job application.

JOB:
- Title: {title}
- Company: {company}
- Key skills needed: {', '.join(requirements.get('required_skills', []))}
- Responsibilities: {'; '.join(requirements.get('key_responsibilities', []))}

MY CV SUMMARY:
{cv_text[:2000]}

{research_section}
INSTRUCTIONS:
1. Address the hiring manager (use "Dear Hiring Manager" if name unknown)
2. Open with enthusiasm for {company} specifically — reference something unique about them
3. In 2-3 paragraphs, connect your experience directly to the job requirements
4. Use specific achievements from your CV that match the role
5. Close with a call to action for an interview
6. Keep it to 250-350 words
7. Be authentic, not robotic — avoid cliches like "I am writing to express my interest"

Return only the cover letter text."""

    return _call_ai(prompt)


def _build_cv_text(parsed_cv: ParsedCV) -> str:
    """Convert a ParsedCV to a single text string for the AI prompt."""
    sections = parsed_cv.sections
    parts = []

    for section_name in ["summary", "skills", "experience", "education"]:
        content = sections.get(section_name, "")
        if content.strip():
            parts.append(f"--- {section_name.upper()} ---\n{content}")

    if parsed_cv.skills:
        parts.append(f"--- SKILLS LIST ---\n{', '.join(parsed_cv.skills)}")

    return "\n\n".join(parts)
