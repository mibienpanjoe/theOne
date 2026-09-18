# Contributing to theOne

Thanks for helping. theOne is a personal yt-dlp TUI; keep changes focused, testable, and easy to review.

## Setup

```bash
git clone https://github.com/mibienpanjoe/theOne.git
cd theOne
uv sync --group dev
uv run theOne          # run the TUI
uv run pytest          # tests (offline)
uv run ruff check .
uv run ruff format .
```

You also need a recent [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and [`ffmpeg`](https://ffmpeg.org/) on `PATH` for real downloads. Unit tests must not require the network.

## How we work

1. Open an issue for larger ideas when you can; small fixes can go straight to a PR.
2. Branch from `main`, keep commits focused (one concern per commit when practical).
3. Match existing style: typed Python 3.12+, `pathlib`, centralized yt-dlp argv in `downloader.py`.
4. Do **not** import the `yt_dlp` Python package into the app — subprocess only.
5. Do **not** commit cookies, browser profiles, downloaded media, or secrets.
6. Update docs when behavior changes: [`docs/01_requirements_prd.md`](docs/01_requirements_prd.md), [`docs/02_requirements_srs.md`](docs/02_requirements_srs.md), and the README if user-facing.

## Pull requests

- Describe **what** changed and **why**.
- Include tests for new logic (argv, formats, platforms, progress parsing, etc.).
- Confirm `uv run pytest` and `uv run ruff check .` pass locally.
- Screenshots help for TUI/UX changes.

## Scope guardrails

Please ask before:

- Adding heavy dependencies beyond Textual / textual-image / pytest / ruff
- Bundling yt-dlp, ffmpeg, or aria2c
- Playlist queues, multi-job downloads, or a web UI
- Changing the default filename template or audio format defaults

## Code of conduct

Be respectful. Assume good intent. No harassment or gatekeeping.

## License

By contributing, you agree your contributions are licensed under the [MIT License](LICENSE).
