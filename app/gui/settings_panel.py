from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class SettingsPanel(QWidget):
    def __init__(self, context):
        super().__init__()
        names = "\n".join(f"{k}: {v}" for k, v in context.detector.names.items())
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Model classes:\n"
            f"{names}\n\n"
            "Telegram reads .env values:\n"
            "TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_MESSAGE_THREAD_ID\n\n"
            f"Model path: {context.config['model']['path']}\n"
            f"Database: {context.config['database']['path']}"
        )
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings"))
        layout.addWidget(text)
