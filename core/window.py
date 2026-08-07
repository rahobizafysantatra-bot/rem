"""
JARVIS - Interface graphique PyQt6 (v2)
Design minimaliste, chat agrandi et copiable, mascotte kawaii animée,
thème clair / sombre avec bouton de switch.
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
# Dépose ici tes GIFs téléchargés (voir README) :
#   assets/mascot/idle.gif
#   assets/mascot/listening.gif
#   assets/mascot/speaking.gif
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "mascot"

MASCOT_FILES = {
    "idle":      ASSETS_DIR / "idle.gif",
    "listening": ASSETS_DIR / "listening.gif",
    "speaking":  ASSETS_DIR / "speaking.gif",
}

# Emoji de secours si un GIF n'est pas encore présent
FALLBACK_FACES = {
    "idle":      "( ◡ ‿ ◡ )",
    "listening": "( o ‿ o )",
    "speaking":  "( ^ ‿ ^ )",
}


# ─── Thèmes ─────────────────────────────────────────────────────────────────
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
    QSplitter::handle {{
        background: {t['border']};
        width: 1px;
    }}
    """


# ─── Mascotte ────────────────────────────────────────────────────────────────
class MascotWidget(QLabel):
    """
    Affiche un GIF animé selon l'état ('idle' | 'listening' | 'speaking').
    Si le fichier GIF n'existe pas encore, affiche un visage texte de secours
    pour que l'interface reste utilisable pendant que tu récupères tes assets.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._movies = {}
        self._current_state = "idle"
        self._load_movies()
        self.set_state("idle")

    def _load_movies(self):
        for state, path in MASCOT_FILES.items():
            if path.exists():
                movie = QMovie(str(path))
                movie.setScaledSize(QSize(200, 200))
                self._movies[state] = movie

    def set_state(self, state: str):
        self._current_state = state
        if state in self._movies:
            self.setMovie(self._movies[state])
            self._movies[state].start()
        else:
            # Fallback texte tant que le GIF n'est pas fourni
            self.setMovie(None)
            self.setText(FALLBACK_FACES.get(state, "( . . )"))
            self.setStyleSheet("font-size: 28px;")

    def apply_theme(self, theme_name: str):
        # Les GIF restent identiques ; place utilisée si tu veux gérer
        # des variantes claires/sombres plus tard (ex: idle_light.gif).
        pass


# ─── Fenêtre principale ───────────────────────────────────────────────────────
class JarvisWindow(QMainWindow):
    sig_user_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("REM")
        self.resize(1100, 700)

        self._theme_name = "dark"
        self._current_state = "idle"

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

        self._apply_theme()
        self._start_clock()

    # ── Sections ─────────────────────────────────────────────────────────────
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

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._clock)
        lay.addSpacing(16)
        lay.addWidget(self._theme_btn)
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
        # Sélectionnable + copiable par défaut (comportement natif de QTextBrowser)
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
        self._input.setPlaceholderText("Send a message to Jarvis...")
        self._input.returnPressed.connect(self._on_send)

        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(90)
        send_btn.clicked.connect(self._on_send)

        lay.addWidget(self._input)
        lay.addWidget(send_btn)
        return bar

    # ── Thème ────────────────────────────────────────────────────────────────
    def _apply_theme(self):
        t = THEMES[self._theme_name]
        self.setStyleSheet(build_stylesheet(t))
        self.mascot.apply_theme(self._theme_name)
        self._render_chat_theme()

    def _toggle_theme(self):
        self._theme_name = "light" if self._theme_name == "dark" else "dark"
        self._apply_theme()

    def _render_chat_theme(self):
        # Redessine l'historique existant avec les couleurs du thème actuel
        t = THEMES[self._theme_name]
        self._chat.document().setDefaultStyleSheet(f"""
            .jarvis {{ color: {t['accent']}; font-weight: 600; }}
            .you {{ color: {t['text_dim']}; font-weight: 600; }}
            .msg {{ color: {t['text']}; }}
        """)

    # ── Horloge ──────────────────────────────────────────────────────────────
    def _start_clock(self):
        t = QTimer(self)
        t.timeout.connect(lambda: self._clock.setText(datetime.now().strftime("%H:%M:%S")))
        t.start(1000)
        self._clock.setText(datetime.now().strftime("%H:%M:%S"))

    # ── Actions ───────────────────────────────────────────────────────────────
    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_message("You", text)
        self.set_state("listening")
        self.sig_user_message.emit(text)

    # ── API publique (compatible avec main.py / brain.py / voice.py) ──────────
    def add_message(self, sender: str, text: str):
        """Ajoute un message dans le chat (sélectionnable et copiable)."""
        css_class = "jarvis" if sender.upper() == "JARVIS" else "you"
        safe_text = (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
        )
        html = f'<p><span class="{css_class}">{sender.upper()}</span><br>' \
               f'<span class="msg">{safe_text}</span></p>'
        self._chat.append(html)
        self._chat.verticalScrollBar().setValue(
            self._chat.verticalScrollBar().maximum()
        )

    def set_state(self, state: str):
        """state = 'idle' | 'listening' | 'speaking'"""
        self._current_state = state
        self.mascot.set_state(state)
        labels = {
            "idle":      "STANDBY",
            "listening": "PROCESSING...",
            "speaking":  "SPEAKING",
        }
        self._state_lbl.setText(labels.get(state, "STANDBY"))


# ─── Worker thread pour brain.py ──────────────────────────────────────────────
class BrainWorker(QThread):
    """Exécute demander() dans un thread séparé pour ne pas bloquer l'UI."""
    response_ready = pyqtSignal(str)

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def run(self):
        from core.brain import demander
        reponse = demander(self.message)
        self.response_ready.emit(reponse)


# ─── Lancement ────────────────────────────────────────────────────────────────
def launch():
    app = QApplication(sys.argv)
    win = JarvisWindow()

    def on_user_message(text: str):
        worker = BrainWorker(text)

        def on_response(reponse: str):
            win.add_message("Jarvis", reponse)
            win.set_state("speaking")

            from core.voice import parler
            import threading
            def speak_then_idle():
                parler(reponse)
                win.set_state("idle")
            threading.Thread(target=speak_then_idle, daemon=True).start()

        worker.response_ready.connect(on_response)
        worker.start()

    win.sig_user_message.connect(on_user_message)

    welcome = "Welcome sir. Systems online. How can I assist you today?"
    win.add_message("Jarvis", welcome)

    import threading
    from core.voice import parler
    threading.Thread(target=parler, args=(welcome,), daemon=True).start()

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()