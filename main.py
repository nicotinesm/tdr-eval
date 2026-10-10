"""DR Price Evaluation Tool for the Thailand market.

Entry point: python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication


def main() -> int:
    from utils.logger import setup_logging

    logger = setup_logging()
    logger.info("Starting DR Price Evaluator")

    from app_controller import AppController
    from config import DRConfig
    from data_fetcher import YahooFinanceFetcher
    from engine import CalculationEngine
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("DR Price Evaluator")
    app.setOrganizationName("TH-DR")

    config = DRConfig()
    fetcher = YahooFinanceFetcher(cache_ttl=60)
    engine = CalculationEngine()

    view = MainWindow(config)
    controller = AppController(config, fetcher, engine, view)
    view.destroyed.connect(controller.deleteLater)

    view.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
