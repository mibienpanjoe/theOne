# theOne — Software Requirements Specification

Version: v1.0, 2026-09-18

## Normative Vocabulary

- **MUST / MUST NOT / REQUIRED**: Absolute requirement. The system fails if violated.
- **SHOULD / SHOULD NOT**: Recommended. Deviation permitted with documented justification.
- **MAY**: Optional capability.

## Actors

| Actor | Description |
|-------|-------------|
| Operator | The human user; pastes URLs, chooses formats/slides, owns the download folder |
| TUI | Textual app (`theOne` / package `theone`) presenting home, confirm, and picker screens |
| yt-dlp | External CLI invoked only via subprocess for probe and download |
| ffmpeg | External tool used by yt-dlp for merges / audio extraction when needed |
| Terminal graphics | Kitty TGP, Sixel, or half-cell path used by `textual-image` for in-TUI thumbnails |
| mpv | Optional external player for non-saving stream preview |
| Config store | `~/.config/theOne/config.toml` and `history.json` |

## Functional Requirements

### FR-010: Launch and home

- **FR-011**: The CLI entrypoint MUST be `theOne`; the Python package MUST be `theone`.
- **FR-012**: Launch MUST present a centered home screen with brand, tagline, platforms hint, URL input, and footer key hints.
- **FR-013**: If `download_dir` is unset, the app MUST prompt once, persist the choice, and MUST NOT re-prompt on later launches unless config is cleared.
- **FR-014**: `Ctrl+T` MUST cycle theme among `auto`, `dark`, and `light`. `auto` SHOULD follow terminal light/dark preference when detectable.
- **FR-015**: `Ctrl+V` SHOULD paste the first line of the system clipboard into the URL field when a clipboard helper is available.
- **FR-016**: `↑` / `↓` on the home URL field SHOULD walk persisted URL history.

### FR-020: Probe

- **FR-021**: Probe and download MUST invoke `yt-dlp` as an external process. The app entry path MUST NOT import the `yt_dlp` Python package.
- **FR-022**: Probe MUST collect title, uploader (when present), duration (when present), thumbnail candidates, format choices, extractor identity, and carousel entries when yt-dlp returns a playlist of slides.
- **FR-023**: For Instagram / TikTok / X / Threads (host or extractor), the app MUST expand playlist/carousel entries when probing. For YouTube watch URLs, probe MUST NOT expand related playlists (`--no-playlist` or equivalent).
- **FR-024**: Image-only carousel entries MUST still probe successfully (ignore missing AV formats when expanding those playlists).
- **FR-025**: If `yt-dlp` is missing from PATH, the app MUST show an actionable install hint and MUST NOT hang.

### FR-030: Format selection UX

- **FR-031**: For YouTube-like URLs, after probe the app MUST show a format picker (best, height-capped video options when available, audio-only) with an in-TUI thumbnail when one can be fetched.
- **FR-032**: For instant-best platforms (Instagram, TikTok, X, Threads), after probe the app MUST show a confirm screen (not a long format list) with thumbnail and grab confirmation.
- **FR-033**: `Ctrl+A` MUST prefer audio-only in the picker defaults / confirm audio path where the current item is video.
- **FR-034**: `Ctrl+Q` MUST cycle preferred quality among `best`, `1080`, and `720` for subsequent picks.
- **FR-035**: Esc MUST dismiss confirm/picker modals and MUST cancel an in-flight probe without starting a download.

### FR-040: Carousel

- **FR-041**: When a post has multiple media items, confirm MUST allow `←` / `→` (and SHOULD allow `h` / `l`) to change the current slide.
- **FR-042**: Preview thumbnail MUST refresh for the current slide (cached per index when already fetched).
- **FR-043**: Grab MUST download only the current slide (playlist item index for AV; image file for image slides).

### FR-050: Thumbnails and preview

- **FR-051**: In-TUI thumbnails MUST use `textual-image` with Kitty TGP when available, else Sixel when supported, else truecolor half-cell. Unicode dither MUST NOT be used as the primary path.
- **FR-052**: Thumbnail URL ranking MUST prefer larger, uncropped candidates; Instagram square-crop CDN markers (`c0.` / equal `sNxN` crops) MUST be penalized relative to full-frame display URLs when both exist.
- **FR-053**: Thumbnail widgets on confirm/picker SHOULD be horizontally centered in the dialog.
- **FR-054**: When `mpv` is installed, `p` MAY open a non-saving stream preview of the page URL for video items.
- **FR-055**: Thumbnail HTTP fetches for Instagram SHOULD send an appropriate Referer when required by the CDN.

### FR-060: Download

