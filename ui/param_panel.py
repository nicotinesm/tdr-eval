"""Parameter panel: editable underlying price, FX rate, and locked ratio."""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QFrame, QLabel, QLineEdit, QVBoxLayout


class ParamPanel(QFrame):
    value_edited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("section", "parameters")

        title = QLabel("Parameters")
        title.setObjectName("SectionTitle")

        form = QFormLayout()
        form.setContentsMargins(16, 12, 16, 16)
        form.setSpacing(10)

        self.price_edit = self._make_field("Underlying Price", form)
        self.fx_edit = self._make_field("Exchange Rate", form)

        ratio_label = QLabel("Ratio")
        ratio_label.setObjectName("FieldLabel")
        self.ratio_edit = QLineEdit()
        self.ratio_edit.setObjectName("ratioEdit")
        self.ratio_edit.setReadOnly(True)
        self.ratio_edit.setPlaceholderText("-")
        self.ratio_edit.setToolTip("DR ratio (locked from registry)")
        form.addRow(ratio_label, self.ratio_edit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title)
        layout.addLayout(form)

        self.price_edit.textEdited.connect(self._on_edit)
        self.fx_edit.textEdited.connect(self._on_edit)

    def _make_field(self, name: str, form: QFormLayout) -> QLineEdit:
        label = QLabel(name)
        label.setObjectName("FieldLabel")
        edit = QLineEdit()
        edit.setObjectName("numberEdit")
        edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        edit.setPlaceholderText("0.00")
        form.addRow(label, edit)
        return edit

    def _on_edit(self):
        self.value_edited.emit()

    def underlying_price(self) -> Optional[float]:
        return self._parse(self.price_edit)

    def fx_rate(self) -> Optional[float]:
        return self._parse(self.fx_edit)

    def ratio(self) -> Optional[float]:
        return self._parse(self.ratio_edit)

    @staticmethod
    def _parse(edit: QLineEdit) -> Optional[float]:
        text = edit.text().strip().replace(",", "").replace(" ", "")
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
        return value

    def set_underlying_price(self, value: float):
        self._set_safely(self.price_edit, value)

    def set_fx_rate(self, value: float):
        self._set_safely(self.fx_edit, value)

    def set_ratio(self, value: float):
        self._set_safely(self.ratio_edit, value)

    @staticmethod
    def _set_safely(edit: QLineEdit, value: float):
        # Plain decimal representation without thousands commas to prevent parsing errors
        edit.setText(f"{value:.4f}".rstrip("0").rstrip("."))

    def validate(self) -> bool:
        price, fx, ratio = self.underlying_price(), self.fx_rate(), self.ratio()
        ok = price is not None and price > 0 and fx is not None and fx > 0
        self._mark_valid(self.price_edit, price is not None and price > 0)
        self._mark_valid(self.fx_edit, fx is not None and fx > 0)
        return ok

    @staticmethod
    def _mark_valid(edit: QLineEdit, valid: bool):
        if valid:
            edit.setProperty("invalid", False)
        else:
            edit.setProperty("invalid", True)
        edit.style().unpolish(edit)
        edit.style().polish(edit)
