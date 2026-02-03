"""암호화폐 데이터 스크래퍼 (업비트 + 바이낸스)."""

import pandas as pd
import requests
import time
from datetime import datetime


class _SimpleCache:
    """간단한 TTL 캐시."""
    def __init__(self, ttl_seconds: int = 60):
        self._cache = {}
        self._ttl = ttl_seconds

    def get(self, key: str):
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return data
            del self._cache[key]
        return None

    def set(self, key: str, data):
        self._cache[key] = (data, time.time())


# 바이낸스 코인 한글명 매핑
COIN_NAMES_KR = {
    'BTC': '비트코인', 'ETH': '이더리움', 'XRP': '리플', 'SOL': '솔라나',
    'DOGE': '도지코인', 'ADA': '에이다', 'AVAX': '아발란체', 'DOT': '폴카닷',
    'MATIC': '폴리곤', 'LINK': '체인링크', 'SHIB': '시바이누', 'UNI': '유니스왑',
    'ATOM': '코스모스', 'LTC': '라이트코인', 'ETC': '이더리움클래식',
    'NEAR': '니어프로토콜', 'APT': '앱토스', 'ARB': '아비트럼',
    'OP': '옵티미즘', 'FIL': '파일코인', 'SAND': '샌드박스',
    'MANA': '디센트럴랜드', 'AXS': '엑시인피니티', 'AAVE': '에이브',
    'SUI': '수이', 'SEI': '세이', 'TIA': '셀레스티아',
    'PEPE': '페페', 'WIF': '위프', 'BONK': '봉크',
    'TRX': '트론', 'BCH': '비트코인캐시', 'ALGO': '알고랜드',
    'FTM': '팬텀', 'IMX': '이뮤터블X', 'INJ': '인젝티브',
    'RENDER': '렌더', 'GRT': '더그래프', 'STX': '스택스',
    'BNB': '바이낸스코인', 'TON': '톤코인', 'HBAR': '헤데라',
}


class UpbitScraper:
    """업비트 공개 API 스크래퍼."""

    BASE_URL = "https://api.upbit.com/v1"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        self._cache = _SimpleCache(ttl_seconds=60)
        self._candle_cache = _SimpleCache(ttl_seconds=300)

    def get_krw_markets(self) -> pd.DataFrame:
        """KRW 마켓 코인 목록 조회."""
        cached = self._cache.get("krw_markets")
        if cached is not None:
            return cached

        try:
            resp = self.session.get(f"{self.BASE_URL}/market/all", params={"is_details": "true"}, timeout=10)
            data = resp.json()

            records = []
            for item in data:
                if item['market'].startswith('KRW-'):
                    records.append({
                        'market': item['market'],
                        'symbol': item['market'].replace('KRW-', ''),
                        'korean_name': item.get('korean_name', ''),
                        'english_name': item.get('english_name', ''),
                    })

            df = pd.DataFrame(records)
            self._cache.set("krw_markets", df)
            return df

        except Exception as e:
            print(f"업비트 마켓 조회 오류: {e}")
            return pd.DataFrame()

    def get_tickers(self, markets: list = None) -> pd.DataFrame:
        """현재가 일괄 조회."""
        if markets is None:
            market_df = self.get_krw_markets()
            if market_df.empty:
                return pd.DataFrame()
            markets = market_df['market'].tolist()

        cache_key = "tickers_" + str(len(markets))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            markets_str = ",".join(markets)
            resp = self.session.get(f"{self.BASE_URL}/ticker", params={"markets": markets_str}, timeout=10)
            data = resp.json()

            # 한글명 매핑
            market_df = self.get_krw_markets()
            name_map = {}
            if not market_df.empty:
                name_map = dict(zip(market_df['market'], market_df['korean_name']))

            records = []
            for item in data:
                records.append({
                    'market': item['market'],
                    'symbol': item['market'].replace('KRW-', ''),
                    'name': name_map.get(item['market'], item['market']),
                    'price': item['trade_price'],
                    'change_rate': round(item.get('signed_change_rate', 0) * 100, 2),
                    'change_price': item.get('signed_change_price', 0),
                    'volume_24h': item.get('acc_trade_volume_24h', 0),
                    'trade_value_24h': item.get('acc_trade_price_24h', 0),
                    'high_price': item.get('high_price', 0),
                    'low_price': item.get('low_price', 0),
                    'prev_closing_price': item.get('prev_closing_price', 0),
                })

            df = pd.DataFrame(records)
            self._cache.set(cache_key, df)
            return df

        except Exception as e:
            print(f"업비트 시세 조회 오류: {e}")
            return pd.DataFrame()

    def get_daily_candles(self, market: str, count: int = 30) -> pd.DataFrame:
        """일봉 캔들 조회."""
        cache_key = f"candle_{market}_{count}"
        cached = self._candle_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/candles/days",
                params={"market": market, "count": count},
                timeout=10
            )
            data = resp.json()

            records = []
            for item in data:
                records.append({
                    'date': item['candle_date_time_kst'][:10],
                    'open': item['opening_price'],
                    'high': item['high_price'],
                    'low': item['low_price'],
                    'close': item['trade_price'],
                    'volume': item['candle_acc_trade_volume'],
                })

            df = pd.DataFrame(records)
            if not df.empty:
                df = df.sort_values('date').reset_index(drop=True)

            self._candle_cache.set(cache_key, df)
            return df

        except Exception as e:
            print(f"업비트 캔들 조회 오류: {e}")
            return pd.DataFrame()

    def get_top_coins_by_volume(self, top_n: int = 30) -> pd.DataFrame:
        """거래대금 기준 상위 코인."""
        tickers = self.get_tickers()
        if tickers.empty:
            return pd.DataFrame()

        tickers = tickers.sort_values('trade_value_24h', ascending=False).head(top_n)
        tickers['rank'] = range(1, len(tickers) + 1)
        tickers['trade_value_억'] = (tickers['trade_value_24h'] / 1e8).round(0).astype(int)

        return tickers[['rank', 'market', 'symbol', 'name', 'price', 'change_rate',
                        'volume_24h', 'trade_value_억', 'high_price', 'low_price']].copy()