- **FR-061**: Video downloads MUST use yt-dlp with `--newline` progress, concurrent fragments from config, and the shared output template `%(title).200B [%(id)s].%(ext)s` (or equivalent).
- **FR-062**: Filenames MUST keep Unicode; the app MUST NOT pass `--restrict-filenames`.
- **FR-063**: Audio-only grabs MUST extract to `m4a` (best audio) via yt-dlp/`ffmpeg` as configured in the downloader argv builder.
- **FR-064**: Image slides MUST save under the platform destination directory with a filesystem-safe stem; direct URL download SHOULD be tried before yt-dlp thumbnail fallback.
- **FR-065**: The effective download directory MUST be `download_dir / platform_subdir(url, extractor)` with folders such as `youtube`, `instagram`, `tiktok`, `x`, `threads`, and a host- or extractor-derived name otherwise.
- **FR-066**: Esc during download MUST cancel the subprocess job and report cancelled.
- **FR-067**: On success the home URL field SHOULD clear, history SHOULD record the URL, and status SHOULD show the destination path.
- **FR-068**: Optional config `use_aria2c` and `cookies_from_browser` MUST be honored when building argv when those tools/browsers are available.

### FR-070: Progress and errors

- **FR-071**: Progress lines from yt-dlp SHOULD update the status area with percent, speed, and title when parseable.
- **FR-072**: Outdated-extractor / nsig-style failures SHOULD surface a short “update yt-dlp” message rather than a raw traceback dump.
- **FR-073**: HTTP 403 failures SHOULD mention JS runtime, cookies-from-browser, and yt-dlp update as recovery hints.

## Business Rules

| ID | Rule |
|----|------|
| BR-01 | yt-dlp remains the only site extractor; theOne never scrapes or reverse-engineers CDNs beyond choosing among URLs yt-dlp already exposed. |
| BR-02 | Default grab quality is “best” unless the operator’s quality preference or an explicit format choice says otherwise. |
| BR-03 | Instant-best platforms skip the long format menu; YouTube-like platforms use the picker. |
| BR-04 | Platform folder names are stable short slugs (`x` for Twitter/X, not `twitter`). |
| BR-05 | Config and history are per-machine under `~/.config/theOne/`; secrets/cookies files MUST NOT be committed. |
| BR-06 | One grab at a time in the TUI (exclusive download worker); no concurrent job queue in MVP. |

## Non-Functional Constraints

### Performance
- Home screen SHOULD open in under ~1s on a warm machine without contacting the network.
- Probe and download I/O MUST be async / subprocess-based so the UI thread is not blocked.

### Portability
- REQUIRED runtime: Python ≥ 3.12, Linux-first terminal.
- REQUIRED external tools: `yt-dlp` on PATH; `ffmpeg` for merges/audio.
- OPTIONAL: clipboard helpers, `aria2c`, `mpv`, `deno`/`node` for YouTube JS challenges.

### Reliability
- Argv construction for yt-dlp MUST be centralized so unit tests can assert flags without network.
- Tests MUST run offline in CI (mock subprocess / fixtures); real downloads are manual only.

### Privacy & security
- MUST NOT commit cookies, browser profiles, or downloaded media.
- `cookies_from_browser` MAY read the operator’s local browser cookie store via yt-dlp; theOne MUST NOT upload those cookies.
- Network access is only to destinations the operator requested (probe/download/thumbnail/preview).

### UX
- Footer hints SHOULD stay single-line / non-wrapping where possible.
- Errors MUST be readable in the status area without requiring log diving for common cases.

## Error Cases

| ID | Trigger | Required Behavior |
|----|---------|-------------------|
| ERR-01 | `yt-dlp` not on PATH | Show install hint (`uv tool install yt-dlp`); abort probe/download |
| ERR-02 | Probe fails / extractor outdated | Show short recovery message; clear busy state; keep URL editable |
| ERR-03 | Operator presses Esc during probe | Cancel probe; status cancelled; no modal |
| ERR-04 | Operator presses Esc during download | Cancel job; status cancelled |
| ERR-05 | Operator dismisses confirm/picker | Status cancelled; focus URL input |
| ERR-06 | Image slide has no URL | Show “No image URL”; do not start empty download |
| ERR-07 | `mpv` missing on preview | Notify that preview is unavailable |
| ERR-08 | HTTP 403 from CDN | Surface recovery hints (JS runtime, cookies, update yt-dlp, lower quality) |
| ERR-09 | `ffmpeg` missing when merge/extract needed | Surface ffmpeg hint from yt-dlp error formatting |
| ERR-10 | Thumbnail URLs fail | Show note / empty thumb; still allow format choice and grab |

## Traceability

| PRD area | SRS |
|----------|-----|
| Home / launch | FR-010 |
| Probe & choose | FR-020, FR-030 |
| Carousel | FR-040 |
| Thumbnails / preview | FR-050 |
| Download + platform folders | FR-060, BR-04 |
| Config / errors | FR-014, FR-070, ERR-* |
| Out of scope (product) | BR-01, BR-06, non-goals in PRD §5 |
