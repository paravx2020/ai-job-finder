"""Company research module — gathers intelligence about employers before applying.

Uses web search and AI summarization to build a company intelligence brief,
flagging potential concerns before application submission.
"""

from config import AI_MODEL, COMPANY_RED_FLAG_KEYWORDS
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── Web Search ───────────────────────────────────────────────────────────────


def _web_search_company(company_name: str, max_results: int = 5) -> list[dict]:
    """Search the web for recent news about a company.

    Uses DuckDuckGo HTML search (zero API key requirement).
    Falls back gracefully if web search is unavailable.

    Returns:
        List of dicts: [{"title": "...", "url": "...", "snippet": "..."}]
    """
    try:
        import requests
    except ImportError:
        logger.warning("requests not installed — skipping web search for company research")
        return []

    results = []
    query = f"{company_name} company news culture reviews"

    try:
        # Use DuckDuckGo's HTML endpoint (no API key needed, rate-limited)
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=10,
        )

        if resp.status_code != 200:
            return []

        # Simple HTML parsing without external deps
        from html.parser import HTMLParser

        class ResultParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.in_result = False
                self.in_title = False
                self.in_snippet = False
                self.current_title = ""
                self.current_snippet = ""
                self.current_url = ""

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "a" and "result__a" in attrs_dict.get("class", ""):
                    self.in_result = True
                    self.current_url = attrs_dict.get("href", "")
                if tag == "a" and self.in_result and "result__snippet" not in attrs_dict.get("class", ""):
                    self.in_title = True
                if tag == "a" and "result__snippet" in attrs_dict.get("class", ""):
                    self.in_snippet = True

            def handle_endtag(self, tag):
                if tag == "a" and self.in_title:
                    self.in_title = False
                if tag == "a" and self.in_snippet:
                    self.in_snippet = False

            def handle_data(self, data):
                if self.in_title:
                    self.current_title += data
                if self.in_snippet:
                    self.current_snippet += data

        parser = ResultParser()
        parser.feed(resp.text)

        # Fallback: regex-based extraction
        import re

        titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
        urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

        for i in range(min(len(titles), max_results)):
            results.append(
                {
                    "title": re.sub(r"<[^>]+>", "", titles[i]).strip() if i < len(titles) else "",
                    "url": urls[i].strip() if i < len(urls) else "",
                    "snippet": re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else "",
                }
            )

    except Exception as e:
        logger.warning(f"Web search for {company_name} failed: {e}")

    return results


# ── AI-Powered Research ──────────────────────────────────────────────────────


def _summarize_with_ai(company_name: str, search_results: list[dict], job_title: str) -> str:
    """Use AI to generate a concise company intelligence brief."""
    if not search_results:
        return _fallback_summary(company_name, job_title)

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('snippet', '')}" for r in search_results[:5]
    )

    prompt = f"""You are a career advisor researching a potential employer for a job applicant.

Company: {company_name}
Job being applied for: {job_title}

Web search results about this company:
{snippets if snippets else 'No results found.'}

Write a 100-200 word company intelligence brief covering:
1. What the company does (industry, products)
2. Recent news or notable events
3. Company culture indicators (from reviews/mentions)
4. Any potential concerns the applicant should be aware of

Be balanced and factual. If the search results are sparse, say so and give your best assessment based on what you know about the company name.

Return only the brief text."""

    try:
        from config import GEMINI_API_KEY, OPENAI_API_KEY

        if GEMINI_API_KEY:
            from google import genai

            client = genai.Client(api_key=GEMINI_API_KEY)
            resp = client.models.generate_content(model=AI_MODEL, contents=prompt)
            return resp.text.strip()

        elif OPENAI_API_KEY:
            from openai import OpenAI

            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a career advisor providing factual company intelligence briefs.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()

    except Exception as e:
        logger.warning(f"AI summarization failed for {company_name}: {e}")

    return _fallback_summary(company_name, job_title)


def _fallback_summary(company_name: str, job_title: str) -> str:
    """Generate a minimal summary when no external data is available."""
    return (
        f"Automated research for {company_name} could not retrieve external data at this time. "
        f"This company is hiring for {job_title}. "
        f"Recommend reviewing the company website and employee reviews on Glassdoor/Indeed "
        f"before the interview stage."
    )


# ── Red Flag Detection ───────────────────────────────────────────────────────


def _detect_red_flags(summary: str, search_results: list[dict]) -> list[str]:
    """Check company research for red flag keywords."""
    flags = []

    # Check summary
    summary_lower = summary.lower()
    for kw in COMPANY_RED_FLAG_KEYWORDS:
        kw = kw.strip()
        if kw and kw.lower() in summary_lower:
            flags.append(kw)

    # Check snippet texts
    for result in search_results:
        snippet = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        for kw in COMPANY_RED_FLAG_KEYWORDS:
            kw = kw.strip()
            if kw and kw.lower() in snippet and kw not in flags:
                flags.append(kw)

    return list(set(flags))  # deduplicate


# ── Main Interface ───────────────────────────────────────────────────────────


def research_company(company_name: str, job_title: str = "") -> dict:
    """Research a company before applying.

    Args:
        company_name: Name of the company
        job_title: Optional job title for context

    Returns:
        Dict with:
            - summary_brief: 100-200 word intelligence summary
            - sources: list of dicts with url/title/snippet
            - red_flags: list of red flag keywords found
    """
    logger.info(f"Researching company: {company_name}")

    search_results = _web_search_company(company_name)
    summary = _summarize_with_ai(company_name, search_results, job_title)
    red_flags = _detect_red_flags(summary, search_results)

    return {
        "summary_brief": summary,
        "sources": search_results,
        "red_flags": red_flags,
    }