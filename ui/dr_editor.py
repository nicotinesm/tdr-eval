"""Dialog for registering or editing a DR entry in dr_config.json."""

import re
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from config import REQUIRED_KEYS

# Strict charsets: registry keys also surface in logs, window titles and CSV
# file names, so reject anything outside the expected ticker alphabet.
SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,19}$")
TICKER_RE = re.compile(r"^[A-Z0-9.:-]{1,20}$")
PAIR_RE = re.compile(r"^[A-Z]{3,7}=X$")
MARKET_RE = re.compile(r"^[A-Z]{1,10}$")


class DREditorDialog(QDialog):
    """Modal form to add a new DR or edit an existing one.

    Emits `saved` with (dr_symbol, config_dict) on accept.
    """

    saved = pyqtSignal(str, dict)

    def __init__(self, config, dr_symbol: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._config = config
        self._original_symbol = dr_symbol
        self.setWindowTitle(
            f"Edit DR - {dr_symbol}" if dr_symbol else "Register New DR"
        )
        self.setMinimumWidth(420)

        existing = config.get_config(dr_symbol) if dr_symbol else {}

        title = QLabel(
            "Edit Depositary Receipt" if dr_symbol else "Register New Depositary Receipt"
        )
        title.setObjectName("SectionTitle")

        form = QFormLayout()
        form.setSpacing(10)

        self.symbol_edit = self._make_field("DR Symbol", form, existing.get("symbol"))
        self.ticker_edit = self._make_field(
            "Underlying Ticker", form, existing.get("underlying_ticker", "")
        )
        self.pair_edit = self._make_field(
            "Currency Pair", form, existing.get("currency_pair", "THB=X")
        )
        self.ratio_edit = self._make_field(
            "Ratio", form, self._fmt(existing.get("ratio"))
        )
        self.market_edit = self._make_field("Market", form, existing.get("market", ""))
        self.name_edit = self._make_field("Name", form, existing.get("name", ""))
        self.tick_edit = self._make_field(
            "Underlying Tick Size", form, self._fmt(existing.get("underlying_tick_size"))
        )

        if dr_symbol:
            self.symbol_edit.setText(dr_symbol)
            self.symbol_edit.setReadOnly(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.error_label.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(buttons)

        self.ticker_edit.setFocus()

    # ------------------------------------------------------------- Helpers
    def _make_field(self, name: str, form: QFormLayout, value: str) -> QLineEdit:
        label = QLabel(name)
        label.setObjectName("FieldLabel")
        edit = QLineEdit(str(value) if value else "")
        edit.setObjectName("numberEdit")
        form.addRow(label, edit)
        return edit

    @staticmethod
    def _fmt(value) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    def _parse_float(self, edit: QLineEdit) -> Optional[float]:
        text = edit.text().strip().replace(",", "").replace(" ", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def _on_save(self):
        symbol = self.symbol_edit.text().strip().upper()
        ticker = self.ticker_edit.text().strip().upper()
        pair = self.pair_edit.text().strip().upper()
        ratio = self._parse_float(self.ratio_edit)
        tick_size = self._parse_float(self.tick_edit)

        if not symbol or not SYMBOL_RE.match(symbol):
            self._show_error("DR Symbol must be 1-20 chars: A-Z, 0-9, . _ -")
            return
        if not ticker or not TICKER_RE.match(ticker):
            self._show_error("Underlying Ticker must be 1-20 chars: A-Z, 0-9, . : -")
            return
        if not pair or not PAIR_RE.match(pair):
            self._show_error("Currency Pair must look like THB=X or HKDTHB=X.")
            return
        if ratio is None or ratio <= 0:
            self._show_error("Ratio must be a positive number.")
            return
        if self._original_symbol != symbol and self._config.has(symbol):
            self._show_error(f"DR '{symbol}' already exists in the registry.")
            return

        cfg = {
            "underlying_ticker": ticker,
            "currency_pair": pair,
            "ratio": ratio,
        }
        market = self.market_edit.text().strip().upper()
        if market and not MARKET_RE.match(market):
            self._show_error("Market must be 1-10 letters (e.g. US, HK, JP).")
            return
        if market:
            cfg["market"] = market
        name = self.name_edit.text().strip()[:60]
        if name:
            cfg["name"] = name
        if tick_size is not None and tick_size > 0:
            cfg["underlying_tick_size"] = tick_size

        self.saved.emit(symbol, cfg)
        self.accept()


def open_dr_editor(config, dr_symbol: Optional[str] = None, parent=None) -> Optional[tuple]:
    """Run the editor modally; return (symbol, cfg) or None if cancelled."""
    dlg = DREditorDialog(config, dr_symbol, parent)
    result = {"v": None}
    dlg.saved.connect(lambda symbol, cfg: result.update(v=(symbol, cfg)))
    dlg.exec()
    return result["v"]
