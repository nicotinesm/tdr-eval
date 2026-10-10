"""Configuration manager for the DR registry.

Reads dr_config.json which maps Thai DR symbols to their underlying
ticker, currency pair, ratio and tick size.
"""

import json
import os
import sys
from typing import Dict, List

REQUIRED_KEYS = ("underlying_ticker", "currency_pair", "ratio")


class DRConfig:
    def __init__(self, config_path: str = "dr_config.json"):
        self.config_path = self._resolve_path(config_path)
        self._data: Dict[str, dict] = self._load(self.config_path)

    @staticmethod
    def _resolve_path(config_path: str) -> str:
        if os.path.isabs(config_path):
            return config_path
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), config_path))
        candidates.append(os.path.abspath(config_path))
        candidates.append(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), config_path)
        )
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0]

    @staticmethod
    def _load(path: str) -> Dict[str, dict]:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError("dr_config.json must contain a JSON object.")
        for symbol, cfg in raw.items():
            for key in REQUIRED_KEYS:
                if key not in cfg:
                    raise ValueError(
                        f"DR '{symbol}' is missing required key '{key}'."
                    )
        return raw

    def get_all_dr_names(self) -> List[str]:
        return list(self._data.keys())

    def get_config(self, dr_symbol: str) -> dict:
        if dr_symbol not in self._data:
            raise KeyError(f"DR symbol not found in registry: {dr_symbol}")
        return self._data[dr_symbol]

    def has(self, dr_symbol: str) -> bool:
        return dr_symbol in self._data

    def upsert(self, dr_symbol: str, cfg: dict) -> None:
        """Add or replace a DR entry and persist the registry to disk."""
        for key in REQUIRED_KEYS:
            if key not in cfg:
                raise ValueError(f"DR '{dr_symbol}' is missing required key '{key}'.")
        self._data[dr_symbol] = cfg
        self._write()

    def _write(self) -> None:
        data = {symbol: self._ordered(cfg) for symbol, cfg in self._data.items()}
        # Atomic write: a crash mid-write must never leave a truncated registry.
        tmp_path = self.config_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.config_path)

    @staticmethod
    def _ordered(cfg: dict) -> dict:
        order = REQUIRED_KEYS + ("market", "name", "underlying_tick_size")
        return {k: cfg[k] for k in order if k in cfg}

    @property
    def data(self) -> Dict[str, dict]:
        return self._data
