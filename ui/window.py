"""
JARVIS / REM - Interface graphique PyQt6 (v3)
Sidebar avec historique de conversations + nouvelle conversation,
blocs de code avec bouton copier, indicateur de reflexion anime,
theme clair/sombre, mascotte kawaii, synchro texte/voix, bouton Quit.
"""

import re
import sys
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSplitter, QFrame, QSizePolicy,
    QScrollArea, QListWidget, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QUrl
from PyQt6.QtGui import (
    QMovie, QFont, QSyntaxHighlighter, QTextCharFormat, QColor,
    QPixmap, QDesktopServices
)


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
ASSISTANT_NAME = "Rem"


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
    QWidget#sidebar {{
        background: {t['bg_alt']};
        border-right: 1px solid {t['border']};
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
    QScrollArea#chatScroll {{
        background: {t['bg']};
        border: none;
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
    QPushButton#newChatBtn {{
        text-align: left;
        font-weight: 600;
    }}
    QWidget#webPanel {{
        background: {t['bg_alt']};
        border-left: 1px solid {t['border']};
    }}
    QSplitter::handle {{
        background: {t['border']};
        width: 1px;
    }}
    QListWidget {{
        background: transparent;
        border: none;
        font-size: 12px;
        color: {t['text']};
        outline: none;
    }}
    QListWidget::item {{
        padding: 9px 10px;
        border-radius: 6px;
        margin-bottom: 2px;
    }}
    QListWidget::item:hover {{
        background: {t['accent_bg']};
    }}
    QListWidget::item:selected {{
        background: {t['accent_bg']};
        color: {t['accent']};
    }}
    """


# ─── Parsing des blocs de code dans une réponse ──────────────────────────────
CODE_RE = re.compile(r"```(\w*)\n?(.*?)```", re.DOTALL)


def parse_segments(text: str):
    """Découpe un texte en segments ('text', contenu) / ('code', code, lang)."""
    segments = []
    pos = 0
    for m in CODE_RE.finditer(text):
        if m.start() > pos:
            segments.append(("text", text[pos:m.start()]))
        segments.append(("code", m.group(2), m.group(1) or ""))
        pos = m.end()
    if pos < len(text):
        segments.append(("text", text[pos:]))
    if not segments:
        segments.append(("text", text))
    return segments


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


class ClickableLabel(QLabel):
    """QLabel qui ouvre une URL dans le navigateur par défaut au clic."""

    def __init__(self, text: str, url: str = "", *args, **kwargs):
        super().__init__(text, *args, **kwargs)
        self._url = url
        if url:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self._url:
            QDesktopServices.openUrl(QUrl(self._url))
        super().mousePressEvent(event)


# ─── Coloration syntaxique façon VS Code Dark+ ───────────────────────────────
LANGUAGE_KEYWORDS = {
    "python": [
        "def", "class", "return", "if", "elif", "else", "for", "while", "in",
        "import", "from", "as", "with", "try", "except", "finally", "raise",
        "pass", "break", "continue", "lambda", "yield", "global", "nonlocal",
        "not", "and", "or", "is", "None", "True", "False", "self", "async",
        "await", "assert", "del", "print",
    ],
    "javascript": [
        "function", "return", "if", "else", "for", "while", "do", "switch",
        "case", "break", "continue", "var", "let", "const", "new", "this",
        "class", "extends", "import", "export", "default", "from", "async",
        "await", "try", "catch", "finally", "throw", "typeof", "instanceof",
        "null", "undefined", "true", "false", "of", "in",
    ],
    "bash": [
        "if", "then", "else", "elif", "fi", "for", "while", "do", "done",
        "case", "esac", "function", "return", "echo", "export", "local",
        "in", "break", "continue",
    ],
    "java": [
        "public", "private", "protected", "class", "static", "void", "new",
        "return", "if", "else", "for", "while", "do", "switch", "case",
        "break", "continue", "import", "package", "extends", "implements",
        "try", "catch", "finally", "throw", "throws", "this", "super",
        "null", "true", "false", "int", "String", "boolean", "double",
        "float", "long", "final", "interface", "enum",
    ],
    "c": [
        "int", "char", "float", "double", "void", "return", "if", "else",
        "for", "while", "do", "switch", "case", "break", "continue",
        "struct", "typedef", "const", "static", "sizeof", "include",
        "define", "NULL",
    ],
    "sql": [
        "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE",
        "SET", "DELETE", "CREATE", "TABLE", "ALTER", "DROP", "JOIN", "ON",
        "AND", "OR", "NOT", "NULL", "PRIMARY", "KEY", "FOREIGN",
        "REFERENCES", "ORDER", "BY", "GROUP", "HAVING", "AS", "DISTINCT",
    ],
}
LANGUAGE_KEYWORDS["py"] = LANGUAGE_KEYWORDS["python"]
LANGUAGE_KEYWORDS["js"] = LANGUAGE_KEYWORDS["javascript"]
LANGUAGE_KEYWORDS["ts"] = LANGUAGE_KEYWORDS["typescript"] = LANGUAGE_KEYWORDS["javascript"]
LANGUAGE_KEYWORDS["sh"] = LANGUAGE_KEYWORDS["bash"]
LANGUAGE_KEYWORDS["cpp"] = LANGUAGE_KEYWORDS["c++"] = LANGUAGE_KEYWORDS["c"]

HASH_COMMENT_LANGS = {"python", "py", "bash", "sh", "yaml", "yml", "ruby", "rb"}


class CodeHighlighter(QSyntaxHighlighter):
    """
    Coloration syntaxique légère (mots-clés, chaînes, nombres, fonctions,
    commentaires) inspirée du thème VS Code Dark+. Volontairement simple
    (regex par ligne, pas de vrai tokenizer) mais suffisante pour rendre
    le code lisible dans le chat.
    """

    def __init__(self, document, language: str = ""):
        super().__init__(document)
        self.language = (language or "").lower()
        self._rules = []
        self._build_rules()

    def _fmt(self, color, bold=False, italic=False):
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:
            f.setFontWeight(QFont.Weight.Bold)
        if italic:
            f.setFontItalic(True)
        return f

    def _build_rules(self):
        keywords = LANGUAGE_KEYWORDS.get(self.language, [])
        if keywords:
            pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
            self._rules.append((re.compile(pattern), self._fmt("#569cd6", bold=True)))

        # nombres
        self._rules.append((re.compile(r'\b\d+\.?\d*\b'), self._fmt("#b5cea8")))

        # appels de fonction : mot suivi de "("
        self._rules.append((re.compile(r'\b[A-Za-z_]\w*(?=\()'), self._fmt("#dcdcaa")))

        # décorateurs / annotations (@quelquechose)
        self._rules.append((re.compile(r'@\w+'), self._fmt("#c586c0")))

        # chaînes de caractères (appliquées après pour écraser le reste)
        self._rules.append((re.compile(r'(\".*?\"|\'.*?\'|`.*?`)'), self._fmt("#ce9178")))

        # commentaires (appliqués en dernier, priment sur tout le reste)
        if self.language in HASH_COMMENT_LANGS:
            comment_re = re.compile(r'#.*')
        else:
            comment_re = re.compile(r'//.*')
        self._rules.append((comment_re, self._fmt("#6a9955", italic=True)))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                start, end = m.span()
                self.setFormat(start, end - start, fmt)


# ─── Bloc de code avec bouton copier ──────────────────────────────────────────
class CodeBlockWidget(QFrame):
    """Bloc de code façon IA moderne : fond sombre + bouton copier."""

    def __init__(self, code: str, language: str = ""):
        super().__init__()
        self.code = code.strip("\n")

        self.setStyleSheet("""
            QFrame#codeBlock { background: #1e1e1e; border: 1px solid #333333; border-radius: 8px; }
        """)
        self.setObjectName("codeBlock")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = QWidget()
        header.setStyleSheet(
            "background: #2a2a2a; border-top-left-radius: 8px; "
            "border-top-right-radius: 8px;"
        )
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(12, 6, 8, 6)

        lang_lbl = QLabel(language or "code")
        lang_lbl.setStyleSheet("color: #9aa0a6; font-size: 11px; background: transparent; border: none;")

        self.copy_btn = QPushButton("⧉ Copy")
        self.copy_btn.setStyleSheet("""
            QPushButton { color: #cfd3d8; background: transparent; border: none;
                          font-size: 11px; padding: 2px 6px; }
            QPushButton:hover { color: #ffffff; }
        """)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy)

        hlay.addWidget(lang_lbl)
        hlay.addStretch()
        hlay.addWidget(self.copy_btn)

        body = QPlainTextEdit()
        body.setReadOnly(True)
        body.setPlainText(self.code)
        body.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        body.setStyleSheet("""
            QPlainTextEdit { background: #1e1e1e; color: #d4d4d4; border: none;
                              padding: 10px 12px; }
        """)
        mono_font = QFont("Consolas")
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        mono_font.setPointSize(10)
        body.setFont(mono_font)

        self._highlighter = CodeHighlighter(body.document(), language)

        line_count = max(1, self.code.count("\n") + 1)
        line_height = body.fontMetrics().lineSpacing()
        body.setFixedHeight(min(line_height * line_count + 24, 420))

        lay.addWidget(header)
        lay.addWidget(body)

    def _copy(self):
        QApplication.clipboard().setText(self.code)
        self.copy_btn.setText("✓ Copied")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("⧉ Copy"))


# ─── Bulle de message (texte + éventuels blocs de code) ──────────────────────
class MessageBubble(QWidget):
    def __init__(self, sender: str, text: str, theme: dict):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 10)
        lay.setSpacing(6)

        is_assistant = sender.upper() == ASSISTANT_NAME.upper()
        sender_color = theme["accent"] if is_assistant else theme["text_dim"]

        sender_lbl = QLabel(sender.upper())
        sender_lbl.setStyleSheet(
            f"color: {sender_color}; font-weight: 600; font-size: 11px; "
            "letter-spacing: 1px; background: transparent;"
        )
        lay.addWidget(sender_lbl)

        for seg in parse_segments(text):
            if seg[0] == "text":
                content = seg[1].strip("\n")
                if not content.strip():
                    continue
                lbl = QLabel(escape_html(content).replace("\n", "<br>"))
                lbl.setWordWrap(True)
                lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                lbl.setStyleSheet(
                    f"color: {theme['text']}; font-size: 13px; background: transparent;"
                )
                lay.addWidget(lbl)
            else:
                _, code, lang = seg
                lay.addWidget(CodeBlockWidget(code, lang))


# ─── Indicateur "réfléchit..." animé (façon Claude) ───────────────────────────
class ThinkingWidget(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 10)
        lay.setSpacing(6)

        sender_lbl = QLabel(ASSISTANT_NAME.upper())
        sender_lbl.setStyleSheet(
            f"color: {theme['text_dim']}; font-weight: 600; font-size: 11px; "
            "letter-spacing: 1px; background: transparent;"
        )
        self._label = QLabel("réfléchit.")
        self._label.setStyleSheet(
            f"color: {theme['text_dim']}; font-style: italic; font-size: 13px; background: transparent;"
        )
        lay.addWidget(sender_lbl)
        lay.addWidget(self._label)

        self._dots = 1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(450)

    def _tick(self):
        self._dots = (self._dots % 3) + 1
        self._label.setText("réfléchit" + "." * self._dots)

    def deleteLater(self):
        self._timer.stop()
        super().deleteLater()


# ─── Mascotte ────────────────────────────────────────────────────────────────
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


# ─── Modèle de conversation ────────────────────────────────────────────────
class Conversation:
    _counter = 0

    def __init__(self):
        Conversation._counter += 1
        self.id = Conversation._counter
        self.title = "New conversation"
        self.messages = []        # [(sender, text), ...]
        self.brain_history = []   # historique format Ollama pour cette conv


# ─── Fenêtre principale ───────────────────────────────────────────────────────
class JarvisWindow(QMainWindow):
    sig_user_message = pyqtSignal(object, str, str)   # (Conversation, texte, contexte_recherche)
    sig_close_now = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(ASSISTANT_NAME.upper())
        self.resize(1300, 720)

        self._theme_name = "dark"
        self._current_state = "idle"
        self.voice_enabled = True
        self.web_search_enabled = False
        self._active_workers = []

        self._conversations = []
        self._current_conv = None
        self._thinking_widget = None

        self._quitting = False
        self._ready_to_close = False
        self.sig_close_now.connect(self._do_close_now)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._make_sidebar())

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        right_lay.addWidget(self._make_top_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._make_mascot_panel())
        splitter.addWidget(self._make_chat_panel())
        splitter.addWidget(self._make_web_panel())
        splitter.setSizes([320, 780, 320])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        right_lay.addWidget(splitter, 1)

        right_lay.addWidget(self._make_input_bar())

        outer.addWidget(right, 1)

        self._apply_theme()
        self._start_clock()

        self.web_panel.setVisible(False)
        self.new_conversation()

    # ── Sidebar / conversations ─────────────────────────────────────────────
    def _make_sidebar(self):
        panel = QWidget()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(230)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 16, 14, 16)
        lay.setSpacing(10)

        new_btn = QPushButton("＋ New chat")
        new_btn.setObjectName("newChatBtn")
        new_btn.clicked.connect(self.new_conversation)
        lay.addWidget(new_btn)

        self._conv_list = QListWidget()
        self._conv_list.itemClicked.connect(self._on_conv_item_clicked)
        lay.addWidget(self._conv_list, 1)

        return panel

    def new_conversation(self):
        conv = Conversation()
        self._conversations.insert(0, conv)
        self.switch_conversation(conv)
        self._refresh_sidebar()

    def _on_conv_item_clicked(self, item):
        idx = self._conv_list.row(item)
        if 0 <= idx < len(self._conversations):
            self.switch_conversation(self._conversations[idx])
            self._refresh_sidebar()

    def switch_conversation(self, conv: "Conversation"):
        self._current_conv = conv
        self._thinking_widget = None
        self._clear_chat_view()
        theme = THEMES[self._theme_name]
        for sender, text in conv.messages:
            self._chat_add_widget(MessageBubble(sender, text, theme))

    def _refresh_sidebar(self):
        self._conv_list.blockSignals(True)
        self._conv_list.clear()
        for conv in self._conversations:
            self._conv_list.addItem(conv.title)
        if self._current_conv in self._conversations:
            self._conv_list.setCurrentRow(self._conversations.index(self._current_conv))
        self._conv_list.blockSignals(False)

    # ── Sections ─────────────────────────────────────────────────────────────
    def _make_top_bar(self):
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(52)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)

        title = QLabel(ASSISTANT_NAME.upper())
        title.setObjectName("title")

        self._clock = QLabel()

        self._theme_btn = QPushButton("☀ / ☾")
        self._theme_btn.setFixedWidth(70)
        self._theme_btn.clicked.connect(self._toggle_theme)

        self._voice_btn = QPushButton("🔊 Voice: ON")
        self._voice_btn.setFixedWidth(120)
        self._voice_btn.clicked.connect(self._toggle_voice)

        self._web_btn = QPushButton("🌐 Web: OFF")
        self._web_btn.setFixedWidth(110)
        self._web_btn.clicked.connect(self._toggle_web_search)

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
        lay.addWidget(self._web_btn)
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
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._chat_scroll = QScrollArea()
        self._chat_scroll.setObjectName("chatScroll")
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(16, 12, 16, 12)
        self._chat_layout.setSpacing(2)
        self._chat_layout.addStretch(1)

        self._chat_scroll.setWidget(self._chat_container)
        lay.addWidget(self._chat_scroll)
        return panel

    def _make_web_panel(self):
        self.web_panel = QWidget()
        self.web_panel.setObjectName("webPanel")
        self.web_panel.setMinimumWidth(260)
        outer = QVBoxLayout(self.web_panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QLabel("🌐 WEB RESULTS")
        header.setObjectName("webHeader")
        header.setStyleSheet(
            "font-weight: 600; font-size: 11px; letter-spacing: 1px; "
            "padding: 16px 16px 8px 16px; background: transparent;"
        )
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self._web_layout = QVBoxLayout(container)
        self._web_layout.setContentsMargins(16, 4, 16, 16)
        self._web_layout.setSpacing(16)

        self._web_status_lbl = QLabel("")
        self._web_status_lbl.setWordWrap(True)
        self._web_status_lbl.setStyleSheet("font-size: 12px; font-style: italic; background: transparent;")
        self._web_layout.addWidget(self._web_status_lbl)
        self._web_layout.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll)
        return self.web_panel

    def _toggle_web_search(self):
        self.web_search_enabled = not self.web_search_enabled
        self._web_btn.setText("🌐 Web: ON" if self.web_search_enabled else "🌐 Web: OFF")
        self.web_panel.setVisible(self.web_search_enabled)

    def set_web_status(self, text: str):
        self._web_status_lbl.setText(text)

    def _web_add_widget(self, widget):
        idx = self._web_layout.count() - 1  # avant le stretch final
        self._web_layout.insertWidget(idx, widget)

    def _clear_web_results(self):
        # garde le label de statut (index 0) et le stretch final
        while self._web_layout.count() > 2:
            item = self._web_layout.takeAt(1)
            w = item.widget()
            if w:
                w.deleteLater()

    def _make_section_label(self, text: str):
        lbl = QLabel(text)
        t = THEMES[self._theme_name]
        lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 700; letter-spacing: 1px; "
            f"color: {t['text_dim']}; background: transparent;"
        )
        return lbl

    def _make_link_card(self, title: str, url: str, prefix: str = ""):
        t = THEMES[self._theme_name]
        card = QWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        title_lbl = ClickableLabel(f"{prefix}{title or url}", url)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {t['accent']}; "
            "background: transparent; text-decoration: underline;"
        )
        lay.addWidget(title_lbl)

        url_lbl = QLabel(url)
        url_lbl.setWordWrap(True)
        url_lbl.setStyleSheet(f"font-size: 10px; color: {t['text_dim']}; background: transparent;")
        lay.addWidget(url_lbl)
        return card

    def _make_image_card(self, title: str, thumb_url: str, page_url: str):
        t = THEMES[self._theme_name]
        card = QWidget()
        lay = QHBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(56, 56)
        thumb_lbl.setScaledContents(True)
        thumb_lbl.setStyleSheet("background: rgba(128,128,128,0.15); border-radius: 6px;")
        lay.addWidget(thumb_lbl)

        text_lbl = ClickableLabel(title or "Image", page_url)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(f"font-size: 12px; color: {t['text']}; background: transparent;")
        lay.addWidget(text_lbl, 1)

        if thumb_url:
            worker = ImageThumbWorker(thumb_url)
            self._active_workers.append(worker)

            def on_thumb(data: bytes):
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
                if data:
                    pix = QPixmap()
                    if pix.loadFromData(data):
                        thumb_lbl.setPixmap(pix)

            worker.done.connect(on_thumb)
            worker.start()

        return card

    def populate_web_results(self, result: dict):
        self._clear_web_results()
        self.set_web_status("")

        texts = result.get("text") or []
        images = result.get("images") or []
        videos = result.get("videos") or []

        if not texts and not images and not videos:
            self.set_web_status("No results found.")
            return

        if texts:
            self._web_add_widget(self._make_section_label("LINKS"))
            for r in texts[:5]:
                self._web_add_widget(self._make_link_card(r.get("title", ""), r.get("href", "")))

        if images:
            self._web_add_widget(self._make_section_label("IMAGES"))
            for r in images[:5]:
                self._web_add_widget(self._make_image_card(
                    r.get("title", ""), r.get("thumbnail", ""), r.get("image", r.get("url", ""))
                ))

        if videos:
            self._web_add_widget(self._make_section_label("VIDEOS"))
            for r in videos[:4]:
                self._web_add_widget(self._make_link_card(
                    r.get("title", ""), r.get("content", r.get("url", "")), prefix="▶ "
                ))

    def _build_search_context(self, result: dict) -> str:
        lines = []
        for r in (result.get("text") or [])[:3]:
            title = r.get("title", "")
            body = r.get("body", "")
            if title or body:
                lines.append(f"- {title}: {body}")
        return "\n".join(lines)

    def _make_input_bar(self):
        bar = QFrame()
        bar.setObjectName("inputBar")
        bar.setFixedHeight(64)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(10)

        self._input = QLineEdit()
        self._input.setObjectName("input")
        self._input.setPlaceholderText(f"Send a message to {ASSISTANT_NAME}...")
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
        if self._current_conv is not None:
            self.switch_conversation(self._current_conv)

    def _toggle_theme(self):
        self._theme_name = "light" if self._theme_name == "dark" else "dark"
        self._apply_theme()

    def _toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        self._voice_btn.setText("🔊 Voice: ON" if self.voice_enabled else "🔇 Voice: OFF")

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
        conv = self._current_conv
        self.add_message(conv, "You", text)
        self.start_thinking(conv)
        self.set_state("listening")

        if self.web_search_enabled:
            self._clear_web_results()
            self.set_web_status("Searching the web…")

            search_worker = WebSearchWorker(text)
            self._active_workers.append(search_worker)

            def on_search_done(result: dict):
                if search_worker in self._active_workers:
                    self._active_workers.remove(search_worker)
                self.populate_web_results(result)
                contexte = self._build_search_context(result)
                self.sig_user_message.emit(conv, text, contexte)

            search_worker.done.connect(on_search_done)
            search_worker.start()
        else:
            self.sig_user_message.emit(conv, text, "")

    # ── Chat / rendu ─────────────────────────────────────────────────────────
    def _chat_add_widget(self, widget):
        idx = self._chat_layout.count() - 1  # avant le stretch final
        self._chat_layout.insertWidget(idx, widget)
        QTimer.singleShot(0, self._scroll_chat_to_bottom)

    def _scroll_chat_to_bottom(self):
        sb = self._chat_scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_chat_view(self):
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def add_message(self, conv: "Conversation", sender: str, text: str):
        conv.messages.append((sender, text))

        if conv.title == "New conversation" and sender.upper() == "YOU":
            conv.title = (text[:30] + "…") if len(text) > 30 else text
            self._refresh_sidebar()

        if conv is self._current_conv:
            if self._thinking_widget is not None:
                self._thinking_widget.deleteLater()
                self._thinking_widget = None
            self._chat_add_widget(MessageBubble(sender, text, THEMES[self._theme_name]))

    def start_thinking(self, conv: "Conversation"):
        if conv is self._current_conv:
            self._thinking_widget = ThinkingWidget(THEMES[self._theme_name])
            self._chat_add_widget(self._thinking_widget)

    def stop_thinking(self, conv: "Conversation"):
        if conv is self._current_conv and self._thinking_widget is not None:
            self._thinking_widget.deleteLater()
            self._thinking_widget = None

    def set_state(self, state: str):
        self._current_state = state
        self.mascot.set_state(state)
        labels = {
            "idle":      "STANDBY",
            "listening": "PROCESSING...",
            "speaking":  "SPEAKING",
        }
        self._state_lbl.setText(labels.get(state, "STANDBY"))

    # ── Fermeture avec message d'adieu ─────────────────────────────────────────
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
        conv = self._current_conv
        self.stop_thinking(conv)
        self.set_state("speaking" if self.voice_enabled else "idle")

        if self.voice_enabled:
            synth_worker = VoiceSynthWorker(GOODBYE_TEXT)
            self._active_workers = getattr(self, "_active_workers", [])
            self._active_workers.append(synth_worker)

            def on_synth_done(ok: bool):
                if synth_worker in self._active_workers:
                    self._active_workers.remove(synth_worker)
                self.add_message(conv, ASSISTANT_NAME, GOODBYE_TEXT)

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
            self.add_message(conv, ASSISTANT_NAME, GOODBYE_TEXT)
            QTimer.singleShot(700, self.sig_close_now.emit)

    def _do_close_now(self):
        self._ready_to_close = True
        self.close()


# ─── Worker thread pour la recherche web ──────────────────────────────────────
class WebSearchWorker(QThread):
    """Lance une recherche web (texte + images + vidéos) via DuckDuckGo."""
    done = pyqtSignal(dict)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        from core.websearch import search_text, search_images, search_videos
        result = {
            "text": search_text(self.query, max_results=5),
            "images": search_images(self.query, max_results=6),
            "videos": search_videos(self.query, max_results=4),
        }
        self.done.emit(result)


class ImageThumbWorker(QThread):
    """Télécharge les octets d'une image (miniature) pour l'afficher dans le panneau web."""
    done = pyqtSignal(bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        data = b""
        try:
            import urllib.request
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
        except Exception as e:
            print("Erreur téléchargement miniature :", e)
        self.done.emit(data)


# ─── Worker thread pour brain.py ──────────────────────────────────────────────
class BrainWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, message: str, historique: list, contexte: str = ""):
        super().__init__()
        self.message = message
        self.historique = historique
        self.contexte = contexte

    def run(self):
        from core.brain import demander
        reponse = demander(self.message, self.historique, self.contexte)
        self.response_ready.emit(reponse)


# ─── Worker thread pour la synthèse vocale (sans lecture) ────────────────────
class VoiceSynthWorker(QThread):
    done = pyqtSignal(bool)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        from core.voice import synthesize
        ok = synthesize(self.text)
        self.done.emit(ok)


# ─── Lancement ────────────────────────────────────────────────────────────────
def launch():
    app = QApplication(sys.argv)
    win = JarvisWindow()

    win._active_workers = []

    def on_user_message(conv, text: str, contexte: str):
        worker = BrainWorker(text, conv.brain_history, contexte)
        win._active_workers.append(worker)

        def cleanup():
            if worker in win._active_workers:
                win._active_workers.remove(worker)

        def on_response(reponse: str):
            if win.voice_enabled:
                synth_worker = VoiceSynthWorker(reponse)
                win._active_workers.append(synth_worker)

                def on_synth_done(ok: bool):
                    if synth_worker in win._active_workers:
                        win._active_workers.remove(synth_worker)
                    win.stop_thinking(conv)
                    win.add_message(conv, ASSISTANT_NAME, reponse)
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
                win.stop_thinking(conv)
                win.add_message(conv, ASSISTANT_NAME, reponse)
                win.set_state("idle")

        worker.response_ready.connect(on_response)
        worker.finished.connect(cleanup)
        worker.start()

    win.sig_user_message.connect(on_user_message)

    welcome = "Welcome sir. Systems online. How can I assist you today?"
    conv = win._current_conv

    if win.voice_enabled:
        welcome_worker = VoiceSynthWorker(welcome)
        win._active_workers.append(welcome_worker)

        def on_welcome_synth(ok: bool):
            if welcome_worker in win._active_workers:
                win._active_workers.remove(welcome_worker)
            win.add_message(conv, ASSISTANT_NAME, welcome)

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
        win.add_message(conv, ASSISTANT_NAME, welcome)

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()