# Intent: theOne

- **Outcome:** Personal TUI — paste a link → grab → file on disk via yt-dlp
- **User:** Personal daily driver (not a product launch)
- **Why now:** Avoid yt-dlp flag/format friction; want paste → Enter with sensible defaults
- **Success:** Instant-feeling open/paste; fixed download folder; readable titles; audio-only supported; optional deeper controls later
- **Constraint:** Snappy TUI first; also improve download speed via yt-dlp flags where safe
- **Out of scope (v1):** Shipping to others, playlists/batches, accounts/login UI, web app
- **Stack:** Python 3.12+ · Textual · yt-dlp subprocess · uv · TOML config
- **CLI name:** `theOne` (package: `theone`)
