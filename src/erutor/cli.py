"""Command-line interface for Erutor using Typer and Rich."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from erutor.config import Config
from erutor.manager import ErutorManager

app = typer.Typer(
    name="erutor",
    help="Erutor: Lightweight movie & TV show metadata fetcher and NFO generator",
    add_completion=False,
)
config_app = typer.Typer(name="config", help="Manage Erutor configuration and API keys")
app.add_typer(config_app)

console = Console()


@app.command("movie")
def movie_cmd(
    query: Optional[str] = typer.Argument(None, help="Movie title to search, or IMDb ID (e.g. tt0405296)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Release year filter"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output directory"),
    id: Optional[str] = typer.Option(None, "--id", help="Direct IMDb/TMDB ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite existing files and re-download artwork"),
    no_images: bool = typer.Option(False, "--no-images", help="Skip downloading posters and artwork"),
):
    """Fetch movie metadata, generate movie.nfo, and download artwork."""
    config = Config.load()
    if no_images:
        config.download_images = False
    manager = ErutorManager(config)

    movie_id = id
    if not movie_id and query and query.startswith("tt") and query[2:].isdigit():
        movie_id = query

    if not movie_id:
        if not query:
            query = Prompt.ask("[bold cyan]Enter movie title[/bold cyan]")
            if not year:
                year_str = Prompt.ask("[bold cyan]Enter release year (optional)[/bold cyan]", default="")
                if year_str.strip().isdigit():
                    year = int(year_str.strip())

        with console.status(f"[bold green]Searching for movie '{query}'...[/bold green]"):
            results = manager.search_movies(query, year=year)

        if not results:
            console.print(f"[bold red]✗ No movies found for query:[/bold red] '{query}'")
            raise typer.Exit(code=1)

        if len(results) == 1:
            selected = results[0]
        else:
            table = Table(title="Search Results", show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="bold")
            table.add_column("Year", style="cyan", width=6)
            table.add_column("ID", style="green", width=12)
            table.add_column("Details", style="italic")

            for idx, r in enumerate(results[:8], 1):
                table.add_row(str(idx), r.title, str(r.year or ""), r.id, r.overview or "")

            console.print(table)
            choice = Prompt.ask(
                "[bold cyan]Select a result number[/bold cyan]",
                choices=[str(i) for i in range(1, min(len(results), 8) + 1)],
                default="1",
            )
            selected = results[int(choice) - 1]

        movie_id = selected.id

    with console.status(f"[bold green]Fetching details for ID: {movie_id}...[/bold green]"):
        movie = manager.get_movie(movie_id)

    if not movie:
        console.print(f"[bold red]✗ Failed to retrieve movie metadata for ID:[/bold red] {movie_id}")
        raise typer.Exit(code=1)

    # Determine target directory
    if output is None:
        folder_name = f"{movie.title} ({movie.year})" if movie.year else movie.title
        target_dir = Path.cwd() / folder_name
    else:
        target_dir = output

    with console.status(f"[bold green]Saving metadata to {target_dir}...[/bold green]"):
        saved = manager.save_movie(movie, target_dir, force=force)

    # Display clean summary panel
    details_text = (
        f"[bold]Title:[/bold] {movie.title}\n"
        f"[bold]Year:[/bold] {movie.year or 'N/A'}\n"
        f"[bold]IMDb ID:[/bold] {movie.imdb_id or 'N/A'}\n"
        f"[bold]Genres:[/bold] {', '.join(movie.genres) if movie.genres else 'N/A'}\n"
        f"[bold]Output Dir:[/bold] {target_dir}\n"
        f"[bold]Generated NFO:[/bold] {saved.get('nfo', 'N/A')}\n"
        f"[bold]Poster:[/bold] {saved.get('poster', 'Not downloaded')}"
    )
    console.print(Panel(details_text, title="[bold green]✓ Movie Metadata Generated[/bold green]", expand=False))


@app.command("tv")
def tv_cmd(
    query: Optional[str] = typer.Argument(None, help="TV show title to search, or ID (e.g. tt0084988 or 1072)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="First air date year filter"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output directory"),
    id: Optional[str] = typer.Option(None, "--id", help="Direct TVMaze/IMDb ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite existing files and re-download artwork"),
    no_images: bool = typer.Option(False, "--no-images", help="Skip downloading artwork"),
):
    """Fetch TV show metadata, generate tvshow.nfo, season.nfo, and episode NFOs."""
    config = Config.load()
    if no_images:
        config.download_images = False
    manager = ErutorManager(config)

    show_id = id
    if not show_id and query and (query.startswith("tt") or query.isdigit()):
        show_id = query

    if not show_id:
        if not query:
            query = Prompt.ask("[bold cyan]Enter TV show title[/bold cyan]")
            if not year:
                year_str = Prompt.ask("[bold cyan]Enter premiere year (optional)[/bold cyan]", default="")
                if year_str.strip().isdigit():
                    year = int(year_str.strip())

        with console.status(f"[bold green]Searching for TV show '{query}'...[/bold green]"):
            results = manager.search_tv(query, year=year)

        if not results:
            console.print(f"[bold red]✗ No TV shows found for query:[/bold red] '{query}'")
            raise typer.Exit(code=1)

        if len(results) == 1:
            selected = results[0]
        else:
            table = Table(title="TV Show Search Results", show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="bold")
            table.add_column("Year", style="cyan", width=6)
            table.add_column("ID", style="green", width=10)
            table.add_column("Source", style="yellow", width=8)

            for idx, r in enumerate(results[:8], 1):
                table.add_row(str(idx), r.title, str(r.year or ""), r.id, r.source)

            console.print(table)
            choice = Prompt.ask(
                "[bold cyan]Select a result number[/bold cyan]",
                choices=[str(i) for i in range(1, min(len(results), 8) + 1)],
                default="1",
            )
            selected = results[int(choice) - 1]

        show_id = selected.id

    with console.status(f"[bold green]Fetching full series and episode guide for ID: {show_id}...[/bold green]"):
        show = manager.get_tvshow(show_id)

    if not show:
        console.print(f"[bold red]✗ Failed to retrieve TV show metadata for ID:[/bold red] {show_id}")
        raise typer.Exit(code=1)

    # Determine target directory
    if output is None:
        target_dir = Path.cwd() / show.title
    else:
        target_dir = output

    with console.status(f"[bold green]Writing NFOs and assets to {target_dir}...[/bold green]"):
        saved = manager.save_tvshow(show, target_dir, force=force)

    summary_text = (
        f"[bold]Show:[/bold] {show.title} ({show.year or 'N/A'})\n"
        f"[bold]IMDb ID:[/bold] {show.imdb_id or 'N/A'}\n"
        f"[bold]TVDB ID:[/bold] {show.tvdb_id or 'N/A'}\n"
        f"[bold]Seasons:[/bold] {len(show.seasons)}\n"
        f"[bold]Episodes:[/bold] {len(show.episodes)}\n"
        f"[bold]Total NFO files written:[/bold] {len(saved['nfo'])}\n"
        f"[bold]Total Images saved:[/bold] {len(saved['images'])}\n"
        f"[bold]Directory:[/bold] {target_dir}"
    )
    console.print(Panel(summary_text, title="[bold green]✓ TV Series Metadata Generated[/bold green]", expand=False))


@config_app.command("show")
def config_show():
    """Display current Erutor settings and API keys status."""
    cfg = Config.load()
    table = Table(title="Erutor Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    def _mask(v: Optional[str]) -> str:
        if not v:
            return "[dim]Not configured[/dim]"
        return f"[green]{v[:4]}...{v[-3:]} (Configured)[/green]"

    table.add_row("TMDB API Key", _mask(cfg.tmdb_api_key))
    table.add_row("OMDb API Key", _mask(cfg.omdb_api_key))
    table.add_row("TVDB API Key", _mask(cfg.tvdb_api_key))
    table.add_row("Movie NFO File", cfg.movie_nfo_name)
    table.add_row("TV Show NFO File", cfg.tvshow_nfo_name)
    table.add_row("Season NFO File", cfg.season_nfo_name)
    table.add_row("Poster Name", cfg.poster_name)
    table.add_row("Fanart Name", cfg.fanart_name)
    table.add_row("Download Images", str(cfg.download_images))

    console.print(table)


@config_app.command("set")
def config_set(
    tmdb_key: Optional[str] = typer.Option(None, "--tmdb-key", help="Free TMDB API Key"),
    omdb_key: Optional[str] = typer.Option(None, "--omdb-key", help="Free OMDb API Key"),
):
    """Set API keys in ~/.config/erutor/config.toml."""
    config_dir = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "erutor"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"

    cfg = Config.load()
    if tmdb_key is not None:
        cfg.tmdb_api_key = tmdb_key.strip() or None
    if omdb_key is not None:
        cfg.omdb_api_key = omdb_key.strip() or None

    lines = ["[providers]"]
    if cfg.tmdb_api_key:
        lines.append(f'tmdb_api_key = "{cfg.tmdb_api_key}"')
    if cfg.omdb_api_key:
        lines.append(f'omdb_api_key = "{cfg.omdb_api_key}"')

    lines.append("\n[output]")
    lines.append(f'movie_nfo_name = "{cfg.movie_nfo_name}"')
    lines.append(f'poster_name = "{cfg.poster_name}"')
    lines.append(f'fanart_name = "{cfg.fanart_name}"')
    lines.append(f'download_images = {str(cfg.download_images).lower()}')

    with open(config_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    console.print(f"[bold green]✓ Configuration saved to {config_file}[/bold green]")


def main():
    app()


if __name__ == "__main__":
    main()
