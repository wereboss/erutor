# Erutor

**Erutor** is a lightweight Python-based movie and TV show metadata fetcher and NFO generator designed for **Kodi**, **Jellyfin**, and **Emby**.

## Highlights

- **Zero-Key Out of the Box**: Works immediately without signing up for any API keys.
  - **TV Shows**: Fetches complete series metadata, season names, episode guides, air dates, and episode thumbnails using **TVMaze** (100% free, generous rate limits). Also extracts cross-referenced IMDb and TVDB IDs!
  - **Movies**: Uses IMDb Suggest API + Wikipedia Summary API to retrieve titles, release years, IMDb IDs, plots, cast, directors, writers, genres, and high-resolution posters.
- **Kodi / Jellyfin / Emby XML Standard**: Generates fully compliant `.nfo` files:
  - `movie.nfo`
  - `tvshow.nfo`
  - `Season X/season.nfo`
  - `Season X/<Show> - SxxExx - <Title>.nfo`
- **Automatic Artwork Fetching**: Downloads `poster.jpg`, `fanart.jpg`, season posters, and per-episode `<episode>-thumb.jpg`.
- **Polished CLI UX**: Built with **Typer** and **Rich** featuring interactive search selection, progress spinners, and summary cards.
- **Optional Free API Key Upgrades**: Easily configure free TMDB or OMDb API keys to unlock 4K backdrops, Rotten Tomatoes critics scores, and TMDB IDs.

---

## Installation

```bash
# Clone the repository
cd erutor

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

---

## Quick Start

### 1. Fetch Movie Metadata
```bash
# Search by title and release year
erutor movie "A Scanner Darkly" --year 2006 --output ./A.Scanner.Darkly.2006/

# Or look up directly by IMDb ID
erutor movie --id tt0405296 --output ./A.Scanner.Darkly.2006/
```

This creates:
```
A.Scanner.Darkly.2006/
├── movie.nfo
└── poster.jpg
```

### 2. Fetch TV Show Metadata (All Seasons & Episodes)
```bash
# Search and generate full TV hierarchy
erutor tv "Blackadder" --year 1983 --output ./Blackadder/
```

This creates:
```
Blackadder/
├── tvshow.nfo
├── poster.jpg
├── Season 1/
│   ├── season.nfo
│   ├── poster.jpg
│   ├── Blackadder - S01E01 - The Foretelling.nfo
│   ├── Blackadder - S01E01 - The Foretelling-thumb.jpg
│   └── ...
├── Season 2/
├── Season 3/
└── Season 4/
```

### 3. Check / Configure Optional API Keys
```bash
# View current settings and key status
erutor config show

# Set optional free keys (e.g. TMDB or OMDb)
erutor config set --tmdb-key <YOUR_TMDB_KEY> --omdb-key <YOUR_OMDB_KEY>
```

---

## Running Tests

```bash
pytest
```
