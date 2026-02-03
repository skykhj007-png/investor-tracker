"""암호화폐 종합 분석 및 추천."""

import pandas as pd
import time
from dataclasses import dataclass, field
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.crypto import CryptoScraper


@dataclass
class CryptoSignal:
    """개별 코인 분석 신호."""
    market: str
    name: str
    price: float = 0
    change_24h: float = 0
    volume_24h: float = 0
    ma5: float = 0
    ma20: float = 0
    rsi: float = 50
    momentum_score: float = 0
    volume_score: float = 0
    technical_score: float = 0
    total_score: float = 0
    signals: list = field(default_factory=list)


class CryptoRecommender:
    """암호화폐 종합 분석 및 추천."""

    def __init__(self):
        self.scraper = CryptoScraper()

    def _calculate_rsi(self, closes: pd.Series, period: int = 14) -> float:
        """RSI 계산 (Wilder 방식)."""
        if len(closes) < period + 1:
            return 50.0

        deltas = closes.diff().dropna()
        gains = deltas.clip(lower=0)
        losses = (-deltas).clip(lower=0)

        avg_gain = gains.iloc[:period].mean()
        avg_loss = losses.iloc[:period].mean()

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains.iloc[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses.iloc[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def _analyze_technical(self, candles_df: pd.DataFrame) -> dict:
        """기술적 분석 (MA + RSI)."""
        if candles_df.empty or len(candles_df) < 5:
            return {'ma5': 0, 'ma20': 0, 'rsi': 50, 'trend': 'unknown',
                    'technical_score': 0, 'signals': []}

        closes = candles_df['close']
        current_price = closes.iloc[-1]

        ma5 = closes.tail(5).mean()
        ma20 = closes.tail(20).mean() if len(closes) >= 20 else closes.mean()
        rsi = self._calculate_rsi(closes)

        score = 0
        signals = []

        # MA 추세 분석
        if current_price > ma5 > ma20:
            score += 15
            trend = 'strong_up'
            signals.append("📈강한상승추세")
        elif current_price > ma5:
            score += 10
            trend = 'up'
            signals.append("📈상승추세")
        elif current_price > ma20:
            score += 5
            trend = 'mild_up'
        elif current_price < ma5 < ma20:
            score -= 10
            trend = 'strong_down'
            signals.append("📉하락추세")
        else:
            trend = 'neutral'

        # RSI 분석
        if rsi > 70:
            score -= 5
            signals.append(f"⚠️과매수(RSI:{rsi:.0f})")
        elif 50 <= rsi <= 70:
            score += 10
            signals.append(f"📈RSI강세({rsi:.0f})")
        elif 30 <= rsi < 50:
            score += 5
        elif rsi < 30:
            score += 15
            signals.append(f"💎과매도반등(RSI:{rsi:.0f})")

        return {
            'ma5': round(ma5, 2),
            'ma20': round(ma20, 2),
            'rsi': rsi,
            'trend': trend,
            'technical_score': score,
            'signals': signals,
        }

    def _analyze_momentum(self, change_24h: float, candles_df: pd.DataFrame) -> dict:
        """모멘텀 분석."""
        score = 0
        signals = []

        # 24시간 변화율
        if change_24h > 10:
            score += 15
            signals.append(f"🚀24h급등({change_24h:+.1f}%)")
        elif change_24h > 5:
            score += 10
            signals.append(f"📈24h상승({change_24h:+.1f}%)")
        elif change_24h > 2:
            score += 5
        elif change_24h < -10:
            score -= 10
            signals.append(f"📉24h급락({change_24h:+.1f}%)")
        elif change_24h < -5:
            score -= 5

        # 5일 수익률
        if not candles_df.empty and len(candles_df) >= 5:
            price_5d = candles_df['close'].iloc[-5]
            current = candles_df['close'].iloc[-1]
            if price_5d > 0:
                change_5d = ((current - price_5d) / price_5d) * 100
                if change_5d > 15:
                    score += 10
                    signals.append(f"🔥5일+{change_5d:.0f}%")
                elif change_5d > 5:
                    score += 5

        return {
            'momentum_score': score,
            'signals': signals,
        }

    def _analyze_volume(self, candles_df: pd.DataFrame) -> dict:
        """거래량 급증 분석."""
        if candles_df.empty or len(candles_df) < 7:
            return {'volume_score': 0, 'vol_change_pct': 0, 'signals': []}

        recent_vol = candles_df['volume'].tail(1).values[0]
        avg_vol = candles_df['volume'].iloc[-8:-1].mean()

        if avg_vol <= 0:
            return {'volume_score': 0, 'vol_change_pct': 0, 'signals': []}

        vol_change = ((recent_vol - avg_vol) / avg_vol) * 100

        score = 0
        signals = []

        if vol_change > 200:
            score = 20
            signals.append(f"🔥거래량폭증({vol_change:+.0f}%)")
        elif vol_change > 100:
            score = 15
            signals.append(f"📊거래량급증({vol_change:+.0f}%)")
        elif vol_change > 50:
            score = 10
            signals.append(f"📈거래량증가({vol_change:+.0f}%)")
        elif vol_change > 20:
            score = 5

        return {
            'volume_score': score,
            'vol_change_pct': round(vol_change, 1),
            'signals': signals,
        }

    def get_recommendations(self, exchange: str = "upbit", top_n: int = 20) -> pd.DataFrame:
        """종합 추천 코인.

        점수 산정 (최대 ~100점):
        - 모멘텀 (24h+5d): 최대 25점
        - 거래량 급증: 최대 20점
        - 기술적 (MA+RSI): 최대 25점
        - 거래대금 순위: 최대 15점
        - 추세 지속성: 최대 15점
        """
        top_coins = self.scraper.get_top_coins(exchange, 50)
        if top_coins.empty:
            return pd.DataFrame()

        # 분석 대상 (상위 30개만 - 속도)
        analyze_count = min(30, len(top_coins))
        records = []

        for i in range(analyze_count):
            row = top_coins.iloc[i]

            if exchange == "upbit":
                market_id = row['market']
                symbol = row['symbol']
            else:
                market_id = row['symbol']
                symbol = row['base']

            # 캔들 데이터 조회
            candles = self.scraper.get_candles(market_id, exchange, 30)
            time.sleep(0.1)  # rate limit

            # 분석
            tech = self._analyze_technical(candles)
            momentum = self._analyze_momentum(row['change_rate'], candles)
            volume = self._analyze_volume(candles)

            # 거래대금 순위 보너스
            rank_score = 0
            rank_val = int(row['rank'])
            if rank_val <= 5:
                rank_score = 15
            elif rank_val <= 10:
                rank_score = 10
            elif rank_val <= 20:
                rank_score = 5

            # 추세 지속성 보너스
            trend_score = 0
            trend_signals = []
            if not candles.empty and len(candles) >= 3:
                last3 = candles.tail(3)
                green_count = sum(1 for _, c in last3.iterrows() if c['close'] > c['open'])
                if green_count >= 3:
                    trend_score = 15
                    trend_signals.append("⭐3연속양봉")
                elif green_count >= 2:
                    trend_score = 10
                    trend_signals.append("📈2연속양봉")

            # 총점
            total = (tech['technical_score'] + momentum['momentum_score'] +
                     volume['volume_score'] + rank_score + trend_score)

            all_signals = tech['signals'] + momentum['signals'] + volume['signals'] + trend_signals

            if total > 0:
                records.append({
                    'market': market_id,
                    'symbol': symbol,
                    'name': row['name'],
                    'price': row['price'],
                    'change_24h': row['change_rate'],
                    'score': round(total, 1),
                    'momentum_score': momentum['momentum_score'],
                    'volume_score': volume['volume_score'],
                    'technical_score': tech['technical_score'],
                    'ma5': tech['ma5'],
                    'ma20': tech['ma20'],
                    'rsi': tech['rsi'],
                    'vol_change_pct': volume.get('vol_change_pct', 0),
                    'signals': ', '.join(all_signals) if all_signals else '',
                })

        result = pd.DataFrame(records)
        if not result.empty:
            result = result.sort_values('score', ascending=False).head(top_n)
            result['rank'] = range(1, len(result) + 1)
            result = result[['rank', 'market', 'symbol', 'name', 'price', 'change_24h',
                           'score', 'momentum_score', 'volume_score', 'technical_score',
                           'rsi', 'vol_change_pct', 'signals']]

        return result

    def get_volume_surge_coins(self, exchange: str = "upbit", top_n: int = 15) -> pd.DataFrame:
        """거래량 급증 코인."""
        top_coins = self.scraper.get_top_coins(exchange, 40)
        if top_coins.empty:
            return pd.DataFrame()

        records = []
        for i in range(min(30, len(top_coins))):
            row = top_coins.iloc[i]

            if exchange == "upbit":
                market_id = row['market']
                symbol = row['symbol']
            else:
                market_id = row['symbol']
                symbol = row['base']

            candles = self.scraper.get_candles(market_id, exchange, 10)
            time.sleep(0.1)

            vol_data = self._analyze_volume(candles)
            if vol_data['volume_score'] > 0:
                records.append({
                    'market': market_id,
                    'symbol': symbol,
                    'name': row['name'],
                    'price': row['price'],
                    'change_24h': row['change_rate'],
                    'vol_change_pct': vol_data['vol_change_pct'],
                    'volume_score': vol_data['volume_score'],
                    'signals': ', '.join(vol_data['signals']),
                })

        result = pd.DataFrame(records)
        if not result.empty:
            result = result.sort_values('volume_score', ascending=False).head(top_n)
            result['rank'] = range(1, len(result) + 1)

        return result

    def get_technical_analysis(self, market: str, exchange: str = "upbit") -> dict:
        """개별 코인 기술적 분석 상세."""
        candles = self.scraper.get_candles(market, exchange, 30)

        if candles.empty:
            return {'market': market, 'error': '데이터 없음'}

        tech = self._analyze_technical(candles)

        # 이동평균선을 캔들 데이터에 추가
        candles = candles.copy()
        candles['ma5'] = candles['close'].rolling(5).mean()
        candles['ma20'] = candles['close'].rolling(20).mean()

        # 코인명
        if exchange == "upbit":
            markets = self.scraper.upbit.get_krw_markets()
            name_map = dict(zip(markets['market'], markets['korean_name'])) if not markets.empty else {}
            name = name_map.get(market, market)
        else:
            base = market.replace('USDT', '')
            from src.scrapers.crypto import COIN_NAMES_KR
            name = COIN_NAMES_KR.get(base, base)

        return {
            'market': market,
            'name': name,
            'price': candles['close'].iloc[-1] if not candles.empty else 0,
            'ma5': tech['ma5'],
            'ma20': tech['ma20'],
            'rsi': tech['rsi'],
            'trend': tech['trend'],
            'technical_score': tech['technical_score'],
            'signals': tech['signals'],
            'candles': candles,
        }


# CLI 테스트
if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    recommender = CryptoRecommender()

    print("\n" + "="*60)
    print("[암호화폐 종합 추천]")
    print("="*60)

    print("\n[업비트 종합 추천 TOP 10]")
    print("-"*60)
    recs = recommender.get_recommendations("upbit", 10)
    if not recs.empty:
        for _, row in recs.iterrows():
            print(f"{row['rank']:2}. {row['name']:10} | {row['price']:>15,} "
                  f"| {row['change_24h']:+.1f}% | 점수:{row['score']:5.1f} "
                  f"| RSI:{row['rsi']:.0f}")
    else:
        print("데이터 없음")
