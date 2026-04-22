# Asset Universes Definition

UNIVERSES = {
    "CRYPTO_TOP_20": [
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", 
        "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
        "MATIC-USD", "SHIB-USD", "TRX-USD", "LTC-USD", "BCH-USD",
        "UNI-USD", "ATOM-USD", "XLM-USD", "ETC-USD", "FIL-USD"
    ],
    "MAGNIFICENT_7": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"
    ],
    "SP500_SECTOR_ETFs": [
        "XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLB", "XLRE", "XLU", "XLC"
    ],
    "HIGH_VOLATILITY": [
        "TSLA", "COIN", "MARA", "RIOT", "MSTR", "GME", "AMC", "UPST", "PLTR", "AI"
    ],
    "STABLE_DIVIDEND": [
        "KO", "PEP", "PG", "JNJ", "MMM", "XOM", "CVX", "VZ", "T", "ABBV"
    ],
    "INDIAN_BLUE_CHIPS": [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS"
    ],
    "FOREX_MAJORS": [
        "EURUSD=X", "GBPUSD=X", "JPY=X", "GBP=X", "USDCHF=X", "AUDUSD=X", "USDCAD=X"
    ]
}

# Create a combined "ALL" universe
ALL_SYMBOLS = set()
for symbols in UNIVERSES.values():
    ALL_SYMBOLS.update(symbols)

UNIVERSES["ALL_ASSETS_COMBINED"] = sorted(list(ALL_SYMBOLS))
