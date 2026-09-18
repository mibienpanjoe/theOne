"""Textual UI for theOne."""

from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from theone.clipboard import looks_like_url, read_clipboard
from theone.config import (
    Config,
    ThemeName,
    cycle_quality,
    cycle_theme,
    load_config,
    save_config,
)
from theone.downloader import DownloadJob, YtDlpNotFoundError, download_image, run_download
from theone.formats import FormatChoice, ProbeResult, fetch_probe
from theone.history import load_history, push_history
from theone.platforms import prefers_instant_best, resolve_download_dir
from theone.preview import download_thumbnail, mpv_available, stream_preview
from theone.theme_detect import terminal_prefers_dark
from theone.thumb import make_thumb
from theone.widgets import KeyHints, LinkBar, render_brand

BRAND = render_brand("theOne")

TAGLINE = "grab any video. paste. grab. done."
PLATFORMS = "youtube · x · instagram · threads · tiktok · +1800 more"

THEONE_DARK = Theme(
    name="theone-dark",
    primary="#ffffff",
    secondary="#a3a3a3",
    accent="#ffffff",
    foreground="#fafafa",
    background="#000000",
    surface="#000000",
    panel="#0a0a0a",
    success="#fafafa",
    warning="#a3a3a3",
    error="#fafafa",
    dark=True,
    variables={
        "text-muted": "#737373",
        "footer-key-foreground": "#a3a3a3",
        "input-cursor-background": "#fafafa",
        "input-cursor-foreground": "#000000",
        "input-selection-background": "#ffffff 30%",
    },
)

THEONE_LIGHT = Theme(
    name="theone-light",
    primary="#000000",
    secondary="#525252",
    accent="#000000",
    foreground="#0a0a0a",
    background="#ffffff",
    surface="#ffffff",
    panel="#f5f5f5",
    success="#0a0a0a",
    warning="#525252",
    error="#0a0a0a",
    dark=False,
    variables={
        "text-muted": "#737373",
        "footer-key-foreground": "#525252",
        "input-cursor-background": "#0a0a0a",
        "input-cursor-foreground": "#ffffff",
        "input-selection-background": "#000000 20%",
    },
)


def progress_bar(percent: float, width: int = 28) -> str:
    pct = max(0.0, min(100.0, percent))
    filled = int(round(width * pct / 100.0))
    return f"{'█' * filled}{'░' * (width - filled)}"


class DownloadDirScreen(ModalScreen[Path | None]):
    """First-run prompt for the fixed download folder."""

    CSS = """
    DownloadDirScreen {
        align: center middle;
        background: $background 80%;
    }
    #dir-dialog {
        width: 64;
        height: auto;
        border: solid $foreground;
        background: $background;
        padding: 1 2;
    }
    #dir-dialog Label {
        margin-bottom: 1;
        color: $foreground;
    }
    #dir-dialog Input {
        border: solid $foreground;
        background: $background;
    }
    #dir-actions {
        margin-top: 1;
        height: auto;
        align: right middle;
    }
    #dir-actions Button {
        border: none;
        margin-left: 1;
        min-width: 10;
    }
    #dir-save {
        background: $foreground;
        color: $background;
        text-style: bold;
    }
    #dir-cancel {
        background: transparent;
        color: $text-muted;
    }
    """

    def __init__(self, initial: Path) -> None:
        super().__init__()
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Vertical(id="dir-dialog"):
            yield Label("Where should theOne save downloads?")
            yield Input(value=str(self._initial), id="dir-input")
            with Horizontal(id="dir-actions"):
                yield Button("Save", id="dir-save")
                yield Button("Cancel", id="dir-cancel")

    @on(Button.Pressed, "#dir-save")
    @on(Input.Submitted, "#dir-input")
    def save(self) -> None:
        raw = self.query_one("#dir-input", Input).value.strip()
        if not raw:
            self.notify("Pick a folder path", severity="error")
            return
        path = Path(raw).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.notify(f"Cannot create folder: {exc}", severity="error")
            return
        self.dismiss(path)

    @on(Button.Pressed, "#dir-cancel")
    def cancel(self) -> None:
        self.dismiss(None)


