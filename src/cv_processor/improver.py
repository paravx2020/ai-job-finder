"""AI-powered CV improvement using Gemini/OpenAI."""


from config import AI_MODEL, GEMINI_API_KEY, OPENAI_API_KEY
from src.utils.cache import cached_ai_call
from src.utils.models import ChangeDetail, CVImprovement, ParsedCV

# ── AI Client ────────────────────────────────────────────────────────────────

_ai_client = None


def _get_client():
    global _ai_client
    if _ai_client is not None:
        return _ai_client
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _ai_client = ("gemini", genai)
    elif OPENAI_API_KEY:
        from openai import OpenAI
        _ai_client = ("openai", OpenAI(api_key=OPENAI_API_KEY))
    else:
        raise RuntimeError("No AI API key found. Set GEMINI_API_KEY or OPENAI_API_KEY in .env")
    return _ai_client


@cached_ai_call(ttl=86400)
def _call_ai(prompt: str, model: str, section: str) -> str:
    client_type, client = _get_client()
    model_name = model or AI_MODEL

    if client_type == "gemini":
        genai = client
        m = genai.GenerativeModel(model_name)
        resp = m.generate_content(prompt)
        return resp.text.strip()

    elif client_type == "openai":
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": f"You are an expert resume writer improving the {section} section."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()

    return ""


# ── Improver Functions ───────────────────────────────────────────────────────

IMPROVEMENT_PROMPTS = {
    "summary": (
        "Rewrite the following professional summary to be more impactful. "
        "Use strong action-oriented language, include years of experience, "
        "key skills, and career highlights. Keep it 3-5 sentences:\n\n{text}"
    ),
    "experience": (
        "Rewrite the following work experience bullet points. For each point:\n"
        "1. Start with a strong action verb\n"
        "2. Include quantified results where possible\n"
        "3. Focus on achievements, not just responsibilities\n"
        "4. Use industry-standard keywords for {domain}\n\n"
        "Original:\n{text}"
    ),
    "skills": (
        "Reorganize the following skills list. Group by category "
        "(e.g., Languages, Frameworks, Tools, Soft Skills). "
        "Add any missing key skills relevant to {domain}:\n\n{text}"
    ),
}


def improve_section(section: str, text: str, domain: str = "software engineering") -> str:
    if not text.strip():
        return text
    prompt_template = IMPROVEMENT_PROMPTS.get(section, "Improve the following text for a resume:\n\n{text}")
    prompt = prompt_template.format(text=text, domain=domain)
    return _call_ai(prompt=prompt, model=AI_MODEL, section=section)


def improve_cv(parsed_cv: ParsedCV, domain: str = "software engineering") -> CVImprovement:
    """Improve all sections of a parsed CV. Returns improved sections + changes."""
    from src.notification.console_notifier import create_progress

    improved = {}
    changes = []
    sections = parsed_cv.sections
    sections_to_improve = ["summary", "experience", "skills"]

    with create_progress() as progress:
        task = progress.add_task("[cyan]Improving CV sections...", total=len(sections_to_improve))

        for section_name in sections_to_improve:
            progress.update(task, description=f"[cyan]Improving {section_name}...")
            original = sections.get(section_name, "")
            if not original.strip():
                progress.advance(task)
                continue
            new_text = improve_section(section_name, original, domain)
            if new_text and new_text != original:
                improved[section_name] = new_text
                changes.append({
                    "section": section_name,
                    "original_length": len(original),
                    "new_length": len(new_text),
                })
            progress.advance(task)

    return CVImprovement(improved_sections=improved, changes=[ChangeDetail(**c) for c in changes])
