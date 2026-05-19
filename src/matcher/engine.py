"""Job matching engine using sentence embeddings and AI scoring."""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import EMBEDDING_MODEL, MATCH_TOP_K, SIMILARITY_THRESHOLD
from src.utils.models import ParsedCV

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _embed(texts: list[str]) -> np.ndarray:
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True)


def _build_cv_profile(parsed_cv: ParsedCV) -> str:
    """Create a search-friendly text profile from parsed CV."""
    sections = parsed_cv.sections
    skills = parsed_cv.skills
    parts = [
        sections.get("summary", ""),
        sections.get("experience", ""),
        sections.get("education", ""),
        "Skills: " + ", ".join(skills),
    ]
    return "\n".join(p for p in parts if p.strip())


def match_jobs(
    parsed_cv: ParsedCV,
    jobs: list,
    top_k: int = MATCH_TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """Match CV against job postings using embedding similarity."""
    cv_profile = _build_cv_profile(parsed_cv)
    job_descriptions = [f"{j.title} {j.company} {j.description}" for j in jobs]

    if not job_descriptions:
        return []

    # Encode
    cv_vec = _embed([cv_profile])
    job_vecs = _embed(job_descriptions)

    # Compute similarity
    sims = cosine_similarity(cv_vec, job_vecs)[0]

    # Rank and filter
    ranked = []
    for idx, score in enumerate(sims):
        if score >= threshold:
            ranked.append((score, idx))

    ranked.sort(reverse=True, key=lambda x: x[0])
    ranked = ranked[:top_k]

    results = []
    for score, idx in ranked:
        job = jobs[idx]
        results.append({
            "job": {
                "title": job.title,
                "company": job.company,
                "url": job.url,
                "location": job.location,
                "salary": job.salary,
                "source": job.source,
            },
            "match_score": round(float(score), 3),
            "match_percentage": f"{round(score * 100, 1)}%",
            "reason": _generate_reason(parsed_cv, job, score),
        })

    return results


def _generate_reason(parsed_cv: ParsedCV, job, score: float) -> str:
    """Generate a human-readable explanation for the match."""
    skills = parsed_cv.skills
    matched_skills = [s for s in skills if s.lower() in job.description.lower()]

    parts = []
    if matched_skills:
        parts.append(f"Your skills match: {', '.join(matched_skills[:5])}")
    if score > 0.7:
        parts.append("Strong overall fit based on experience and requirements.")
    elif score > 0.5:
        parts.append("Moderate match — some skills align with job requirements.")

    return " | ".join(parts) if parts else "Potential fit — review details."