class ConfirmGrabScreen(ModalScreen[FormatChoice | None]):
    """Confirm grab for IG/TikTok/X — carousel-aware in-TUI preview."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel", show=False, priority=True),
        Binding("enter", "confirm", "grab", show=False, priority=True),
        Binding("left", "prev", "prev", show=False, priority=True),
        Binding("right", "next", "next", show=False, priority=True),
        Binding("h", "prev", "prev", show=False),
        Binding("l", "next", "next", show=False),
        Binding("p", "preview_stream", "preview", show=False),
        Binding("a", "audio", "audio", show=False),
    ]

    CSS = """
    ConfirmGrabScreen {
        align: center middle;
        background: $background 80%;
    }
    #confirm-dialog {
        width: 56;
        max-width: 100%;
        height: auto;
        border: solid $foreground;
        background: $background;
        padding: 1 2;
        align: center middle;
    }
    #confirm-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        height: auto;
        color: $foreground;
    }
    #confirm-meta {
        text-align: center;
        width: 100%;
        color: $text-muted;
        height: auto;
        margin-bottom: 0;
    }
    #confirm-dots {
        text-align: center;
        width: 100%;
        height: 1;
        color: $text-muted;
        margin-bottom: 1;
    }
    #confirm-thumb-wrap {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0 0 1 0;
    }
    #confirm-thumb {
        width: auto;
        height: 24;
        max-width: 100%;
    }
    #confirm-thumb.thumb-halfcell {
        height: 28;
    }
    #confirm-note {
        text-align: center;
        width: 100%;
        color: $text-muted;
        height: auto;
        margin-bottom: 1;
    }
    #confirm-hint {
        text-align: center;
        width: 100%;
        height: 1;
        color: $text-muted;
        text-wrap: nowrap;
    }
    """

    def __init__(
        self,
        probe: ProbeResult,
        *,
        thumb_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._probe = probe
        self._items = probe.items or ()
        self._index = 0
        self._thumb_path = thumb_path
        self._thumb_cache: dict[int, Path | None] = {}
        if thumb_path is not None and self._items:
            self._thumb_cache[0] = thumb_path
        self._previewing = False
        self._loading_thumb = False

    def _current(self):
        from theone.formats import MediaItem

        if self._items:
            return self._items[self._index]
        # Legacy single-probe fallback (should be rare).
        return MediaItem(
            index=1,
            kind="video",
            title=self._probe.title,
            thumbnail_urls=self._probe.thumbnail_urls,
            duration=self._probe.duration,
            choices=tuple(self._probe.choices),
        )

    def _best_choice(self, *, audio: bool = False) -> FormatChoice:
        item = self._current()
        if item.kind == "image":
            return item.choices[0]
        if audio:
            for choice in item.choices:
                if choice.audio_only:
                    return choice
        for choice in item.choices:
            if choice.format_spec == "bv*+ba/b":
                return choice
        return item.choices[0]

    def _dots_text(self) -> str:
        n = len(self._items)
        if n <= 1:
            return ""
        if n > 10:
            return f"{self._index + 1} / {n}"
        return " ".join("●" if i == self._index else "○" for i in range(n))

    def _meta_text(self) -> str:
        item = self._current()
        bits: list[str] = []
        if self._probe.uploader:
            bits.append(self._probe.uploader)
        bits.append(item.kind)
        if item.duration:
            bits.append(item.duration)
        if len(self._items) > 1:
            bits.append(f"{self._index + 1}/{len(self._items)}")
        return " · ".join(bits) or "best quality"

    def _hint_text(self) -> str:
        item = self._current()
        parts: list[str] = ["⏎ grab"]
        if len(self._items) > 1:
            parts.append("← →")
        if item.kind == "video":
            parts.append("a audio")
            if mpv_available():
                parts.append("p play")
        parts.append("esc")
        return " · ".join(parts)

    def compose(self) -> ComposeResult:
        from theone.thumb import HalfcellThumb, uses_halfcell

        title = self._probe.title or "Ready to grab"
        if len(title) > 48:
            title = title[:45] + "…"

        with Vertical(id="confirm-dialog"):
            yield Label(title, id="confirm-title")
            yield Label(self._meta_text(), id="confirm-meta")
            yield Label(self._dots_text(), id="confirm-dots")
            with Center(id="confirm-thumb-wrap"):
                if self._thumb_path is not None:
                    yield make_thumb(self._thumb_path, id="confirm-thumb")
                else:
                    classes = "thumb-halfcell" if uses_halfcell() else None
                    yield HalfcellThumb(None, id="confirm-thumb", classes=classes)
            yield Label(self._hint_text(), id="confirm-hint")

    def on_mount(self) -> None:
        self.focus()

    def action_confirm(self) -> None:
        self.dismiss(self._best_choice())

    def action_audio(self) -> None:
        if self._current().kind != "video":
            self.notify("This slide is an image", severity="information")
            return
        self.dismiss(self._best_choice(audio=True))

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_prev(self) -> None:
        if len(self._items) <= 1:
            return
        self._index = (self._index - 1) % len(self._items)
        self._refresh_slide()

    def action_next(self) -> None:
        if len(self._items) <= 1:
            return
        self._index = (self._index + 1) % len(self._items)
        self._refresh_slide()

    def _refresh_slide(self) -> None:
        self.query_one("#confirm-meta", Label).update(self._meta_text())
        self.query_one("#confirm-dots", Label).update(self._dots_text())
        self.query_one("#confirm-hint", Label).update(self._hint_text())
        cached = self._thumb_cache.get(self._index)
        if cached is not None:
            self._set_thumb(cached)
            return
        if self._loading_thumb:
            return
        self.run_worker(self._load_thumb_for_index(self._index), exclusive=True)

    def _set_thumb(self, path: Path | None) -> None:
        thumb = self.query_one("#confirm-thumb")
        if path is not None and path.is_file():
            thumb.image = str(path)  # type: ignore[attr-defined]
        else:
            thumb.image = None  # type: ignore[attr-defined]

    async def _load_thumb_for_index(self, index: int) -> None:
        self._loading_thumb = True
        try:
            item = self._items[index]
            path = await download_thumbnail(
                item.thumbnail_url,
                candidates=item.thumbnail_urls,
                page_url=self._probe.url,
            )
            self._thumb_cache[index] = path
            if self._index == index:
                self._set_thumb(path)
        finally:
            self._loading_thumb = False

    async def action_preview_stream(self) -> None:
        if self._previewing:
            return
        if self._current().kind != "video":
            self.notify("This slide is an image — no stream preview", severity="information")
            return
        if not mpv_available():
            self.notify("mpv not installed — can't stream preview", severity="error")
            return
        self._previewing = True
        self.notify("opening mpv preview…")
        try:
            await stream_preview(self._probe.url)
        except Exception as exc:  # noqa: BLE001
            self.notify(str(exc), severity="error")
        finally:
            self._previewing = False


class FormatPickerScreen(ModalScreen[FormatChoice | None]):
    """Pick quality / format before download (YouTube etc.)."""

    BINDINGS = [
        Binding("escape", "cancel", "cancel", show=False, priority=True),
        Binding("p", "preview_stream", "preview", show=False),
    ]

    CSS = """
    FormatPickerScreen {
        align: center middle;
        background: $background 80%;
    }
    #fmt-dialog {
        width: 64;
        max-width: 100%;
        height: auto;
        max-height: 90%;
        border: solid $foreground;
        background: $background;
        padding: 1 2;
        align: center middle;
    }
    #fmt-title {
        text-style: bold;
        color: $foreground;
        text-align: center;
        width: 100%;
        height: auto;
        margin-bottom: 0;
    }
    #fmt-meta {
        color: $text-muted;
        text-align: center;
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    #fmt-thumb-wrap {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0 0 1 0;
    }
    #fmt-thumb {
        width: auto;
        height: 14;
        max-width: 100%;
    }
    #fmt-thumb.thumb-halfcell {
        height: 18;
    }
    #fmt-note {
        color: $text-muted;
        text-align: center;
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    #fmt-list {
        height: auto;
        min-height: 10;
        max-height: 14;
        border: none;
        background: $background;
        padding: 0;
        width: 100%;
    }
    #fmt-list:focus {
        border: none;
    }
    #fmt-hint {
        margin-top: 1;
        color: $text-muted;
        text-align: center;
        width: 100%;
        height: 1;
        text-wrap: nowrap;
    }
    """

    def __init__(
        self,
        probe: ProbeResult,
        *,
        thumb_path: Path | None = None,
        prefer_audio: bool = False,
        prefer_quality: str = "best",
    ) -> None:
        super().__init__()
        self._probe = probe
        self._thumb_path = thumb_path
        self._prefer_audio = prefer_audio
        self._prefer_quality = prefer_quality
        self._previewing = False

    def compose(self) -> ComposeResult:
        title = self._probe.title or "Choose format"
        if len(title) > 56:
            title = title[:53] + "…"
        meta_bits = []
        if self._probe.uploader:
            meta_bits.append(self._probe.uploader)
        if self._probe.duration:
            meta_bits.append(self._probe.duration)
        meta = " · ".join(meta_bits)

        with Vertical(id="fmt-dialog"):
            yield Label(title, id="fmt-title")
            yield Label(meta or " ", id="fmt-meta")
            if self._thumb_path is not None:
                with Center(id="fmt-thumb-wrap"):
                    yield make_thumb(self._thumb_path, id="fmt-thumb")
            else:
                yield Label("no thumbnail available", id="fmt-note")
            yield OptionList(id="fmt-list")
            hint = "↑↓ · ⏎ grab · esc"
            if mpv_available():
                hint += " · p play"
            yield Label(hint, id="fmt-hint")

    def on_mount(self) -> None:
        option_list = self.query_one("#fmt-list", OptionList)
        for index, choice in enumerate(self._probe.choices):
            option_list.add_option(Option(choice.label, id=f"fmt-{index}"))
        option_list.highlighted = self._initial_index()
        option_list.focus()

    def _initial_index(self) -> int:
        choices = self._probe.choices
        if self._prefer_audio:
            for index, choice in enumerate(choices):
                if choice.audio_only:
                    return index
        cap: int | None = None
        if self._prefer_quality == "1080":
            cap = 1080
        elif self._prefer_quality == "720":
            cap = 720
        if cap is not None:
            for index, choice in enumerate(choices):
                if choice.height is not None and choice.height <= cap:
                    return index
        return 0

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(self._probe.choices[event.option_index])

    def action_cancel(self) -> None:
        self.dismiss(None)

    async def action_preview_stream(self) -> None:
        if self._previewing:
            return
        if not mpv_available():
            self.notify("mpv not installed — can't stream preview", severity="error")
            return
        self._previewing = True
        self.notify("opening mpv preview…")
        try:
            await stream_preview(self._probe.url)
        except Exception as exc:  # noqa: BLE001
            self.notify(str(exc), severity="error")
        finally:
            self._previewing = False


class TheOneApp(App[None]):
    """Paste → grab → done."""

    TITLE = "theOne"
    # Don't let Textual steal Escape for widget minimize — we use it to cancel.
    ESCAPE_TO_MINIMIZE = False
    CSS = """
    Screen {
        align: center middle;
        background: $background;
        color: $foreground;
    }
    #shell {
        width: 72;
        max-width: 100%;
        height: auto;
        align: center middle;
        padding: 0;
    }
    #brand {
        width: 100%;
        text-align: center;
        color: $foreground;
        text-style: bold;
        margin-bottom: 1;
    }
    #tagline {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin-top: 0;
    }
    #platforms {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin-top: 0;
        margin-bottom: 3;
    }
    #linkbar {
        width: 100%;
        margin-top: 0;
    }
    #status {
        text-align: center;
        margin-top: 2;
        height: auto;
        min-height: 1;
        width: 72;
        max-width: 100%;
        color: $text-muted;
    }
    #status.-error {
        color: $foreground;
        text-style: bold;
    }
    #status.-ok {
        color: $foreground;
    }
    #status.-busy {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit", show=False, priority=True),
        Binding("ctrl+t", "cycle_theme", "theme", show=False),
        Binding("ctrl+a", "toggle_audio", "audio", show=False),
        Binding("ctrl+q", "cycle_quality", "quality", show=False),
        Binding("ctrl+v", "paste_clipboard", "paste", show=False),
        Binding("escape", "cancel_grab", "cancel", show=False, priority=True),
        Binding("up", "history_prev", "history", show=False),
        Binding("down", "history_next", "history", show=False),
    ]

    def __init__(
        self,
        config: Config | None = None,
        config_path: Path | None = None,
        history_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.config = config or load_config(config_path)
        self.config_path = config_path
        self.history_path = history_path
        self._busy = False
        self._job: DownloadJob | None = None
        self._history = load_history(history_path)
        self._history_index = -1
        self._pending_url: str | None = None
        self._pending_extractor: str | None = None
        self._probing = False
        self._probe_cancelled = False

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="shell"):
                yield Static(BRAND, id="brand")
                yield Label(TAGLINE, id="tagline")
                yield Label(PLATFORMS, id="platforms")
                yield LinkBar(id="linkbar")
                yield Static("", id="status")
        yield KeyHints(id="hints")

    def on_mount(self) -> None:
        self.register_theme(THEONE_DARK)
        self.register_theme(THEONE_LIGHT)
        self._apply_theme(self.config.theme)
        self._refresh_hints()
        self.query_one("#url", Input).focus()
        if self.config.download_dir is None:
            self.call_after_refresh(self._prompt_download_dir)
        else:
            # Never block first paint on clipboard tools.
            self.set_timer(0.05, self._maybe_autofill_clipboard)

    def _refresh_hints(self) -> None:
        self.query_one("#hints", KeyHints).show(
            theme=self.config.theme,
            audio_only=self.config.audio_only,
            quality=self.config.quality,
            busy=self._busy,
        )

    def _apply_theme(self, theme: ThemeName) -> None:
        if theme == "light":
            self.theme = "theone-light"
        elif theme == "dark":
            self.theme = "theone-dark"
        else:
            self.theme = "theone-dark" if terminal_prefers_dark() else "theone-light"

    def _set_status(self, message: str, *, kind: str = "") -> None:
        status = self.query_one("#status", Static)
        status.set_class(kind == "error", "-error")
        status.set_class(kind == "ok", "-ok")
        status.set_class(kind == "busy", "-busy")
        status.update(message)

    def _prompt_download_dir(self) -> None:
        initial = Path.home() / "Videos" / "theOne"
        self.push_screen(DownloadDirScreen(initial), self._on_dir_chosen)

    def _on_dir_chosen(self, path: Path | None) -> None:
        if path is None:
            self._set_status(
                "Set a download folder to grab (restart or fix config).",
                kind="error",
            )
            return
        self.config = self.config.with_updates(download_dir=path)
        save_config(self.config, self.config_path)
        self._set_status(f"Saving to {path}", kind="ok")
        self._maybe_autofill_clipboard()

    def _maybe_autofill_clipboard(self) -> None:
        try:
            url_input = self.query_one("#url", Input)
            if url_input.value.strip():
                return
            clip = read_clipboard()
            if clip and looks_like_url(clip):
                url_input.value = clip.splitlines()[0].strip()
                self._set_status("Clipboard URL ready — Enter to grab.", kind="ok")
        except Exception:
            # Never crash the TUI for clipboard quirks.
            return

    def action_cycle_theme(self) -> None:
        self.config = self.config.with_updates(theme=cycle_theme(self.config.theme))
        self._apply_theme(self.config.theme)
        save_config(self.config, self.config_path)
        self._refresh_hints()

    def action_toggle_audio(self) -> None:
        self.config = self.config.with_updates(audio_only=not self.config.audio_only)
        save_config(self.config, self.config_path)
        self._refresh_hints()

    def action_cycle_quality(self) -> None:
        self.config = self.config.with_updates(quality=cycle_quality(self.config.quality))
        save_config(self.config, self.config_path)
        self._refresh_hints()

    def action_paste_clipboard(self) -> None:
        clip = read_clipboard()
        if not clip:
            self._set_status("Clipboard empty (need wl-paste or xclip).", kind="error")
            return
        line = clip.splitlines()[0].strip()
        self.query_one("#url", Input).value = line
        if looks_like_url(line):
            self._set_status("Pasted — Enter to grab.", kind="ok")
        else:
            self._set_status("Pasted clipboard text.")

    def action_cancel_grab(self) -> None:
        if self._busy and self._job is not None:
            self._job.cancel()
            self._set_status("cancelling…", kind="busy")
            return
        if self._probing:
            self._probe_cancelled = True
            self._probing = False
            self._pending_url = None
            self._pending_extractor = None
            self._set_status("cancelled", kind="error")
            self._refresh_hints()
            return
        # App binds Escape with priority=True, so it runs before modal bindings.
        # Dismiss the active modal ourselves (confirm / format picker / dir prompt).
        screen = self.screen
        if getattr(screen, "is_modal", False):
            cancel = getattr(screen, "action_cancel", None)
            if callable(cancel):
                cancel()
            else:
                screen.dismiss(None)

    def action_history_prev(self) -> None:
        if not self._history or self._busy:
            return
        if self._history_index < 0:
            self._history_index = 0
        else:
            self._history_index = min(self._history_index + 1, len(self._history) - 1)
        self.query_one("#url", Input).value = self._history[self._history_index]

    def action_history_next(self) -> None:
        if not self._history or self._busy:
            return
        if self._history_index <= 0:
            self._history_index = -1
            self.query_one("#url", Input).value = ""
            return
        self._history_index -= 1
        self.query_one("#url", Input).value = self._history[self._history_index]

    @on(Button.Pressed, "#grab-btn")
    def grab_clicked(self) -> None:
        self.action_grab()

    @on(Input.Submitted, "#url")
    def url_submitted(self) -> None:
        self.action_grab()

    def action_grab(self) -> None:
        if self._busy or self._probing:
            return
        url = self.query_one("#url", Input).value.strip()
        if not url:
            self._set_status("Paste a link first.", kind="error")
            return
        if self.config.download_dir is None:
            self._prompt_download_dir()
            return
        self._probing = True
        self._probe_cancelled = False
        self._pending_url = url
        self._pending_extractor = None
        self._refresh_hints()
        self._set_status("fetching formats…", kind="busy")
        self.probe_formats_worker(url)

    @work(exclusive=True, thread=False)
    async def probe_formats_worker(self, url: str) -> None:
        probe: ProbeResult | None = None
        thumb_path: Path | None = None
        try:
            self._set_status("fetching formats…", kind="busy")
            probe = await fetch_probe(
                url,
                cookies_from_browser=self.config.cookies_from_browser,
            )
            if self._probe_cancelled:
                return
            if probe.thumbnail_urls or probe.thumbnail_url:
                self._set_status("loading thumbnail…", kind="busy")
                thumb_path = await download_thumbnail(
                    probe.thumbnail_url,
                    candidates=probe.thumbnail_urls,
                    page_url=url,
                )
            if self._probe_cancelled:
                return
        except YtDlpNotFoundError as exc:
            self._pending_url = None
            self._pending_extractor = None
            self._set_status(str(exc), kind="error")
            return
        except Exception as exc:  # noqa: BLE001 — show probe failures in UI
            self._pending_url = None
            self._pending_extractor = None
            message = str(exc).strip() or "Could not fetch formats."
            if "outdated" in message.lower() or "unable to extract" in message.lower():
                message = (
                    "Could not read formats (yt-dlp may be outdated).\n"
                    "Update: uv tool install --force yt-dlp"
                )
            self._set_status(message, kind="error")
            return
        finally:
            self._probing = False
            self._refresh_hints()

        if self._probe_cancelled or probe is None:
            return

        self._pending_extractor = probe.extractor
        self._set_status("")
        # IG / TikTok / X: confirm + in-TUI thumbnail, not a long format list.
        if prefers_instant_best(url, probe.extractor):
            self.push_screen(
                ConfirmGrabScreen(probe, thumb_path=thumb_path),
                self._on_format_chosen,
            )
            return

        self.push_screen(
            FormatPickerScreen(
                probe,
                thumb_path=thumb_path,
                prefer_audio=self.config.audio_only,
                prefer_quality=self.config.quality,
            ),
            self._on_format_chosen,
        )

    def _on_format_chosen(self, choice: FormatChoice | None) -> None:
        url = self._pending_url
        if choice is None or not url:
            self._pending_url = None
            self._pending_extractor = None
            self._set_status("cancelled", kind="error")
            self.query_one("#url", Input).focus()
            return
        self._start_download(url, choice)

    def _start_download(self, url: str, choice: FormatChoice) -> None:
        if self._busy:
            return
        self._busy = True
        self._job = DownloadJob()
        self._refresh_hints()
        self._set_status(f"{progress_bar(0)}  0%  ·  {choice.label}", kind="busy")
        self.download_worker(url, choice)

    @work(exclusive=True, thread=False)
    async def download_worker(self, url: str, choice: FormatChoice) -> None:
        assert self.config.download_dir is not None
        job = self._job or DownloadJob()
        title: str | None = None
        download_dir = resolve_download_dir(
            self.config.download_dir,
            url,
            self._pending_extractor,
        )
        try:
            if choice.kind == "image":
                image_url = choice.image_url
                if not image_url:
                    self._set_status("No image URL for this slide", kind="error")
                    return
                updates = download_image(
                    image_url,
                    download_dir=download_dir,
                    title=None,
                    playlist_index=choice.playlist_index,
                    page_url=url,
                    cookies_from_browser=self.config.cookies_from_browser,
                    job=job,
                )
            else:
                updates = run_download(
                    url,
                    download_dir=download_dir,
                    audio_only=choice.audio_only,
                    concurrent_fragments=self.config.concurrent_fragments,
                    quality=self.config.quality,
                    use_aria2c=self.config.use_aria2c,
                    format_spec=choice.format_spec or None,
                    cookies_from_browser=self.config.cookies_from_browser,
                    playlist_index=choice.playlist_index,
                    job=job,
                )

            async for update in updates:
                if update.title:
                    title = update.title
                if update.done:
                    if update.cancelled:
                        self._set_status("cancelled", kind="error")
                    elif update.success:
                        dest = update.destination or str(download_dir)
                        label = f"done  ·  {title}" if title else "done"
                        self._set_status(f"{label}\n{dest}", kind="ok")
                        self.query_one("#url", Input).value = ""
                        self._history = push_history(url, self.history_path)
                        self._history_index = -1
                        self._pending_url = None
                        self._pending_extractor = None
                    else:
                        self._set_status(update.error or "download failed", kind="error")
                elif update.percent is not None:
                    bits = [progress_bar(update.percent), f"{update.percent:.0f}%"]
                    if update.speed and update.speed != "UnknownB/s":
                        bits.append(update.speed)
                    if title:
                        bits.append(title)
                    self._set_status("  ".join(bits), kind="busy")
                elif update.destination:
                    self._set_status(update.destination, kind="busy")
                elif title:
                    self._set_status(title, kind="busy")
        except YtDlpNotFoundError as exc:
            self._set_status(str(exc), kind="error")
        except OSError as exc:
            self._set_status(f"Failed to start download: {exc}", kind="error")
        finally:
            self._busy = False
            self._job = None
            self._refresh_hints()
            self.query_one("#url", Input).focus()
