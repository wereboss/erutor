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
from erutor.parser import TitleParser, VIDEO_EXTENSIONS
from erutor.scanner import DirectoryScanner

app = typer.Typer(
    name="erutor",
    help="Erutor: Lightweight movie & TV show metadata fetcher and NFO generator",
    add_completion=False,
)
config_app = typer.Typer(name="config", help="Manage Erutor configuration and API keys")
app.add_typer(config_app)

console = Console()


@app.command("parse")
def parse_cmd(
    name: str = typer.Argument(..., help="File name, folder name, or path to parse"),
):
    """Inspect how Erutor parses a file or folder name."""
    parsed = TitleParser.parse(name)
    table = Table(title=f"Parsed: {Path(name).name}", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Detected Value")

    table.add_row("Detected Title", f"[bold green]{parsed.title}[/bold green]")
    table.add_row("Media Type", f"[cyan]{parsed.media_type.upper()}[/cyan]")
    table.add_row("Year", str(parsed.year or "[dim]N/A[/dim]"))
    if parsed.season is not None:
        ep_str = f"S{parsed.season:02d}E{parsed.episode:02d}" if parsed.episode is not None else f"Season {parsed.season}"
        if parsed.episode_end:
            ep_str += f"-E{parsed.episode_end:02d}"
        table.add_row("Season / Episode", ep_str)
    if parsed.episode_title:
        table.add_row("Episode Title", parsed.episode_title)
    if parsed.resolution:
        table.add_row("Resolution", f"[yellow]{parsed.resolution}[/yellow]")
    if parsed.source:
        table.add_row("Source", parsed.source)
    if parsed.video_codec:
        table.add_row("Video Codec", parsed.video_codec)
    if parsed.audio_codec:
        table.add_row("Audio Codec", parsed.audio_codec)
    if parsed.release_group:
        table.add_row("Release Group", f"[magenta]{parsed.release_group}[/magenta]")

    console.print(table)


def resolve_movie_interactively(
    manager: ErutorManager,
    query: Optional[str] = None,
    year: Optional[int] = None,
    movie_id: Optional[str] = None,
) -> Optional[MovieMetadata]:
    """Interactively search and resolve a movie, prompting for an ID or exact title if not found."""
    curr_id = movie_id
    curr_query = query
    curr_year = year

    while True:
        # If ID is provided, fetch directly
        if curr_id:
            with console.status(f"[bold green]Fetching movie details for ID: {curr_id}...[/bold green]"):
                movie = manager.get_movie(curr_id)
            if movie:
                return movie
            console.print(f"[bold yellow]⚠️  Could not find movie metadata with ID:[/bold yellow] [cyan]{curr_id}[/cyan]")
            curr_id = None

        # Search by query
        results = []
        if curr_query:
            with console.status(f"[bold green]Searching for movie '{curr_query}'...[/bold green]"):
                results = manager.search_movies(curr_query, year=curr_year)

        if results:
            table = Table(title="Movie Search Results", show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="bold")
            table.add_column("Year", style="cyan", width=6)
            table.add_column("ID", style="green", width=12)
            table.add_column("Details", style="italic")

            for idx, r in enumerate(results[:8], 1):
                table.add_row(str(idx), r.title, str(r.year or ""), r.id, r.overview or "")

            console.print(table)
            console.print("[dim]Select a number (1-8), [bold]m[/bold] for manual search / enter ID, or [bold]s[/bold] to skip.[/dim]")
            valid_choices = [str(i) for i in range(1, min(len(results), 8) + 1)] + ["m", "s"]
            choice = Prompt.ask("[bold cyan]Choice[/bold cyan]", choices=valid_choices, default="1")

            if choice == "s":
                return None
            elif choice != "m":
                selected = results[int(choice) - 1]
                with console.status(f"[bold green]Fetching details for '{selected.title}' ({selected.id})...[/bold green]"):
                    movie = manager.get_movie(selected.id)
                if movie:
                    return movie
                console.print(f"[bold red]✗ Failed to load details for {selected.id}[/bold red]")

        # If no results or user chose manual search
        year_hint = f" ({curr_year})" if curr_year else ""
        console.print(f"[bold yellow]⚠️  No matches found for movie '{curr_query or 'Unknown'}'{year_hint}.[/bold yellow]")
        console.print("[dim]Enter an IMDb ID (e.g. tt0405296), TMDB ID, or exact title (or 's' to skip):[/dim]")
        user_input = Prompt.ask("[bold cyan]Search query / ID[/bold cyan]", default="s").strip()

        if not user_input or user_input.lower() in ("s", "skip", "q", "quit"):
            return None

        low = user_input.lower()
        if (
            low.startswith("tt")
            or low.startswith("imdb:")
            or low.startswith("tmdb:")
            or "imdb.com" in low
            or "themoviedb.org" in low
            or (low.isdigit() and len(low) >= 3)
        ):
            curr_id = user_input
            curr_query = None
            curr_year = None
        else:
            curr_id = None
            curr_query = user_input
            year_input = Prompt.ask("[bold cyan]Release year (optional, press Enter to skip)[/bold cyan]", default="").strip()
            curr_year = int(year_input) if year_input.isdigit() else None


def resolve_tvshow_interactively(
    manager: ErutorManager,
    query: Optional[str] = None,
    year: Optional[int] = None,
    show_id: Optional[str] = None,
) -> Optional[TVShowMetadata]:
    """Interactively search and resolve a TV show, prompting for an ID or exact title if not found."""
    curr_id = show_id
    curr_query = query
    curr_year = year

    while True:
        # If ID is provided, fetch directly
        if curr_id:
            with console.status(f"[bold green]Fetching TV show details for ID: {curr_id}...[/bold green]"):
                show = manager.get_tvshow(curr_id)
            if show:
                return show
            console.print(f"[bold yellow]⚠️  Could not find TV show metadata with ID:[/bold yellow] [cyan]{curr_id}[/cyan]")
            curr_id = None

        # Search by query
        results = []
        if curr_query:
            with console.status(f"[bold green]Searching for TV show '{curr_query}'...[/bold green]"):
                results = manager.search_tv(curr_query, year=curr_year)

        if results:
            table = Table(title="TV Show Search Results", show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="bold")
            table.add_column("Year", style="cyan", width=6)
            table.add_column("ID", style="green", width=10)
            table.add_column("Source", style="yellow", width=8)

            for idx, r in enumerate(results[:8], 1):
                table.add_row(str(idx), r.title, str(r.year or ""), r.id, r.source)

            console.print(table)
            console.print("[dim]Select a number (1-8), [bold]m[/bold] for manual search / enter ID, or [bold]s[/bold] to skip.[/dim]")
            valid_choices = [str(i) for i in range(1, min(len(results), 8) + 1)] + ["m", "s"]
            choice = Prompt.ask("[bold cyan]Choice[/bold cyan]", choices=valid_choices, default="1")

            if choice == "s":
                return None
            elif choice != "m":
                selected = results[int(choice) - 1]
                with console.status(f"[bold green]Fetching series and episode guide for '{selected.title}'...[/bold green]"):
                    show = manager.get_tvshow(selected.id)
                if show:
                    return show
                console.print(f"[bold red]✗ Failed to load details for {selected.id}[/bold red]")

        # If no results or user chose manual search
        year_hint = f" ({curr_year})" if curr_year else ""
        console.print(f"[bold yellow]⚠️  No matches found for TV show '{curr_query or 'Unknown'}'{year_hint}.[/bold yellow]")
        console.print("[dim]Enter an IMDb ID (e.g. tt0084988), TVDB ID (e.g. tvdb:76736), TVMaze ID, or exact title (or 's' to skip):[/dim]")
        user_input = Prompt.ask("[bold cyan]Search query / ID[/bold cyan]", default="s").strip()

        if not user_input or user_input.lower() in ("s", "skip", "q", "quit"):
            return None

        low = user_input.lower()
        if (
            low.startswith("tt")
            or low.startswith("tvdb:")
            or low.startswith("thetvdb:")
            or low.startswith("imdb:")
            or "thetvdb.com" in low
            or "imdb.com" in low
            or low.isdigit()
        ):
            curr_id = user_input
            curr_query = None
            curr_year = None
        else:
            curr_id = None
            curr_query = user_input
            year_input = Prompt.ask("[bold cyan]Premiere year (optional, press Enter to skip)[/bold cyan]", default="").strip()
            curr_year = int(year_input) if year_input.isdigit() else None


@app.command("movie")
def movie_cmd(
    query: Optional[str] = typer.Argument(None, help="Movie title to search, or file path, or IMDb ID"),
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

    video_filename: Optional[str] = None
    if query:
        path_candidate = Path(query)
        if path_candidate.is_file() or path_candidate.suffix.lower() in VIDEO_EXTENSIONS or "." in path_candidate.name:
            parsed = TitleParser.parse(query)
            if parsed.title:
                console.print(f"[dim]Auto-detected from filename:[/dim] [cyan]{parsed.title}[/cyan] ({parsed.year or 'Year unknown'})")
                query = parsed.title
                if not year and parsed.year:
                    year = parsed.year
                if path_candidate.is_file() or path_candidate.suffix.lower() in VIDEO_EXTENSIONS:
                    video_filename = path_candidate.name
                    if path_candidate.is_file() and output is None:
                        output = path_candidate.parent

    movie_id = id
    if not movie_id and query and query.startswith("tt") and query[2:].isdigit():
        movie_id = query
        query = None

    if not movie_id and not query:
        query = Prompt.ask("[bold cyan]Enter movie title[/bold cyan]")
        if not year:
            year_str = Prompt.ask("[bold cyan]Enter release year (optional)[/bold cyan]", default="")
            if year_str.strip().isdigit():
                year = int(year_str.strip())

    movie = resolve_movie_interactively(manager, query=query, year=year, movie_id=movie_id)
    if not movie:
        console.print("[dim]Movie fetching canceled.[/dim]")
        raise typer.Exit(code=1)


    # Determine target directory
    if output is None:
        folder_name = f"{movie.title} ({movie.year})" if movie.year else movie.title
        target_dir = Path.cwd() / folder_name
    else:
        target_dir = output

    with console.status(f"[bold green]Saving metadata to {target_dir}...[/bold green]"):
        saved = manager.save_movie(movie, target_dir, force=force, video_filename=video_filename)

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

    if query:
        path_candidate = Path(query)
        if path_candidate.is_dir() or path_candidate.is_file() or path_candidate.suffix.lower() in VIDEO_EXTENSIONS:
            parsed = TitleParser.parse(query)
            if parsed.title:
                console.print(f"[dim]Auto-detected show name:[/dim] [cyan]{parsed.title}[/cyan] ({parsed.year or 'Year unknown'})")
                query = parsed.title
                if not year and parsed.year:
                    year = parsed.year
                if output is None:
                    output = path_candidate if path_candidate.is_dir() else path_candidate.parent

    show_id = id
    if not show_id and query and (query.startswith("tt") or query.isdigit() or query.lower().startswith("tvdb:")):
        show_id = query
        query = None

    if not show_id and not query:
        query = Prompt.ask("[bold cyan]Enter TV show title[/bold cyan]")
        if not year:
            year_str = Prompt.ask("[bold cyan]Enter premiere year (optional)[/bold cyan]", default="")
            if year_str.strip().isdigit():
                year = int(year_str.strip())

    show = resolve_tvshow_interactively(manager, query=query, year=year, show_id=show_id)
    if not show:
        console.print("[dim]TV show fetching canceled.[/dim]")
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


@app.command("scan")
def scan_cmd(
    directory: Path = typer.Argument(Path("."), help="Directory to recursively scan for media"),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite existing metadata"),
    skip_existing: bool = typer.Option(False, "--skip-existing", "-s", help="Skip existing metadata without prompting"),
    no_images: bool = typer.Option(False, "--no-images", help="Skip downloading posters and artwork"),
    create_missing_seasons: bool = typer.Option(
        True,
        "--create-missing-seasons/--no-missing-seasons",
        help="Create folders upfront for missing seasons in TV shows",
    ),
):
    """Scan a local directory, detect movies and TV shows, and generate metadata."""
    target_path = directory.resolve()
    if not target_path.exists() or not target_path.is_dir():
        console.print(f"[bold red]✗ Directory not found:[/bold red] {target_path}")
        raise typer.Exit(code=1)

    with console.status(f"[bold green]Scanning directory '{target_path}'...[/bold green]"):
        items = DirectoryScanner.scan(target_path)

    if not items:
        console.print(f"[bold yellow]No media files found in:[/bold yellow] {target_path}")
        raise typer.Exit(code=0)

    # Show table of discovered items
    table = Table(
        title=f"Discovered Media Items in {target_path.name or str(target_path)}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", width=7)
    table.add_column("Detected Title", style="bold")
    table.add_column("Year", style="cyan", width=6)
    table.add_column("Location")
    table.add_column("Existing Metadata", style="yellow")

    has_conflicts = False
    for idx, item in enumerate(items, 1):
        type_str = "[cyan]MOVIE[/cyan]" if item.media_type == "movie" else "[magenta]TV[/magenta]"
        try:
            loc_str = str(item.path.relative_to(target_path))
            if loc_str == ".":
                loc_str = item.path.name
        except ValueError:
            loc_str = str(item.path)

        meta_status = item.existing_metadata_desc
        if meta_status != "None":
            has_conflicts = True
            meta_display = f"[yellow]{meta_status}[/yellow]"
        else:
            meta_display = "[green]None (New)[/green]"

        table.add_row(str(idx), type_str, item.title, str(item.year or ""), loc_str, meta_display)

    console.print(table)

    # Conflict check & user validation
    should_overwrite = force
    if has_conflicts and not force and not skip_existing:
        console.print("\n[bold yellow]⚠️  Existing metadata (.nfo or images) was detected on one or more items.[/bold yellow]")
        console.print("[dim]Original video files and existing folders will never be modified.[/dim]")
        console.print("  [bold cyan]1[/bold cyan]: Skip existing metadata (only fetch missing files) [Recommended]")
        console.print("  [bold cyan]2[/bold cyan]: Overwrite all existing metadata")
        console.print("  [bold cyan]3[/bold cyan]: Cancel scan")
        choice = Prompt.ask(
            "[bold cyan]Select action[/bold cyan]",
            choices=["1", "2", "3"],
            default="1",
        )
        if choice == "1":
            should_overwrite = False
        elif choice == "2":
            should_overwrite = True
        else:
            console.print("[dim]Scan canceled by user.[/dim]")
            raise typer.Exit(code=0)

    config = Config.load()
    if no_images:
        config.download_images = False
    manager = ErutorManager(config)

    total_nfo = 0
    total_images = 0
    total_skipped = 0

    for item in items:
        if item.media_type == "movie":
            with console.status(f"[bold green]Searching for '{item.title}'...[/bold green]"):
                results = manager.search_movies(item.title, year=item.year)
                movie = manager.get_movie(results[0].id) if results else None

            if not movie:
                console.print(f"\n[bold yellow]⚠️  Could not automatically find movie:[/bold yellow] [bold cyan]{item.title}[/bold cyan] ({item.year or 'Year unknown'})")
                console.print(f"[dim]Location: {item.path}[/dim]")
                movie = resolve_movie_interactively(manager, query=item.title, year=item.year)

            if not movie:
                console.print(f"[dim]Skipping movie '{item.title}'...[/dim]\n")
                continue

            video_filename = item.video_file.name if item.video_file else None
            saved = manager.save_movie(movie, item.path, force=should_overwrite, video_filename=video_filename)
            total_nfo += 1 if "nfo" in saved else 0
            total_images += (1 if "poster" in saved else 0) + (1 if "fanart" in saved else 0)

        elif item.media_type == "tv":
            with console.status(f"[bold green]Searching for TV show '{item.title}'...[/bold green]"):
                results = manager.search_tv(item.title, year=item.year)
                show = manager.get_tvshow(results[0].id) if results else None

            if not show:
                console.print(f"\n[bold yellow]⚠️  Could not automatically find TV show:[/bold yellow] [bold cyan]{item.title}[/bold cyan] ({item.year or 'Year unknown'})")
                console.print(f"[dim]Location: {item.path}[/dim]")
                show = resolve_tvshow_interactively(manager, query=item.title, year=item.year)

            if not show:
                console.print(f"[dim]Skipping TV show '{item.title}'...[/dim]\n")
                continue

            # Build episode mapping from scanned items
            episodes_map: dict[tuple[int, int], Path] = {}
            for s_num, ep_list in item.seasons.items():
                for ep_item in ep_list:
                    episodes_map[(ep_item.season_number, ep_item.episode_number)] = ep_item.path


                saved = manager.save_tvshow(
                    show,
                    item.path,
                    force=should_overwrite,
                    existing_episodes_map=episodes_map,
                    create_missing_seasons=create_missing_seasons,
                )
                total_nfo += len(saved.get("nfo", []))
                total_images += len(saved.get("images", []))
                total_skipped += len(saved.get("skipped", []))

    summary_text = (
        f"[bold]Total Media Items Scanned:[/bold] {len(items)}\n"
        f"[bold]New NFO Files Written:[/bold] {total_nfo}\n"
        f"[bold]New Images Saved:[/bold] {total_images}\n"
        f"[bold]Existing Files Preserved (Skipped):[/bold] {total_skipped}"
    )
    console.print(Panel(summary_text, title="[bold green]✓ Scan & Metadata Generation Complete[/bold green]", expand=False))


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
