"""
REM - Interface graphique PyQt6 (v2)
Design minimaliste, chat agrandi et copiable, mascotte kawaii animée,
thème clair / sombre, indicateur de réflexion animé, bouton Quit avec
message d'adieu, et synchronisation texte/voix.
"""

import sys
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextBrowser, QSplitter, QFrame,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QMovie, QFont


# ─── Emplacement des assets de la mascotte ─────────────────────────────────
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "mascot"

MASCOT_FILES = {
    "idle":      ASSETS_DIR / "idle.gif",
    "listening": ASSETS_DIR / "listening.gif",
    "speaking":  ASSETS_DIR / "speaking.gif",
}

FALLBACK_FACES = {
    "idle":      "( ◡ ‿ ◡ )",
    "listening": "( o ‿ o )",
    "speaking":  "( ^ ‿ ^ )",
}

GOODBYE_TEXT = "Goodbye, sir."


THEMES = {
    "dark": {
        "bg":        "#0c0f12",
        "bg_alt":    "#14181c",
        "border":    "#242a30",
        "text":      "#e8eaed",
        "text_dim":  "#8a9099",
        "accent":    "#7dd3fc",
        "accent_bg": "rgba(125,211,252,0.10)",
    },
    "light": {
        "bg":        "#fafafa",
        "bg_alt":    "#ffffff",
        "border":    "#e4e4e7",
        "text":      "#1c1c1e",
        "text_dim":  "#7a7a80",
        "accent":    "#0284c7",
        "accent_bg": "rgba(2,132,199,0.08)",
    },
}


def build_stylesheet(t: dict) -> str:
    return f"""
    QWidget {{
        background: {t['bg']};
        color: {t['text']};
        font-family: 'Segoe UI', 'Inter', sans-serif;
    }}
    QFrame#topBar, QFrame#inputBar {{
        background: {t['bg_alt']};
        border: none;
        border-bottom: 1px solid {t['border']};
    }}
    QFrame#inputBar {{
        border-top: 1px solid {t['border']};
        border-bottom: none;
    }}
    QLabel#title {{
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 2px;
        color: {t['text']};
    }}
    QLabel#stateLbl {{
        font-size: 11px;
        letter-spacing: 1px;
        color: {t['text_dim']};
    }}
    QTextBrowser#chat {{
        background: {t['bg']};
        border: none;
        padding: 12px;
        font-size: 13px;
    }}
    QLineEdit#input {{
        background: {t['bg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
        color: {t['text']};
    }}
    QLineEdit#input:focus {{
        border-color: {t['accent']};
    }}
    QPushButton {{
        background: transparent;
        border: 1px solid {t['border']};
        border-radius: 8px;
        color: {t['text']};
        padding: 8px 16px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background: {t['accent_bg']};
        border-color: {t['accent']};
    }}
    QPushButton#quitBtn:hover {{
        background: rgba(239,68,68,0.12);
        border-color: #ef4444;
    }}
    QSplitter::handle {{
        background: {t['border']};
        width: 1px;
    }}
    """


class MascotWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(340, 340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._movies = {}
        self._current_state = "idle"
        self._load_movies()
        self.set_state("idle")

    def _load_movies(self):
        for state, path in MASCOT_FILES.items():
            if path.exists():
                movie = QMovie(str(path))
                movie.setScaledSize(QSize(320, 320))
                self._movies[state] = movie

    def set_state(self, state: str):
        self._current_state = state
        if state in self._movies:
            self.setMovie(self._movies[state])
            self._movies[state].start()
        else:
            self.setMovie(None)
            self.setText(FALLBACK_FACES.get(state, "( . . )"))
            self.setStyleSheet("font-size: 28px;")

    def apply_theme(self, theme_name: str):
        pass


class JarvisWindow(QMainWindow):
    sig_user_message = pyqtSignal(str)
    sig_close_now = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("REM")
        self.resize(1100, 700)

        self._theme_name = "dark"
        self._current_state = "idle"
        self.voice_enabled = True

        self._messages = []
        self._thinking = False
        self._thinking_dots = 1

        self._quitting = False
        self._ready_to_close = False
        self.sig_close_now.connect(self._do_close_now)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_top_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._make_mascot_panel())
        splitter.addWidget(self._make_chat_panel())
        splitter.setSizes([350, 750])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        root.addWidget(self._make_input_bar())

        self._thinking_timer = QTimer(self)
        self._thinking_timer.timeout.connect(self._tick_thinking)

        self._apply_theme()
        self._start_clock()

    def _make_top_bar(self):
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(52)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)

        title = QLabel("REM")
        title.setObjectName("title")

        self._clock = QLabel()

        self._theme_btn = QPushButton("☀ / ☾")
        self._theme_btn.setFixedWidth(70)
        self._theme_btn.clicked.connect(self._toggle_theme)

        self._voice_btn = QPushButton("🔊 Voice: ON")
        self._voice_btn.setFixedWidth(120)
        self._voice_btn.clicked.connect(self._toggle_voice)

        self._quit_btn = QPushButton("⏻ Quit")
        self._quit_btn.setObjectName("quitBtn")
        self._quit_btn.setFixedWidth(90)
        self._quit_btn.clicked.connect(self.close)

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._clock)
        lay.addSpacing(16)
        lay.addWidget(self._voice_btn)
        lay.addSpacing(8)
        lay.addWidget(self._theme_btn)
        lay.addSpacing(8)
        lay.addWidget(self._quit_btn)
        return bar

    def _make_mascot_panel(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(14)

        self.mascot = MascotWidget()
        lay.addStretch()
        lay.addWidget(self.mascot)

        self._state_lbl = QLabel("STANDBY")
        self._state_lbl.setObjectName("stateLbl")
        self._state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._state_lbl)
        lay.addStretch()
        return panel

    def _make_chat_panel(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(0)

        self._chat = QTextBrowser()
        self._chat.setObjectName("chat")
        self._chat.setOpenExternalLinks(False)
        lay.addWidget(self._chat)
        return panel

    def _make_input_bar(self):
        bar = QFrame()
        bar.setObjectName("inputBar")
        bar.setFixedHeight(64)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(10)

        self._input = QLineEdit()
        self._input.setObjectName("input")
        self._input.setPlaceholderText("Send a message to Rem...")
        self._input.returnPressed.connect(self._on_send)

        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(90)
        send_btn.clicked.connect(self._on_send)

        lay.addWidget(self._input)
        lay.addWidget(send_btn)
        return bar

    def _apply_theme(self):
        t = THEMES[self._theme_name]
        self.setStyleSheet(build_stylesheet(t))
        self.mascot.apply_theme(self._theme_name)
        self._render_chat_stylesheet()
        self._render_chat()

    def _toggle_theme(self):
        self._theme_name = "light" if self._theme_name == "dark" else "dark"
        self._apply_theme()

    def _toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        self._voice_btn.setText("🔊 Voice: ON" if self.voice_enabled else "🔇 Voice: OFF")

    def _render_chat_stylesheet(self):
        t = THEMES[self._theme_name]
        self._chat.document().setDefaultStyleSheet(f"""
            .rem {{ color: {t['accent']}; font-weight: 600; }}
            .you {{ color: {t['text_dim']}; font-weight: 600; }}
            .msg {{ color: {t['text']}; }}
            .thinking {{ color: {t['text_dim']}; font-style: italic; }}
        """)

    def _start_clock(self):
        t = QTimer(self)
        t.timeout.connect(lambda: self._clock.setText(datetime.now().strftime("%H:%M:%S")))
        t.start(1000)
        self._clock.setText(datetime.now().strftime("%H:%M:%S"))

    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_message("You", text)
        self.start_thinking()
        self.set_state("listening")
        self.sig_user_message.emit(text)

    def add_message(self, sender: str, text: str):
        self._thinking = False
        self._thinking_timer.stop()
        self._messages.append((sender, text))
        self._render_chat()

    def start_thinking(self):
        self._thinking = True
        self._thinking_dots = 1
        self._thinking_timer.start(450)
        self._render_chat()

    def stop_thinking(self):
        self._thinking = False
        self._thinking_timer.stop()
        self._render_chat()

    def _tick_thinking(self):
        self._thinking_dots = (self._thinking_dots % 3) + 1
        self._render_chat()

    def _escape(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
        )

    def _render_chat(self):
        blocks = []
        for sender, text in self._messages:
            css_class = "rem" if sender.upper() == "REM" else "you"
            blocks.append(
                f'<p><span class="{css_class}">{sender.upper()}</span><br>'
                f'<span class="msg">{self._escape(text)}</span></p>'
            )

        if self._thinking:
            dots = "." * self._thinking_dots
            blocks.append(
                '<p><span class="rem">REM</span><br>'
                f'<span class="thinking">réfléchit{dots}</span></p>'
            )

        self._chat.setHtml("".join(blocks))
        self._chat.verticalScrollBar().setValue(
            self._chat.verticalScrollBar().maximum()
        )

    def set_state(self, state: str):
        self._current_state = state
        self.mascot.set_state(state)
        labels = {
            "idle":      "STANDBY",
            "listening": "PROCESSING...",
            "speaking":  "SPEAKING",
        }
        self._state_lbl.setText(labels.get(state, "STANDBY"))

    def closeEvent(self, event):
        if self._ready_to_close:
            event.accept()
            return
        event.ignore()
        if not self._quitting:
            self._start_quit_sequence()

    def _start_quit_sequence(self):
        self._quitting = True
        self._input.setEnabled(False)
        self._quit_btn.setEnabled(False)
        self.stop_thinking()
        self.set_state("speaking" if self.voice_enabled else "idle")

        if self.voice_enabled:
            synth_worker = VoiceSynthWorker(GOODBYE_TEXT)
            self._active_workers = getattr(self, "_active_workers", [])
            self._active_workers.append(synth_worker)

            def on_synth_done(ok: bool):
                if synth_worker in self._active_workers:
                    self._active_workers.remove(synth_worker)
                self.add_message("Rem", GOODBYE_TEXT)

                import threading
                from core.voice import play
                def do_play():
                    if ok:
                        play()
                    self.sig_close_now.emit()
                threading.Thread(target=do_play, daemon=True).start()

            synth_worker.done.connect(on_synth_done)
            synth_worker.start()
        else:
                self.add_message("Rem", GOODBYE_TEXT)

    def _do_close_now(self):
        self._ready_to_close = True
        self.close()


class BrainWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def run(self):
        from core.brain import demander
        reponse = demander(self.message)
        self.response_ready.emit(reponse)


class VoiceSynthWorker(QThread):
    """Génère l'audio (Piper) sans le jouer, pour synchroniser texte et voix."""
    done = pyqtSignal(bool)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        from core.voice import synthesize
        ok = synthesize(self.text)
        self.done.emit(ok)


def launch():
    app = QApplication(sys.argv)
    win = JarvisWindow()

    win._active_workers = []

    def on_user_message(text: str):
        worker = BrainWorker(text)
        win._active_workers.append(worker)

        def cleanup():
            if worker in win._active_workers:
                win._active_workers.remove(worker)

        def on_response(reponse: str):
            win.stop_thinking()

            if win.voice_enabled:
                synth_worker = VoiceSynthWorker(reponse)
                win._active_workers.append(synth_worker)

                def on_synth_done(ok: bool):
                    if synth_worker in win._active_workers:
                        win._active_workers.remove(synth_worker)
                    win.add_message("Rem", reponse)
                    win.set_state("speaking")

                    import threading
                    from core.voice import play
                    def do_play():
                        if ok:
                            play()
                        win.set_state("idle")
                    threading.Thread(target=do_play, daemon=True).start()

                synth_worker.done.connect(on_synth_done)
                synth_worker.start()
            else:
                win.add_message("Rem", reponse)
                win.set_state("idle")

        worker.response_ready.connect(on_response)
        worker.finished.connect(cleanup)
        worker.start()

    win.sig_user_message.connect(on_user_message)

    welcome = "Welcome sir. Systems online. How can I assist you today?"

    if win.voice_enabled:
        welcome_worker = VoiceSynthWorker(welcome)
        win._active_workers.append(welcome_worker)

        def on_welcome_synth(ok: bool):
            if welcome_worker in win._active_workers:
                win._active_workers.remove(welcome_worker)
            win.add_message("Rem", welcome)

            import threading
            from core.voice import play
            def do_play():
                if ok:
                    play()
                win.set_state("idle")
            win.set_state("speaking")
            threading.Thread(target=do_play, daemon=True).start()

        welcome_worker.done.connect(on_welcome_synth)
        welcome_worker.start()
    else:
            win.add_message("Rem", welcome)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()