"""Integration tests for JobFinder CLI commands.

Uses Click's CliRunner to invoke commands end-to-end with
mocked external services and an isolated test database.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base

# Guard against missing ML dependencies (transformers, torch)
try:
    from src.main import cli
except (ImportError, ModuleNotFoundError):
    pytest.skip(
        "Skipping integration tests: missing ML dependencies "
        "(sentence-transformers, transformers, torch). "
        "Install with: pip install sentence-transformers",
        allow_module_level=True,
    )


@pytest.fixture(autouse=True)
def test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Replace DB with in-memory SQLite for each test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("src.database.DB_PATH", db_path)
    monkeypatch.setattr("config.DB_PATH", db_path)
    
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    
    # Replace session factory
    monkeypatch.setattr("src.database.engine", engine)
    monkeypatch.setattr("src.database.SessionLocal", sessionmaker(bind=engine))
    
    yield
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_cv_pdf(tmp_path: Path) -> Path:
    """Create a mock PDF file for testing."""
    pdf = tmp_path / "resume.pdf"
    pdf.write_text("%PDF-1.4 mock resume\nSUMMARY\nExperienced engineer.\nSKILLS\nPython, Docker")
    return pdf


@pytest.fixture
def sample_cv_docx(tmp_path: Path) -> Path:
    """Create a mock DOCX file for testing (minimal valid bytes)."""
    docx = tmp_path / "resume.docx"
    # Minimal valid DOCX structure
    docx.write_bytes(
        b"PK\x03\x04\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00"
        b"word/document.xml\x00PK\x01\x02\x14\x00\x14\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00word/document.xmlPK\x05\x06"
        b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00"
    )
    return docx


# ── CLI Group Tests ─────────────────────────────────────────────────────────

class TestCLIGroup:
    """Tests for the CLI group itself."""

    def test_help_succeeds(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "JobFinder" in result.output

    def test_version_succeeds(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_verbose_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0


# ── Analyze Command Tests ──────────────────────────────────────────────────

class TestAnalyzeCommand:
    """Tests for the 'analyze' CLI command."""

    def test_analyze_missing_file(self, runner: CliRunner):
        """Analyze should fail with error for missing file."""
        result = runner.invoke(cli, ["analyze", "/nonexistent/cv.pdf"])
        assert result.exit_code != 0
        assert "does not exist" in result.output.lower()

    def test_analyze_invalid_extension(self, runner: CliRunner, tmp_path: Path):
        """Analyze should fail for unsupported file types."""
        txt = tmp_path / "cv.txt"
        txt.write_text("test")
        result = runner.invoke(cli, ["analyze", str(txt)])
        assert result.exit_code != 0

    @patch("src.cv_processor.parser.parse_cv")
    @patch("src.cv_processor.scorer.score_cv")
    @patch("src.cv_processor.improver.improve_cv")
    def test_analyze_basic_flow(
        self,
        mock_improve: MagicMock,
        mock_score: MagicMock,
        mock_parse: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
        sample_cv_pdf: Path,
    ):
        """Analyze should process a CV end-to-end with mocked internals."""
        # Mock parse_cv
        from src.utils.models import ParsedCV, ScoredCV, CVImprovement, ScoreDetail, ChangeDetail
        
        mock_parse.return_value = ParsedCV(
            raw_text="test",
            sections={"summary": "test", "experience": "test", "skills": "test"},
            skills=["python", "docker"],
            word_count=50,
        )
        mock_score.return_value = ScoredCV(
            scores=ScoreDetail(keyword_density=0.5, quantified_achievements=0.3,
                              section_completeness=0.8, ats_compatibility=0.6),
            overall=0.55,
            suggestions=["Add more metrics"],
        )
        mock_improve.return_value = CVImprovement(
            improved_sections={"summary": "Improved summary text"},
            changes=[ChangeDetail(section="summary", original_length=4, new_length=22)],
        )

        result = runner.invoke(cli, ["analyze", str(sample_cv_pdf)])
        
        # Should succeed
        assert result.exit_code == 0
        assert "Parsing" in result.output
        assert mock_parse.called
        assert mock_score.called
        assert mock_improve.called

    @patch("src.cv_processor.parser.parse_cv")
    @patch("src.cv_processor.scorer.score_cv")
    @patch("src.cv_processor.improver.improve_cv")
    def test_analyze_with_user(
        self,
        mock_improve: MagicMock,
        mock_score: MagicMock,
        mock_parse: MagicMock,
        runner: CliRunner,
        sample_cv_pdf: Path,
    ):
        """Analyze should work with --user flag."""
        from src.utils.models import ParsedCV, ScoredCV, CVImprovement
        
        mock_parse.return_value = ParsedCV(sections={"summary": "test"}, word_count=10)
        mock_score.return_value = ScoredCV()
        mock_improve.return_value = CVImprovement()

        result = runner.invoke(cli, [
            "analyze", str(sample_cv_pdf),
            "--user", "alice@example.com",
        ])
        assert result.exit_code == 0


# ── Search Command Tests ───────────────────────────────────────────────────

class TestSearchCommand:
    """Tests for the 'search' CLI command."""

    def test_search_missing_file(self, runner: CliRunner):
        result = runner.invoke(cli, ["search", "/nonexistent/cv.pdf"])
        assert result.exit_code != 0

    @patch("src.job_scraper.engine.search_all")
    @patch("src.cv_processor.parser.parse_cv")
    @patch("src.matcher.engine.match_jobs")
    def test_search_basic_flow(
        self,
        mock_match: MagicMock,
        mock_parse: MagicMock,
        mock_search: MagicMock,
        runner: CliRunner,
        sample_cv_pdf: Path,
    ):
        """Search should find and match jobs."""
        from src.utils.models import ParsedCV
        
        mock_parse.return_value = ParsedCV(
            sections={"summary": "test"},
            skills=["python", "react"],
            word_count=50,
        )
        mock_search.return_value = [
            MagicMock(
                title="Software Engineer",
                company="Tech Corp",
                description="Python, React job",
                url="https://example.com/job1",
                source="linkedin",
                salary="$100k",
                location="NYC",
                posted_date=None,
            )
        ]
        mock_match.return_value = [
            {
                "job": {"title": "Software Engineer", "company": "Tech Corp",
                        "url": "https://example.com/job1", "source": "linkedin",
                        "salary": "$100k", "location": "NYC"},
                "match_score": 0.85,
                "match_percentage": "85%",
                "reason": "Good skill match: python, react",
            }
        ]

        result = runner.invoke(cli, [
            "search", str(sample_cv_pdf),
            "--query", "software engineer",
            "--top-k", "3",
        ])
        
        assert result.exit_code == 0
        assert mock_parse.called
        assert mock_search.called
        assert mock_match.called


# ── List Command Tests ─────────────────────────────────────────────────────

class TestListCommand:
    """Tests for the 'list' CLI command."""

    def test_list_empty(self, runner: CliRunner):
        """List should show message when no applications exist."""
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0

    def test_list_with_status_filter(self, runner: CliRunner):
        result = runner.invoke(cli, ["list", "--status", "pending"])
        assert result.exit_code == 0

    def test_list_with_limit(self, runner: CliRunner):
        result = runner.invoke(cli, ["list", "--limit", "5"])
        assert result.exit_code == 0


# ── Stats Command Tests ────────────────────────────────────────────────────

class TestStatsCommand:
    """Tests for the 'stats' CLI command."""

    def test_stats_shows_counts(self, runner: CliRunner):
        """Stats should display summary counts."""
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0


# ── Profile Command Tests ──────────────────────────────────────────────────

class TestProfileCommand:
    """Tests for the 'profile' CLI command."""

    def test_profile_list_empty(self, runner: CliRunner):
        """Profile list should show message when no profiles."""
        result = runner.invoke(cli, ["profile"])
        assert result.exit_code == 0

    def test_profile_create(self, runner: CliRunner):
        """Profile should be created with email."""
        result = runner.invoke(cli, [
            "profile", "alice@example.com",
            "--name", "Alice",
            "--domain", "data science",
            "--location", "NYC",
        ])
        assert result.exit_code == 0

    def test_profile_list_after_create(self, runner: CliRunner):
        """Profile list should show created profiles."""
        # Create a profile first
        runner.invoke(cli, ["profile", "bob@example.com", "--name", "Bob"])
        # Then list
        result = runner.invoke(cli, ["profile"])
        assert result.exit_code == 0
