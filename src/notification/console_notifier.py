"""Console-based notification using Rich."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn, TimeElapsedColumn

from src.utils.models import ScoredCV, ChangeDetail

console = Console()


def print_header(text: str):
    console.print(f"\n[bold cyan]=== {text} ===[/bold cyan]")


def print_job_results(results: list[dict]):
    """Display matched jobs in a formatted table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Match")
    table.add_column("Source")

    for i, r in enumerate(results, 1):
        job = r["job"]
        table.add_row(
            str(i),
            job["title"][:50],
            job["company"][:30],
            f"[green]{r['match_percentage']}[/green]",
            job.get("source", ""),
        )

    console.print(table)

    for i, r in enumerate(results, 1):
        reason = r.get("reason", "")
        console.print(Panel(
            f"[bold]{i}. {r['job']['title']}[/bold] @ {r['job']['company']}\n"
            f"   Match: [green]{r['match_percentage']}[/green] | "
            f"   URL: [blue]{r['job']['url']}[/blue]\n"
            f"   [dim]{reason}[/dim]",
            title=f"Match #{i}",
        ))


def print_cv_score(score_data: ScoredCV):
    scores = score_data.scores
    score_dict = scores.model_dump()
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Dimension")
    table.add_column("Score")
    for key, val in score_dict.items():
        color = "green" if val >= 0.7 else "yellow" if val >= 0.4 else "red"
        table.add_row(key.replace("_", " ").title(), f"[{color}]{val}[/{color}]")
    console.print(table)

    suggestions = score_data.suggestions
    if suggestions:
        console.print("\n[bold yellow]Suggestions:[/bold yellow]")
        for s in suggestions:
            console.print(f"  • {s}")


def print_improvement_diff(changes: list[ChangeDetail]):
    for c in changes:
        console.print(
            f"  • {c.section}: {c.original_length} → {c.new_length} chars"
        )


def create_progress() -> Progress:
    """Create a standard Rich Progress bar for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def status_spinner(text: str):
    """Context manager for a simple status spinner.

    Usage:
        with status_spinner("Parsing CV..."):
            do_slow_thing()
    """
    return console.status(f"[bold cyan]{text}[/bold cyan]", spinner="dots")
