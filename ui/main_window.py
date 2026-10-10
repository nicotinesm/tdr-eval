"""Main application window assembling the full UI."""

import os
from typing import List, Optional

from PyQt6.QtCore import QSettings, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.dr_search import DRSearchCombo
from ui.param_panel import ParamPanel
from ui.price_table import PriceTableView

THEMES = {"light": "light.qss", "dark": "dark.qss"}


def _styles_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")


class MainWindow(QMainWindow):
    dr_selected = pyqtSignal(str)
    fetch_clicked = pyqtSignal(bool)  # True = manual refresh (force), False = auto-fetch
    params_changed = pyqtSignal()
    dr_saved = pyqtSignal(str, dict)  # (dr_symbol, config) after editor accept

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setObjectName("MainWindow")
        self.setWindowTitle("DR Price Evaluator - Thailand")
        self.resize(1120, 780)
        self._config = config
        self._settings = QSettings("TH-DR", "DRPriceEvaluator")
        self._theme = self._settings.value("theme", "dark", type=str)

        self._build_ui()
        self._build_shortcuts()
        self.apply_theme(self._theme)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("MainWindow")
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 12)
        root.setSpacing(14)

        root.addLayout(self._header())

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._left_panel(), stretch=0)
        body.addWidget(self._table_card(), stretch=1)
        root.addLayout(body, stretch=1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready.")

    def _header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("DR Price Evaluator")
        title.setObjectName("AppTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.inaverage_label = QLabel()
        self.inaverage_label.setObjectName("HighlightText")
        self.inaverage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.inaverage_label)

        self.last_update_label = QLabel("Last update: -")
        self.last_update_label.setObjectName("StatusLabel")
        header.addWidget(self.last_update_label)

        export_button = QPushButton("Export CSV")
        export_button.setObjectName("SecondaryButton")
        export_button.clicked.connect(self._export)
        header.addWidget(export_button)

        self.theme_button = QPushButton("Dark Mode")
        self.theme_button.setObjectName("SecondaryButton")
        self.theme_button.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_button)
        return header

    def _left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("SidePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._dr_card())

        self.param_panel = ParamPanel()
        self.param_panel.value_edited.connect(self.params_changed)
        layout.addWidget(self.param_panel)

        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.setToolTip("Fetch live underlying price and FX rate (Ctrl+R)")
        self.fetch_button.clicked.connect(lambda _checked=False: self.fetch_clicked.emit(True))
        layout.addWidget(self.fetch_button)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        layout.addStretch(1)
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(360)
        return panel

    def _dr_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Select Depositary Receipt")
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        head.addStretch(1)

        self.edit_button = QPushButton("Add / Edit")
        self.edit_button.setObjectName("SecondaryButton")
        self.edit_button.setToolTip("Register a new DR or edit the selected one")
        self.edit_button.clicked.connect(self._open_editor)
        head.addWidget(self.edit_button)
        layout.addLayout(head)

        self.dr_combo = DRSearchCombo(self._config.get_all_dr_names())
        self.dr_combo.setMinimumWidth(0)
        layout.addWidget(self.dr_combo)

        self.dr_combo.dr_selected.connect(self.dr_selected)
        return card

    def _open_editor(self):
        from ui.dr_editor import open_dr_editor

        current = self.current_dr()
        symbol = current if current and self._config.has(current) else None
        result = open_dr_editor(self._config, symbol, self)
        if result:
            new_symbol, cfg = result
            self.dr_saved.emit(new_symbol, cfg)

    def _table_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Price Table (±10 Ticks)")
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        head.addStretch(1)
        layout.addLayout(head)

        self.price_table = PriceTableView()
        layout.addWidget(self.price_table)
        return card

    def _build_shortcuts(self):
        if self.dr_combo.lineEdit():
            QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
                self.dr_combo.lineEdit().setFocus
            )
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(
            lambda: self.fetch_clicked.emit(True)
        )

    # ------------------------------------------------------------- Theming
    def apply_theme(self, theme: str):
        if theme not in THEMES:
            theme = "light"
        self._theme = theme
        self._settings.setValue("theme", theme)
        qss_path = os.path.join(_styles_dir(), THEMES[theme])
        with open(qss_path, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())
        self.theme_button.setText(
            "Light Mode" if theme == "dark" else "Dark Mode"
        )
        self.theme_button.setProperty("theme", theme)
        self.theme_button.style().unpolish(self.theme_button)
        self.theme_button.style().polish(self.theme_button)

    def toggle_theme(self):
        self.apply_theme("dark" if self._theme == "light" else "light")

    @property
    def theme(self) -> str:
        return self._theme

    # --------------------------------------------------------- DR helpers
    def current_dr(self) -> str:
        return self.dr_combo.current_dr()

    def refresh_dr_list(self, select_symbol: str = ""):
        """Reload the combo from the registry, optionally re-selecting a symbol."""
        self.dr_combo.blockSignals(True)
        self.dr_combo.clear()
        self.dr_combo.addItems(self._config.get_all_dr_names())
        self.dr_combo.setCurrentIndex(-1)
        self.dr_combo.blockSignals(False)
        if select_symbol:
            self.dr_combo.set_dr(select_symbol)

    def set_ratio(self, value: float):
        self.param_panel.set_ratio(value)

    def set_underlying_price(self, value: float):
        self.param_panel.set_underlying_price(value)

    def set_fx_rate(self, value: float):
        self.param_panel.set_fx_rate(value)

    def underlying_price(self) -> Optional[float]:
        return self.param_panel.underlying_price()

    def fx_rate(self) -> Optional[float]:
        return self.param_panel.fx_rate()

    def ratio(self) -> Optional[float]:
        return self.param_panel.ratio()

    # ------------------------------------------------------------- Status
    def set_last_update(self, timestamp_str: str, price_src: str = "", fx_src: str = ""):
        src_info = f" [Price: {price_src} | FX: {fx_src}]" if price_src and fx_src else ""
        self.last_update_label.setText(f"Last update: {timestamp_str}{src_info}")

    def show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self):
        self.error_label.clear()
        self.error_label.hide()

    def set_fetching(self, fetching: bool):
        self.fetch_button.setEnabled(not fetching)
        self.fetch_button.setText("Fetching..." if fetching else "Fetch Data")

    def update_table(self, levels: List[dict]):
        self.price_table.update_table(levels)

    def set_inavg(self, text: str):
        self.inaverage_label.setText(text)

    def _export(self):
        self.price_table.export_csv(self.current_dr() or "DR")
