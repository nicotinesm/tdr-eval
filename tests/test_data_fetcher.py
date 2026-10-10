import unittest

from data_fetcher import YahooFinanceFetcher


class TestTradingViewCandidates(unittest.TestCase):
    def test_us_maps_to_nasdaq_nyse_amex(self):
        slug, tickers = YahooFinanceFetcher._tv_candidates("US", "BAC")
        self.assertEqual(slug, "america")
        self.assertIn("NYSE:BAC", tickers)
        self.assertIn("NASDAQ:BAC", tickers)

        slug, tickers = YahooFinanceFetcher._tv_candidates("US", "TSLA")
        self.assertEqual(slug, "america")
        self.assertEqual(tickers, ["NASDAQ:TSLA", "NYSE:TSLA", "AMEX:TSLA"])

    def test_hk_strips_suffix(self):
        slug, tickers = YahooFinanceFetcher._tv_candidates("HK", "9988.HK")
        self.assertEqual(slug, "hongkong")
        self.assertEqual(tickers, ["HKEX:9988"])

    def test_jp_maps_to_tse(self):
        slug, tickers = YahooFinanceFetcher._tv_candidates("JP", "6857.T")
        self.assertEqual(slug, "asia")
        self.assertEqual(tickers, ["TSE:6857"])

    def test_cn_maps_to_sse_and_szse(self):
        slug, tickers = YahooFinanceFetcher._tv_candidates("CN", "688713.SS")
        self.assertEqual(slug, "asia")
        self.assertIn("SSE:688713", tickers)
        self.assertIn("SZSE:688713", tickers)

        slug, tickers = YahooFinanceFetcher._tv_candidates("CN", "300750.SZ")
        self.assertIn("SZSE:300750", tickers)

    def test_sg_maps_to_sgx(self):
        slug, tickers = YahooFinanceFetcher._tv_candidates("SG", "N6M.SI")
        self.assertEqual(slug, "asia")
        self.assertEqual(tickers, ["SGX:N6M"])

    def test_fr_de_dk_tw_vn(self):
        self.assertEqual(
            YahooFinanceFetcher._tv_candidates("FR", "RMS.PA"),
            ("europe", ["EURONEXT:RMS"]),
        )
        slug, tickers = YahooFinanceFetcher._tv_candidates("DE", "DEAM.DE")
        self.assertEqual(slug, "europe")
        self.assertEqual(tickers, ["XETR:DEAM", "EURONEXT:DEAM"])
        self.assertEqual(
            YahooFinanceFetcher._tv_candidates("DK", "NOVO-B.CO"),
            ("europe", ["CPH:NOVO-B"]),
        )
        self.assertEqual(
            YahooFinanceFetcher._tv_candidates("TW", "0050.TW"),
            ("taiwan", ["TWSE:0050"]),
        )
        slug, tickers = YahooFinanceFetcher._tv_candidates("VN", "FPT.VN")
        self.assertEqual(slug, "vietnam")
        self.assertEqual(tickers, ["HOSE:FPT", "HNX:FPT"])

    def test_unknown_market_defaults_to_hongkong(self):
        slug, tickers = YahooFinanceFetcher._tv_candidates("XX", "FOO")
        self.assertEqual(slug, "hongkong")
        self.assertEqual(tickers, ["HKEX:FOO"])


if __name__ == "__main__":
    unittest.main()
