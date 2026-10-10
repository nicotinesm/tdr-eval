"""Editable, auto-completing combo box for DR selection."""

from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QCompleter


class DRSearchCombo(QComboBox):
    dr_selected = pyqtSignal(str)

    def __init__(self, dr_names: List[str], parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setPlaceholderText("Select or type a DR symbol...")
        self.addItems(dr_names)
        self.setCurrentIndex(-1)

        self._completer = QCompleter(dr_names, self)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(self._completer)

        self._last_emitted: str = ""

        self.currentIndexChanged.connect(self._on_index_changed)
        self.activated.connect(self._on_activated)
        if self.lineEdit():
            self.lineEdit().returnPressed.connect(self._on_return_pressed)
        self._completer.activated.connect(self._emit_symbol)

    def _on_index_changed(self, index: int):
        if 0 <= index < self.count():
            self._emit_symbol(self.itemText(index))

    def _on_activated(self, index_or_text):
        if isinstance(index_or_text, int):
            if 0 <= index_or_text < self.count():
                self._emit_symbol(self.itemText(index_or_text))
        else:
            self._emit_symbol(str(index_or_text))

    def _on_return_pressed(self):
        text = self.current_dr()
        if text:
            self._emit_symbol(text)

    def _emit_symbol(self, raw_symbol: str):
        symbol = str(raw_symbol).strip().upper()
        if not symbol:
            return
        if symbol != self._last_emitted:
            self._last_emitted = symbol
            self.dr_selected.emit(symbol)

    def current_dr(self) -> str:
        return self.currentText().strip().upper()

    def set_dr(self, symbol: str):
        symbol = symbol.strip().upper()
        idx = self.findText(symbol, Qt.MatchFlag.MatchExactly)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentText(symbol)
