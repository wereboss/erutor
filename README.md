# Erutor

[![Release](https://img.shields.io/github/v/release/wereboss/erutor?display_name=tag)](https://github.com/wereboss/erutor/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Erutor** is a lightweight, zero-key movie and TV show metadata fetcher, recursive directory scanner, and NFO generator engineered for **Kodi**, **Jellyfin**, and **Emby**.

---

## Key Highlights

- **Zero-Key Out of the Box**: Operates immediately without requiring paid accounts or API keys.
  - **TV Series**: Comprehensive series metadata, season names, episode air dates, episode plots, and thumbnails via **TVMaze** (100% free with generous rate limits). Cross-references IMDb and TVDB IDs automatically!
  - **Movies**: Uses the IMDb Suggest API + Wikipedia API to resolve titles, release years, IMDb IDs, plots, cast, directors, writers, genres, and high-resolution posters.
- **Rich Metadata Tags (`<tag>`)**:
  - Automatically enriches NFO files with thematic keywords, locations, subgenres, and adaptation sources (e.g. `dystopian`, `cyberpunk`, `mass surveillance`, `based on novel or book`, `california`).
  - Supports custom user tags via the `--tag` / `-t` CLI option (e.g. `--tag 4K --tag Favorites`).
- **Universal Portable Binaries**:
  - Download a single self-contained executable (`erutor` or `erutor.pyz`) and run it directly on **macOS**, **Linux**, and media servers (Mac mini, NAS, etc.) without managing Python virtual environments or dependencies.
- **Safe & Non-Destructive Directory Scanner (`erutor scan`)**:
  - Recursively discovers movies and TV series across local folders.
  - Never touches, renames, or modifies your video files or folder hierarchy.
  - Conflict detection with interactive choices (skip existing, overwrite all, or cancel).
  - Real-time progress feedback with live spinners, item-by-item logs, and update counts (`Updated: 1 NFO, poster.jpg (3 preserved)`).
  - Automatically creates missing season directories upfront (`--create-missing-seasons`).
- **Interactive Disambiguation & ID Lookup**:
  - If a media item cannot be matched automatically, Erutor prompts you to enter an exact title, year, IMDb ID (`tt0405296` or `imdb:tt...`), TheTVDB ID (`tvdb:76736`), or TVMaze ID.
  - Built-in Wikidata bridging (`haswbstatement:P345`, `P4835`) for resolving obscure and punctuation-heavy titles (e.g. `Agatha Christie-Poirot`, `A Knight of the Seven Kingdoms`).
- **Resilient Network Stack & Diagnostics (`erutor doctor`)**:
  - Automatic DNS-over-HTTPS (DoH) fallback via Cloudflare (`1.1.1.1`) and Google (`8.8.8.8`) by direct IP when system DNS fails with macOS `[Errno 8]`.
  - Built-in SSL CA certificate verification using `certifi`.
  - Built-in `erutor doctor` diagnostic utility to test connectivity, DNS resolution, SSL certs, and media provider APIs.
- **Kodi / Jellyfin / Emby XML Compliant**: Generates standards-compliant `.nfo` files:
  - `movie.nfo`
  - `tvshow.nfo`
  - `Season X/season.nfo`
  - `Season X/<Show> - SxxExx - <Title>.nfo`
- **Automatic Artwork Fetching**: Downloads `poster.jpg`, `fanart.jpg`, season posters, and per-episode `<episode>-thumb.jpg`.
- **Optional Free API Key Upgrades**: Easily configure free TMDB or OMDb API keys to unlock 4K backdrops, Rotten Tomatoes critics scores, and TMDB keywords.

---

## Installation

### Option 1: Standalone Portable Binary (Recommended)

No installation or virtual environment needed. Download the single executable from the [Releases](https://github.com/wereboss/erutor/releases/latest) page:

```bash
# Download latest executable (macOS / Linux)
curl -LO https://github.com/wereboss/erutor/releases/latest/download/erutor
chmod +x erutor

# Test it
./erutor --help
```

Or download the universal Python ZipApp:
```bash
curl -LO https://github.com/wereboss/erutor/releases/latest/download/erutor.pyz
python3 erutor.pyz --help
```

### Option 2: Install via pip / git

```bash
# Clone repository
git clone https://github.com/wereboss/erutor.git
cd erutor

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

---

## Usage Guide

### 1. Scan a Media Directory (`erutor scan`)

Scan an entire movies or TV series directory recursively. Discovers all media, inspects existing metadata, and downloads missing NFOs and artwork:

```bash
# Scan a directory (prompts on conflict)
erutor scan "/Volumes/Media/Movies"

# Skip already existing metadata (only fetch missing files)
erutor scan "/Volumes/Media/Series" --skip-existing

# Force overwrite existing metadata and re-download artwork
erutor scan "/Volumes/Media/Movies" --force

# Add custom tags to all scanned items
erutor scan "/Volumes/Media/Movies" --tag "Remux" --tag "HDR"
```

### 2. Fetch Movie Metadata (`erutor movie`)

```bash
# Search by title and release year
erutor movie "A Scanner Darkly" --year 2006 --output ./A.Scanner.Darkly.2006/

# Direct lookup by IMDb ID
erutor movie --id tt0405296 --output ./A.Scanner.Darkly.2006/

# Add custom tags to movie metadata
erutor movie "Inception" -y 2010 --tag "Mind-Bending" --tag "Sci-Fi"
```

Generated folder structure:
```
A.Scanner.Darkly.2006/
├── movie.nfo
└── poster.jpg
```

### 3. Fetch TV Show Metadata (`erutor tv`)

Fetches series metadata, named seasons, and every episode guide in a single command:

```bash
# Search by show title
erutor tv "Blackadder" --year 1983 --output ./Blackadder/

# Direct lookup by TVDB ID or IMDb ID
erutor tv --id "tvdb:76736" --output ./Blackadder/
erutor tv --id "tt0084988" --output ./Blackadder/

# Add custom tags to show and episode metadata
erutor tv "Breaking Bad" --tag "Drama" --tag "Top 10"
```

Generated folder structure:
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

### 4. Inspect Title & Release Parsing (`erutor parse`)

Inspect how Erutor parses technical noise, resolution, codecs, and season/episode info from scene filenames:

```bash
erutor parse "Severance.S01E01.Good.News.About.Hell.1080p.ATVP.WEB-DL.DDP5.1.Atmos.H.264.mkv"
```

### 5. Run System & Network Diagnostics (`erutor doctor`)

Verify internet access, DNS resolution (with DoH check), SSL certificates, and connectivity to IMDb, TVMaze, and Wikipedia:

```bash
erutor doctor
```

### 6. Configure Optional API Keys (`erutor config`)

Erutor works 100% free out of the box. To optionally enrich movies with Rotten Tomatoes scores or TMDB backdrops:

```bash
# View configuration
erutor config show

# Set API keys
erutor config set --tmdb-key <YOUR_TMDB_KEY> --omdb-key <YOUR_OMDB_KEY>
```

---

## Metadata Tags (`<tag>`)

Erutor writes standard Kodi / Jellyfin / Emby XML tags:

```xml
  <tag>dystopian</tag>
  <tag>future</tag>
  <tag>california</tag>
  <tag>based on novel or book</tag>
  <tag>mass surveillance</tag>
  <tag>substance abuse</tag>
```

Tags are extracted from:
- **Free Providers**: Wikipedia thematic categories, TVMaze show types (`Scripted`, `Animation`, `Documentary`), genres, networks (`HBO`, `AMC`, `Netflix`), and language/anime indicators.
- **TMDB**: Full TMDB keywords when TMDB API key is provided.
- **CLI Options**: Any `--tag` or `-t` flag provided at runtime.

---

## Running Tests & Building

### Running the Test Suite
```bash
PYTHONPATH=src pytest
```

### Rebuilding Portable Binaries
```bash
./scripts/build_dist.sh
```
This builds standard wheels, source tarballs, and universal executables (`dist/erutor` and `dist/erutor.pyz`).

---

## License

MIT License. See [LICENSE](LICENSE) for details.
