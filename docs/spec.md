# Spec: theOne (personal yt-dlp TUI)

## Assumptions (correct me now)

1. **Name:** CLI entrypoint is `theOne`. Python package import path is `theone` (PEP 8). Display brand in the TUI is `theOne` / `THEONE`.
2. **yt-dlp & ffmpeg:** Already installed on PATH; we do not vendor them. App fails clearly if missing.
3. **Default mode:** Best available progressive/merged video (yt-dlp’s usual “best” path). Audio-only is an explicit toggle/shortcut, not the default.
4. **Audio format:** Prefer `m4a` / bestaudio; remux with ffmpeg when needed.
5. **Filenames:** Readable title template, e.g. `%(title).200B [%(id)s].%(ext)s`, with filesystem-safe sanitization.
6. **First-run:** If download dir is unset, prompt once and save to config; thereafter silent.
7. **Themes:** Light / dark / auto (follow terminal), toggled with `Ctrl+T` like the reference UI.
8. **Platforms:** Linux first (your machine); no Windows/mac packaging in v1.

→ Say what to change, or approve the spec as-is.

---

## Objective

Build a personal daily-driver TUI for downloading single videos (or audio-only) via yt-dlp.

**User:** You  
**Loop:** Paste URL → Enter → progress → file in a fixed folder with a clean title  
**Success:** Feels instant to open and start; deeper options only when requested; download speed improved via sensible yt-dlp flags where safe.

### Acceptance criteria (v1)

- [ ] Launch shows a centered home screen: title, tagline, platform line, labeled URL input, footer keyhints.
- [ ] Paste/type a URL + Enter starts a download with defaults (no flag hunting).
- [ ] Audio-only mode available (shortcut and/or toggle) without leaving the TUI.
- [ ] Download directory is configured once and reused from config.
- [ ] Output filenames are human-readable and filesystem-safe.
- [ ] Live progress (percent / speed / ETA when yt-dlp provides them).
- [ ] Clear errors if URL invalid, yt-dlp missing, or download fails.
- [ ] `Ctrl+C` quits; `Ctrl+T` cycles theme (`auto` / `dark` / `light`).
- [ ] Cold path avoids importing yt-dlp into the Python process (subprocess only).

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python ≥ 3.12 |
| Package/tooling | `uv` |
| TUI | Textual (latest stable) |
| Downloader | `yt-dlp` CLI via `asyncio` subprocess |
| Config | TOML under `~/.config/theOne/config.toml` |
| Tests | `pytest` + Textual pilot where useful |

---

## Commands

```bash
# Setup / global install (theOne on PATH via ~/.local/bin)
uv tool install --editable .

# Dev
uv sync --group dev
uv run theOne

# Quality
uv run pytest
uv run ruff check .
uv run ruff format .
```

---

## Project Structure

```
pyproject.toml          # project metadata, entrypoint theOne
README.md               # install + usage (minimal)
docs/
  01_requirements_prd.md
  02_requirements_srs.md
  spec.md               # implementation notes / stack (companion)
tasks/
  plan.md               # implementation plan (after spec approval)
  todo.md               # task checklist
src/theone/
  __init__.py
  __main__.py           # python -m theone
  app.py                # Textual App + screens
  widgets/              # input bar, progress, etc.
  config.py             # load/save TOML config
  downloader.py         # yt-dlp argv builder + subprocess runner
  naming.py             # output template / sanitization helpers
tests/
  test_config.py
  test_downloader_argv.py
  test_naming.py
```

---

## Code Style

- Package: `theone`; modules short and verb-oriented (`config`, `downloader`).
- Public functions typed; prefer `pathlib.Path`.
- No business logic in widgets — widgets call services.
- Subprocess argv built in one place (`build_yt_dlp_args(...)`) so tests can assert flags without network.

```python
def build_yt_dlp_args(
    url: str,
    *,
    download_dir: Path,
    audio_only: bool,
    concurrent_fragments: int = 4,
) -> list[str]:
    args = [
        "yt-dlp",
        "--no-playlist",
        "--newline",
        "--progress",
        "-N", str(concurrent_fragments),
        "-P", str(download_dir),
        "-o", "%(title).200B [%(id)s].%(ext)s",
        "--restrict-filenames",  # or custom sanitization — decide in plan
    ]
    if audio_only:
        args += ["-x", "--audio-format", "m4a", "--audio-quality", "0"]
    args.append(url)
    return args
```

---

## Testing Strategy

| Level | What |
|-------|------|
| Unit | Argv builder, config load/save defaults, filename template helpers |
| Integration | Mock subprocess: progress lines parsed into UI state (no real network in CI) |
| Manual | Real one-shot download against a short public URL on your machine |

Coverage target: high on `downloader` / `config` / `naming`; no requirement to pixel-test the full TUI.

---

## Boundaries

**Always**
- Keep yt-dlp out of the import graph for the app entry (subprocess only).
- Fail with an actionable message if `yt-dlp` (or ffmpeg when needed) is missing.
- Update this spec when behavior or defaults change.

**Ask first**
- Adding dependencies beyond Textual / tomllib-or-tomli / pytest / ruff.
- Bundling yt-dlp or aria2c.
- Playlist / batch / login / cookies UI.
- Changing the default output template or audio format.

**Never**
- Commit secrets, cookies, or downloaded media.
- Scrape or reimplement site extractors — yt-dlp only.
- Block the UI thread on downloads.

---

## UI (v1)

Centered composition, dark-first:

1. **Brand:** `THEONE` (ASCII/large text)
2. **Tagline:** e.g. `grab any video. paste. grab. done.`
3. **Platforms line:** short static hint (`youtube · x · instagram · … · yt-dlp`)
4. **Input:** bordered field labeled `Paste a link`, prompt `>`, trailing `grab` action affordance
5. **Footer:** `⏎ grab` · `^c quit` · `^t theme:…` · audio toggle hint (e.g. `^a audio`)
6. **Brand wordmark:** ASCII reads `theOne` (not `THEONE`)

During download: replace or overlay progress (title, %, speed, ETA, destination path). On success: short confirmation + ready for next paste.

---

## Config (v1)

`~/.config/theOne/config.toml`:

```toml
download_dir = "/home/you/Videos/theOne"
theme = "auto"          # auto | dark | light
audio_only = false
concurrent_fragments = 8
quality = "best"        # best | 1080 | 720
use_aria2c = false
```

History: `~/.config/theOne/history.json`

---

## Success Criteria

1. `uv run theOne` opens the TUI in under ~1s on a warm machine (no yt-dlp import).
2. First run can set `download_dir`; later runs remember it.
3. Video and audio-only paths both produce a file in that directory with a readable name.
4. Progress updates without freezing input for cancel (`Ctrl+C` / escape policy as implemented).
5. Unit tests pass without network.

---

## Out of scope (v1)

- Playlists / queues / concurrent jobs
- Account login or cookies manager UI (manual cookie file path may wait)
- Web UI, mobile, packaging for others
- Branding or UI assets from other download apps

## Resolved decisions

1. Unicode titles; strip only illegal filesystem characters (no `--restrict-filenames`).
2. Audio toggle: `Ctrl+A`; footer reflects mode.
3. After success: stay on home screen, clear URL, ready for next paste.

See `tasks/plan.md` and `tasks/todo.md`.
