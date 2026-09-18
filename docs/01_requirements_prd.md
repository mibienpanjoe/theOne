# theOne — Product Requirements Document

Version: v1.0, 2026-09-18

## 1. Problem Statement

Downloading media with yt-dlp is powerful but friction-heavy: format codes, playlist flags, output templates, cookie/browser quirks, and site-specific gotchas. For a personal daily driver, that friction is the product. The user wants to paste a link, hit Enter, and get a cleanly named file in a known folder — with progress, cancel, and only the controls that matter (quality, audio-only, carousel slide). Opening a terminal and fighting argv should not be part of the loop.

## 2. Personas

### Primary — The Operator
A single Linux user who already has `yt-dlp` and `ffmpeg` on PATH. Comfortable in a terminal. Downloads from YouTube, Instagram, TikTok, X/Twitter, Threads, and other yt-dlp-supported sites for personal use. Wants: paste → grab, readable filenames, platform-separated folders, no web UI, no account product.

### Secondary — The Returning Operator
Same user across sessions. Wants: remembered download directory and preferences, URL history, predictable keyboard shortcuts, clear recovery hints when yt-dlp is stale or a site returns 403.

## 3. Solution Overview

theOne is a personal Textual TUI. The operator launches `theOne`, pastes a URL, and the app probes formats via yt-dlp subprocess (never importing yt-dlp into the Python process). YouTube-like sites get a format picker with an in-TUI thumbnail; Instagram/TikTok/X/Threads get a confirm screen with sharp preview and optional carousel navigation. Grab writes under the configured directory in a platform subfolder (`youtube/`, `instagram/`, …). Progress streams live; Esc cancels probe or download. Config and history live under `~/.config/theOne/`.

## 4. MVP Scope

### Home / launch
- Centered brand, tagline, platform hint line, paste-link input, grab affordance, footer key hints
- Themes: auto / dark / light (`Ctrl+T`)
- Clipboard paste (`Ctrl+V`), URL history (`↑` / `↓`)
- First run prompts once for download directory and persists it

### Probe & choose
- Async probe of URL metadata, thumbnails, and format choices
- YouTube (and similar): format list (best, height caps, audio-only) with in-TUI thumbnail
- Instant-best platforms (Instagram, TikTok, X, Threads): confirm screen instead of a long format menu
- Carousel posts: `←` / `→` to change slide; preview and grab target the current slide
- Prefer uncropped / full-frame thumbnail URLs when sites advertise square crops
- Optional stream preview via `mpv` (`p`) without saving

### Download
- Video (best or capped) and audio-only (`m4a`) paths via yt-dlp subprocess
- Image slides saved as files when the entry is image-only
- Concurrent fragments; optional aria2c; optional `cookies_from_browser`
- Live percent / speed / ETA when yt-dlp emits them; Esc cancels
- Output template: readable Unicode title + id; no `--restrict-filenames`
- Destination: `{download_dir}/{platform}/…`

### Config & ops
- TOML config: download dir, theme, quality preference, audio preference, fragments, aria2c, cookies browser
- History JSON of recent URLs
- Actionable errors for missing yt-dlp, outdated extractors, HTTP 403, missing ffmpeg

## 5. Out of Scope (for MVP)

- Multi-user product, packaging for distribution beyond personal `uv tool install`
- Playlists / queues / concurrent download jobs
- Account login UI or full cookies manager (browser cookie import string only)
- Web UI, mobile, or Windows/mac packaging focus
- Reimplementing site extractors (yt-dlp only)
- Auto-posting, uploading, or sharing downloaded media
- Bundling yt-dlp / ffmpeg / aria2c / mpv inside the app

## 6. Success Criteria

- Cold launch feels instant: no yt-dlp import on the app entry path
- Paste → Enter reaches probe → confirm/picker → file on disk with a readable name
- Downloads land under the chosen folder, separated by platform
- Carousel slides can be browsed and grabbed individually with matching preview
- Progress updates without freezing cancel
- Unit tests pass without network
- Operator can recover from common YouTube failures via documented hints (update yt-dlp, JS runtime, cookies)
