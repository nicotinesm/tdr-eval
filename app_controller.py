"""Controller wiring the config, fetcher, engine and view together."""

from PyQt6.QtCore import QObject, pyqtSlot

from ui.fetch_worker import FetchWorker
from utils.debounce import Debouncer
from utils.logger import get_logger, safe

logger = get_logger("controller")


class AppController(QObject):
    def __init__(self, config, fetcher, engine, view, parent=None):
        super().__init__(parent)
        self.config = config
        self.fetcher = fetcher
        self.engine = engine
        self.view = view
        self._current_config = None
        self._active_worker = None
        self._workers: set = set()

        self._param_debouncer = Debouncer(self.recalculate, delay_ms=200)
        self._param_debouncer.bind(self)

        view.dr_selected.connect(self.on_dr_selected)
        view.fetch_clicked.connect(self.on_fetch_clicked)
        view.params_changed.connect(self.on_params_changed)
        view.dr_saved.connect(self.on_dr_saved)

    # ----------------------------------------------------------- Slots
    @pyqtSlot(str)
    def on_dr_selected(self, dr_symbol: str):
        if not self.config.has(dr_symbol):
            return
        cfg = self.config.get_config(dr_symbol)
        self._current_config = cfg
        self.view.clear_error()
        self.view.set_ratio(float(cfg["ratio"]))
        name = cfg.get("name", "")
        if name:
            self.view.setWindowTitle(f"DR Price Evaluator - {dr_symbol} ({name})")
        else:
            self.view.setWindowTitle(f"DR Price Evaluator - {dr_symbol}")
        logger.info("DR selected: %s", safe(dr_symbol))
        self.on_fetch_clicked()

    @pyqtSlot(bool)
    def on_fetch_clicked(self, force: bool = False):
        dr = self.view.current_dr()
        if not dr or not self.config.has(dr):
            self.view.show_error(f"DR symbol not in registry: '{dr or '(empty)'}'")
            return

        cfg = self.config.get_config(dr)
        self._current_config = cfg
        if force:
            # Manual refresh: bypass the 60s result cache.
            self.fetcher.invalidate(cfg["underlying_ticker"], cfg["currency_pair"])
        self.view.set_fetching(True)
        self.view.clear_error()
        logger.info("Starting background fetch for %s (force=%s)", safe(dr), force)

        # Launch a background worker QThread. A previously running worker cannot
        # be interrupted (its run() performs blocking network I/O), so it is
        # left to finish on its own; it self-deletes and its result is ignored
        # by _on_fetch_finished, which only accepts the current worker. Workers
        # have no parent so closing the app cannot destroy a running thread.
        worker = FetchWorker(self.fetcher, dr, cfg)
        worker.result_ready.connect(self._on_fetch_finished)
        # Discard + delete only once the thread has fully terminated (built-in
        # `finished` fires after run() exits); dropping the reference earlier
        # would let GC destroy a still-running QThread and crash the app.
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        self._workers.add(worker)
        worker.start()
        self._active_worker = worker

    @pyqtSlot(object, str)
    def _on_fetch_finished(self, result, dr_symbol: str):
        # Only the current worker may touch the UI. A stale worker that
        # finished in the background is ignored entirely (no state change).
        if self.sender() is not self._active_worker:
            logger.info("Ignoring stale fetch result for %s", safe(dr_symbol))
            return
        self._active_worker = None
        self.view.set_fetching(False)

        # Race-condition guard: Discard result if user switched to another DR during fetch
        if dr_symbol != self.view.current_dr():
            logger.info("Discarding stale fetch result for %s (current: %s)", safe(dr_symbol), safe(self.view.current_dr()))
            return

        if result.error:
            self.view.show_error(result.error)
            logger.error("Fetch error for %s: %s", safe(dr_symbol), safe(result.error))
            return

        self.view.set_underlying_price(result.price)
        self.view.set_fx_rate(result.fx_rate)
        self.view.set_last_update(
            result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            result.price_source,
            result.fx_source,
        )
        self.recalculate()

    @pyqtSlot()
    def on_params_changed(self):
        self._param_debouncer()

    @pyqtSlot(str, dict)
    def on_dr_saved(self, dr_symbol: str, cfg: dict):
        self.config.upsert(dr_symbol, cfg)
        self.view.refresh_dr_list(dr_symbol)
        self.view.clear_error()
        logger.info("DR registry updated: %s", safe(dr_symbol))
        self.on_dr_selected(dr_symbol)

    # ------------------------------------------------------- Recalc
    def recalculate(self):
        if self._current_config is None:
            return
        ul = self.view.underlying_price()
        fx = self.view.fx_rate()
        ratio = self.view.ratio()

        # validate() both marks the offending field (red border) and reports
        # whether the values are usable, so it must run before any early return.
        if not self.view.param_panel.validate():
            self.view.show_error("Enter positive price and FX rate.")
            return

        self.view.clear_error()
        try:
            levels = self.engine.generate_price_table(ul, fx, ratio)
        except ValueError as exc:
            self.view.show_error(str(exc))
            return

        rows = [
            {
                "level": lvl.level,
                "underlying_price": lvl.underlying_price,
                "fx_rate": lvl.fx_rate,
                "raw_dr": lvl.raw_dr,
                "dr_price": lvl.dr_price,
            }
            for lvl in levels
        ]
        self.view.update_table(rows)

        center = next(l for l in levels if l.level == 0)
        self.view.set_inavg(
            f"Indicative DR price (iNAV): THB {center.dr_price:,.2f}"
        )
        self.view.statusBar().showMessage(f"Calculated {len(rows)} levels.")