class BinanceScraper:
    """바이낸스 공개 API 스크래퍼."""

    BASE_URL = "https://api.binance.com/api/v3"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self._cache = _SimpleCache(ttl_seconds=60)
        self._candle_cache = _SimpleCache(ttl_seconds=300)

    def get_24hr_stats(self) -> pd.DataFrame:
        """24시간 전체 티커 통계 (USDT 마켓)."""
        cached = self._cache.get("24hr_stats")
        if cached is not None:
            return cached

        try:
            resp = self.session.get(f"{self.BASE_URL}/ticker/24hr", timeout=10)
            data = resp.json()

            records = []
            for item in data:
                symbol = item['symbol']
                if not symbol.endswith('USDT'):
                    continue
                # 레버리지/특수 토큰 제외
                base = symbol.replace('USDT', '')
                if any(x in base for x in ['UP', 'DOWN', 'BULL', 'BEAR']):
                    continue

                records.append({
                    'symbol': symbol,
                    'base': base,
                    'name': COIN_NAMES_KR.get(base, base),
                    'price': float(item['lastPrice']),
                    'change_rate': float(item['priceChangePercent']),
                    'volume_24h': float(item['volume']),
                    'quote_volume_24h': float(item['quoteVolume']),
                    'high_price': float(item['highPrice']),
                    'low_price': float(item['lowPrice']),
                })

            df = pd.DataFrame(records)
            self._cache.set("24hr_stats", df)
            return df

        except Exception as e:
            print(f"바이낸스 24hr 조회 오류: {e}")
            return pd.DataFrame()

    def get_daily_candles(self, symbol: str, limit: int = 30) -> pd.DataFrame:
        """일봉 캔들 조회."""
        cache_key = f"candle_{symbol}_{limit}"
        cached = self._candle_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/klines",
                params={"symbol": symbol, "interval": "1d", "limit": limit},
                timeout=10
            )
            data = resp.json()

            records = []
            for item in data:
                records.append({
                    'date': datetime.fromtimestamp(item[0] / 1000).strftime('%Y-%m-%d'),
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5]),
                })

            df = pd.DataFrame(records)
            self._candle_cache.set(cache_key, df)
            return df

        except Exception as e:
            print(f"바이낸스 캔들 조회 오류: {e}")
            return pd.DataFrame()

    def get_top_coins_by_volume(self, top_n: int = 30) -> pd.DataFrame:
        """거래대금 상위 코인 (USDT 기준)."""
        stats = self.get_24hr_stats()
        if stats.empty:
            return pd.DataFrame()

        stats = stats.sort_values('quote_volume_24h', ascending=False).head(top_n)
        stats['rank'] = range(1, len(stats) + 1)
        stats['quote_volume_만달러'] = (stats['quote_volume_24h'] / 1e4).round(0).astype(int)

        return stats[['rank', 'symbol', 'base', 'name', 'price', 'change_rate',
                      'volume_24h', 'quote_volume_만달러', 'high_price', 'low_price']].copy()


class CryptoScraper:
    """통합 암호화폐 스크래퍼."""

    def __init__(self):
        self.upbit = UpbitScraper()
        self.binance = BinanceScraper()

    def get_top_coins(self, exchange: str = "upbit", top_n: int = 30) -> pd.DataFrame:
        """거래대금 상위 코인."""
        if exchange == "upbit":
            return self.upbit.get_top_coins_by_volume(top_n)
        else:
            return self.binance.get_top_coins_by_volume(top_n)

    def get_movers(self, exchange: str = "upbit", top_n: int = 10) -> dict:
        """급등/급락 코인."""
        if exchange == "upbit":
            tickers = self.upbit.get_tickers()
        else:
            tickers = self.binance.get_24hr_stats()

        if tickers.empty:
            return {'gainers': pd.DataFrame(), 'losers': pd.DataFrame()}

        sorted_df = tickers.sort_values('change_rate', ascending=False)

        gainers = sorted_df.head(top_n).copy()
        gainers['rank'] = range(1, len(gainers) + 1)

        losers = sorted_df.tail(top_n).sort_values('change_rate').copy()
        losers['rank'] = range(1, len(losers) + 1)

        return {'gainers': gainers, 'losers': losers}

    def get_candles(self, market: str, exchange: str = "upbit", count: int = 30) -> pd.DataFrame:
        """일봉 캔들 조회."""
        if exchange == "upbit":
            return self.upbit.get_daily_candles(market, count)
        else:
            return self.binance.get_daily_candles(market, count)


# CLI 테스트
if __name__ == "__main__":
    scraper = CryptoScraper()

    print("\n=== 업비트 거래대금 TOP 10 ===")
    top = scraper.get_top_coins("upbit", 10)
    if not top.empty:
        for _, row in top.iterrows():
            print(f"{row['rank']:2}. {row['name']:10} ({row['symbol']}) "
                  f"| {row['price']:>15,}원 | {row['change_rate']:+.2f}% | {row['trade_value_억']:,}억")

    print("\n=== 바이낸스 거래대금 TOP 10 ===")
    top_b = scraper.get_top_coins("binance", 10)
    if not top_b.empty:
        for _, row in top_b.iterrows():
            print(f"{row['rank']:2}. {row['name']:10} ({row['base']}) "
                  f"| ${row['price']:>10,.2f} | {row['change_rate']:+.2f}%")
