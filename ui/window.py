"""
JARVIS - Interface graphique PyQt6
Orbe centrale qui pulse quand Jarvis parle
Style : Iron Man / Sci-fi futuriste
"""

import sys
import math
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient,
    QFont, QLinearGradient, QPainterPath
)


# ─── Orbe centrale ────────────────────────────────────────────────────────────
class OrbWidget(QWidget):
    """
    Orbe animée :
    - État repos   : pulse lent, anneau qui tourne doucement
    - État écoute  : anneau cyan vif, pulse moyen
    - État parole  : gros pulse, anneaux multiples rapides, halo explosif
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 320)

        # États
        self.state = "idle"   # "idle" | "listening" | "speaking"

        # Animation
        self._angle1 = 0.0
        self._angle2 = 0.0
        self._angle3 = 0.0
        self._pulse  = 0.0
        self._pulse_dir = 1
        self._halo  = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_state(self, state: str):
        """state = 'idle' | 'listening' | 'speaking'"""
        self.state = state

    def _tick(self):
        # Vitesse selon état
        speed = {"idle": 0.4, "listening": 0.8, "speaking": 1.8}.get(self.state, 0.4)

        self._angle1 = (self._angle1 + speed * 0.6) % 360
        self._angle2 = (self._angle2 - speed * 0.4) % 360
        self._angle3 = (self._angle3 + speed * 0.25) % 360

        pulse_speed = {"idle": 0.015, "listening": 0.025, "speaking": 0.045}.get(self.state, 0.015)
        self._pulse += pulse_speed * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse_dir = 1

        if self.state == "speaking":
            self._halo = min(1.0, self._halo + 0.04)
        else:
            self._halo = max(0.0, self._halo - 0.03)

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        r  = 90  # rayon de base de l'orbe

        # ── Halo externe (speaking uniquement) ───────────────────────────────
        if self._halo > 0:
            for i in range(3):
                halo_r = r + 55 + i * 22
                alpha  = int(self._halo * (40 - i * 12))
                g = QRadialGradient(cx, cy, halo_r)
                g.setColorAt(0.7, QColor(0, 212, 255, alpha))
                g.setColorAt(1.0, QColor(0, 212, 255, 0))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(g))
                p.drawEllipse(
                    int(cx - halo_r), int(cy - halo_r),
                    int(halo_r * 2), int(halo_r * 2)
                )

        # ── Glow de base ──────────────────────────────────────────────────────
        glow_size = r * (1.8 + 0.4 * self._pulse)
        if self.state == "speaking":
            glow_size = r * (2.2 + 0.6 * self._pulse)

        g = QRadialGradient(cx, cy, glow_size)
        if self.state == "speaking":
            g.setColorAt(0, QColor(0, 212, 255, int(60 + 40 * self._pulse)))
        elif self.state == "listening":
            g.setColorAt(0, QColor(0, 180, 255, int(35 + 25 * self._pulse)))
        else:
            g.setColorAt(0, QColor(0, 150, 200, int(20 + 15 * self._pulse)))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(
            int(cx - glow_size), int(cy - glow_size),
            int(glow_size * 2), int(glow_size * 2)
        )

        # ── Anneaux orbitaux ──────────────────────────────────────────────────
        rings = [
            (r + 18, self._angle1, 200, 1.2),
            (r + 10, self._angle2, 120, 0.8),
        ]
        if self.state in ("listening", "speaking"):
            rings.append((r + 32, self._angle3, 80, 0.6))
        if self.state == "speaking":
            rings.append((r + 46, -self._angle1 * 0.7, 60, 0.5))

        for radius, angle, alpha_base, width in rings:
            alpha = int(alpha_base * (0.6 + 0.4 * self._pulse))
            pen = QPen(QColor(0, 212, 255, alpha), width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            span = 220 if self.state == "speaking" else 160
            p.drawArc(rect, int(angle * 16), int(span * 16))

        # ── Corps de l'orbe ───────────────────────────────────────────────────
        orb_r = r * (1.0 + 0.06 * self._pulse)
        if self.state == "speaking":
            orb_r = r * (1.0 + 0.12 * self._pulse)

        orb_grad = QRadialGradient(cx - orb_r * 0.3, cy - orb_r * 0.3, orb_r * 1.3)
        if self.state == "speaking":
            orb_grad.setColorAt(0.0, QColor(0, 220, 255, 140))
            orb_grad.setColorAt(0.5, QColor(0, 140, 200, 80))
            orb_grad.setColorAt(1.0, QColor(2, 10, 20,  240))
            border = QColor(0, 212, 255, 220)
        elif self.state == "listening":
            orb_grad.setColorAt(0.0, QColor(0, 180, 255, 100))
            orb_grad.setColorAt(0.5, QColor(0, 110, 180, 60))
            orb_grad.setColorAt(1.0, QColor(2, 10, 20,  240))
            border = QColor(0, 180, 255, 160)
        else:
            orb_grad.setColorAt(0.0, QColor(0, 140, 200, 70))
            orb_grad.setColorAt(0.5, QColor(0,  90, 150, 40))
            orb_grad.setColorAt(1.0, QColor(2,  10,  20, 240))
            border = QColor(0, 140, 200, 100)

        p.setPen(QPen(border, 1.5))
        p.setBrush(QBrush(orb_grad))
        p.drawEllipse(
            QRectF(cx - orb_r, cy - orb_r, orb_r * 2, orb_r * 2)
        )

        # ── Reflet interne ────────────────────────────────────────────────────
        ref_grad = QRadialGradient(cx - orb_r * 0.2, cy - orb_r * 0.35, orb_r * 0.5)
        ref_grad.setColorAt(0, QColor(255, 255, 255, 30))
        ref_grad.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(ref_grad))
        p.drawEllipse(
            QRectF(cx - orb_r * 0.6, cy - orb_r * 0.6, orb_r * 1.2, orb_r * 1.2)
        )

        # ── Lettre J ──────────────────────────────────────────────────────────
        j_alpha = 30 if self.state == "speaking" else 150
        font = QFont("Courier New", 48, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor(0, 212, 255, j_alpha))
        p.drawText(
            QRectF(cx - 20, cy - 30, 40, 55),
            Qt.AlignmentFlag.AlignCenter,
            "J"
        )

        p.end()


# ─── Bulle de message ─────────────────────────────────────────────────────────
class MessageBubble(QFrame):
    def __init__(self, sender: str, text: str):
        super().__init__()
        is_jarvis = sender.upper() == "JARVIS"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        accent = "#00d4ff" if is_jarvis else "#f0a830"
        txt_color = "#a8d8ea" if is_jarvis else "#c8b090"

        lbl_who = QLabel(sender.upper())
        lbl_who.setStyleSheet(f"""
            font-family: 'Courier New', monospace;
            font-size: 9px;
            letter-spacing: 3px;
            color: {accent};
        """)

        lbl_text = QLabel(text)
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet(f"""
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: {txt_color};
            line-height: 1.6;
        """)

        layout.addWidget(lbl_who)
        layout.addWidget(lbl_text)

        self.setStyleSheet(f"""
            QFrame {{
                border-left: 2px solid {accent};
                background: transparent;
            }}
        """)


# ─── Fenêtre principale ────────────────────────────────────────────────────────
class JarvisWindow(QMainWindow):

    # Signaux pour communiquer avec brain.py / audio.py
    sig_user_message = pyqtSignal(str)   # message envoyé par l'utilisateur

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS")
        self.setMinimumSize(800, 600)
        self.resize(960, 640)
        self._session_start = time.time()
        self._msg_count = 0

        self._build_ui()
        self._start_timers()

        self.setStyleSheet("""
            QMainWindow, QWidget { background: #020c14; color: #a8d8ea; }
            QScrollBar:vertical {
                background: #041825; width: 4px;
            }
            QScrollBar::handle:vertical {
                background: #2a4a5a; border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

    # ── Construction UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._make_topbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._make_center(), 1)
        body.addWidget(self._make_chat_panel())
        layout.addLayout(body, 1)

        layout.addWidget(self._make_input_bar())

    def _make_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(46)
        bar.setStyleSheet("""
            QFrame {
                background: rgba(2,12,20,0.95);
                border-bottom: 1px solid rgba(0,212,255,0.15);
            }
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 0, 24, 0)

        title = QLabel("J A R V I S")
        title.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 8px;
            color: #00d4ff;
        """)

        self._dot = QLabel("●  ONLINE")
        self._dot.setStyleSheet("font-family:'Courier New',monospace;font-size:10px;color:#00ff88;letter-spacing:2px;")

        self._clock = QLabel()
        self._clock.setStyleSheet("font-family:'Courier New',monospace;font-size:12px;color:#00d4ff;")

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._dot)
        lay.addSpacing(24)
        lay.addWidget(self._clock)
        return bar

    def _make_center(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(12)

        self.orb = OrbWidget()
        lay.addStretch()
        lay.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignCenter)

        self._state_lbl = QLabel("STANDBY")
        self._state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_lbl.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 11px;
            letter-spacing: 4px;
            color: rgba(0,212,255,0.6);
        """)
        lay.addWidget(self._state_lbl)
        lay.addStretch()
        return w

    def _make_chat_panel(self):
        panel = QFrame()
        panel.setFixedWidth(300)
        panel.setStyleSheet("QFrame { border-left: 1px solid rgba(0,212,255,0.12); }")

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(8)

        title = QLabel("CONVERSATION LOG")
        title.setStyleSheet("font-family:'Courier New',monospace;font-size:9px;letter-spacing:3px;color:#2a4a5a;")
        lay.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._chat_widget = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_layout.setSpacing(8)
        self._chat_layout.addStretch()

        self._scroll.setWidget(self._chat_widget)
        lay.addWidget(self._scroll)
        return panel

    def _make_input_bar(self):
        bar = QFrame()
        bar.setFixedHeight(58)
        bar.setStyleSheet("""
            QFrame {
                background: rgba(2,12,20,0.95);
                border-top: 1px solid rgba(0,212,255,0.15);
            }
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Send a message to Jarvis...")
        self._input.setStyleSheet("""
            QLineEdit {
                background: rgba(0,212,255,0.04);
                border: 1px solid #2a4a5a;
                color: #a8d8ea;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 8px 14px;
            }
            QLineEdit:focus { border-color: #00d4ff; }
        """)
        self._input.returnPressed.connect(self._on_send)

        send_btn = QPushButton("SEND")
        send_btn.setFixedWidth(80)
        send_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #00d4ff;
                color: #00d4ff;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                letter-spacing: 2px;
                padding: 8px;
                background: transparent;
            }
            QPushButton:hover { background: rgba(0,212,255,0.1); }
            QPushButton:pressed { background: rgba(0,212,255,0.2); }
        """)
        send_btn.clicked.connect(self._on_send)

        lay.addWidget(self._input)
        lay.addWidget(send_btn)
        return bar

    # ── Timers ────────────────────────────────────────────────────────────────
    def _start_timers(self):
        t = QTimer(self)
        t.timeout.connect(lambda: self._clock.setText(datetime.now().strftime("%H:%M:%S")))
        t.start(1000)
        self._clock.setText(datetime.now().strftime("%H:%M:%S"))

        # Clignotement dot
        self._dot_on = True
        t2 = QTimer(self)
        t2.timeout.connect(self._blink)
        t2.start(1200)

    def _blink(self):
        self._dot_on = not self._dot_on
        color = "#00ff88" if self._dot_on else "#020c14"
        self.orb_state = getattr(self, '_current_state', 'idle')
        self._dot.setStyleSheet(f"font-family:'Courier New',monospace;font-size:10px;color:{color};letter-spacing:2px;")

    # ── Actions ───────────────────────────────────────────────────────────────
    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_message("You", text)
        self.set_state("listening")
        self.sig_user_message.emit(text)

    # ── API publique ──────────────────────────────────────────────────────────
    def add_message(self, sender: str, text: str):
        """Ajoute un message dans le chat."""
        bubble = MessageBubble(sender, text)
        count = self._chat_layout.count()
        self._chat_layout.insertWidget(count - 1, bubble)
        self._msg_count += 1
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def set_state(self, state: str):
        """
        state = 'idle' | 'listening' | 'speaking'
        Met à jour l'orbe et le label.
        """
        self._current_state = state
        self.orb.set_state(state)
        labels = {
            "idle":      "STANDBY",
            "listening": "PROCESSING...",
            "speaking":  "SPEAKING",
        }
        self._state_lbl.setText(labels.get(state, "STANDBY"))


# ─── Worker thread pour brain.py ──────────────────────────────────────────────
class BrainWorker(QThread):
    """
    Exécute demander() dans un thread séparé
    pour ne pas bloquer l'interface pendant que Mistral réfléchit.
    """
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

    # Connexion signal → worker → réponse
    workers = []  # garde les workers en mémoire

    def on_user_message(text: str):
        worker = BrainWorker(text)
        workers.append(worker)

        def on_response(reponse: str):
                if worker in workers:
                   workers.remove(worker)
         
                win.add_message("Jarvis", reponse)
                win.set_state("speaking")

            # Voix dans un thread séparé
                from core.voice import parler
                import threading
                def speak_then_idle():
                    parler(reponse)
                    win.set_state("idle")
                threading.Thread(target=speak_then_idle, daemon=True).start()

        worker.response_ready.connect(on_response)
        worker.start()

    win.sig_user_message.connect(on_user_message)

    # Message de bienvenue
    welcome = "Welcome sir. Systems online. How can I assist you today?"
    win.add_message("Jarvis", welcome)

    import threading
    from core.voice import parler
    threading.Thread(target=parler, args=(welcome,), daemon=True).start()

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()