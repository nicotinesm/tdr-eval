"""Read-only price table showing the 21-level iNAV grid."""

import csv
import os
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

COLUMNS = ["Level", "Underlying Price", "FX", "Raw DR (THB)", "SET DR (Rounded)"]
CENTER_BG = QColor("#16a34a")
CENTER_FG = QColor("#ffffff")

# Cells starting with these characters execute as formulas when a CSV is
# opened in Excel/LibreOffice. Prefix with a single quote so the value is
# treated as literal text (OWASP CSV Injection mitigation).
_CSV_UNSAFE_LEADING = ("=", "+", "-", "@", "|", "%")


def sanitize_csv_cell(value) -> str:
    text = str(value)
    if text.startswith(_CSV_UNSAFE_LEADING):
        return "'" + text
    return text


class PriceTableView(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.setMinimumHeight(320)

    def update_table(self, levels: List[dict]):
        self.setRowCount(len(levels))
        for row, entry in enumerate(levels):
            values = [
                f"{entry['level']:+d}" if entry["level"] else "0",
                f"{entry['underlying_price']:,.4f}",
                f"{entry['fx_rate']:,.4f}",
                f"{entry['raw_dr']:,.4f}",
                f"{entry['dr_price']:,.2f}",
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                if entry["level"] == 0:
                    item.setBackground(CENTER_BG)
                    item.setForeground(CENTER_FG)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.setItem(row, col, item)
        self.resizeRowsToContents()

    def export_csv(self, dr_symbol: str):
        default = os.path.join(
            os.path.expanduser("~"), f"DR_{dr_symbol}_price_grid.csv"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Price Grid", default, "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(COLUMNS)
                for row in range(self.rowCount()):
                    writer.writerow(
                        sanitize_csv_cell(self.item(row, col).text())
                        if self.item(row, col)
                        else ""
                        for col in range(self.columnCount())
                    )
        except OSError as exc:
            QMessageBox.critical(
                self, "Export Failed", f"Could not write CSV:\n{exc}"
            )
            return
        QMessageBox.information(self, "Export Complete", f"Saved to:\n{path}")
