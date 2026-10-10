"""Asynchronous background worker for data fetching."""

from PyQt6.QtCore import QThread, pyqtSignal

from data_fetcher import FetchResult, YahooFinanceFetcher


class FetchWorker(QThread):
    # NOTE: named `result_ready` (not `finished`) so the built-in QThread.finished
    # signal stays intact. The controller connects deleteLater to the built-in
    # finished, which is only emitted AFTER the thread has terminated — deleting
    # a still-running QThread crashes.
    result_ready = pyqtSignal(object, str)  # (FetchResult, dr_symbol)

    def __init__(
        self,
        fetcher: YahooFinanceFetcher,
        dr_symbol: str,
        dr_config: dict,
        parent=None,
    ):
        super().__init__(parent)
        self.fetcher = fetcher
        self.dr_symbol = dr_symbol
        self.dr_config = dr_config

    def run(self):
        result = self.fetcher.fetch(self.dr_config)
        self.result_ready.emit(result, self.dr_symbol)
