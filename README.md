# theOne

Personal yt-dlp TUI — paste a link, grab, done.

## Requirements

- Python 3.12+ (via [uv](https://docs.astral.sh/uv/))
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) on your `PATH` — **recent** build (2025+). Distro packages are often years old and break on YouTube.
  ```bash
  uv tool install --force yt-dlp
  yt-dlp --version   # should NOT be 2022.x
  ```
  Optional: install a JS runtime (e.g. `deno`) for full YouTube format support — see [yt-dlp EJS wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
- [`ffmpeg`](https://ffmpeg.org/) (for merges / audio extraction)
- Optional: `wl-paste` or `xclip` (clipboard), `aria2c` (faster downloads)
- Optional: [`mpv`](https://mpv.io/) for stream preview (`p`)
- Thumbnails render in-TUI via [`textual-image`](https://github.com/lnqs/textual-image) (Kitty TGP / Sixel / half-cell fallback)

## Install (global `theOne` command)

From this repo:

```bash
uv tool install --editable .
```

That puts `theOne` on your PATH (usually `~/.local/bin`). Ensure that directory is on `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.bashrc if needed
theOne --version
theOne
```

Re-run `uv tool install --editable .` after pulling updates.

### Dev without global install

```bash
uv sync --group dev
uv run theOne
```

## Keys

| Key | Action |
|-----|--------|
| `Enter` | YouTube: format picker · IG/TikTok/X: preview confirm → grab |
| `←` `→` | carousel: previous / next slide (IG multi-image posts) |
| `p` | stream preview via mpv (no save) |
| `Ctrl+V` | paste URL from clipboard |
| `Ctrl+A` | prefer audio in the format picker |
| `Ctrl+Q` | prefer quality cap: best → 1080 → 720 |
| `Ctrl+T` | cycle theme: auto → dark → light |
| `Esc` | cancel picker or in-flight download |
| `↑` / `↓` | browse URL history / move in format list |
| `Ctrl+C` | quit |

Config: `~/.config/theOne/config.toml`  
History: `~/.config/theOne/history.json`

Downloads land under your chosen folder, split by platform (`youtube/`, `instagram/`, `tiktok/`, `x/`, …).

Optional in config:

```toml
use_aria2c = true
concurrent_fragments = 16
cookies_from_browser = "firefox"   # or chrome — helps with 403 / age gates
```

### HTTP 403 Forbidden

YouTube (and sometimes others) refused the media CDN URL. Typical causes:

1. No JS runtime for signature decryption → install `deno` or ensure `node` is on `PATH`
2. Login / age / region gate → set `cookies_from_browser` in config
3. Stale yt-dlp → `uv tool install --force yt-dlp`
4. Pick a lower quality and retry

## Tests

```bash
uv sync --group dev
uv run pytest
```
