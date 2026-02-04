"""암호화폐 종합 분석 및 추천."""

import pandas as pd
import numpy as np
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

    def _calculate_macd(self, closes: pd.Series) -> dict:
        """MACD 계산 (12-EMA, 26-EMA, 9-Signal)."""
        if len(closes) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'cross': 'none', 'macd_score': 0, 'signals': []}

        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]

        score = 0
        signals = []

        # 크로스 판별
        if prev_macd <= prev_signal and current_macd > current_signal:
            cross = 'golden'
            score = 15
            signals.append("📈MACD골든크로스")
        elif prev_macd >= prev_signal and current_macd < current_signal:
            cross = 'dead'
            score = -5
            signals.append("📉MACD데드크로스")
        elif current_macd > current_signal:
            cross = 'bullish'
            score = 5
        else:
            cross = 'bearish'
            score = -2

        return {
            'macd': round(current_macd, 4),
            'signal': round(current_signal, 4),
            'histogram': round(histogram.iloc[-1], 4),
            'cross': cross,
            'macd_score': score,
            'signals': signals,
        }

    def _analyze_bollinger(self, candles_df: pd.DataFrame) -> dict:
        """볼린저 밴드 분석 (20-SMA ± 2σ)."""
        if candles_df.empty or len(candles_df) < 20:
            return {'bb_score': 0, 'bb_position': 'unknown', 'signals': []}

        closes = candles_df['close']
        sma20 = closes.rolling(20).mean().iloc[-1]
        std20 = closes.rolling(20).std().iloc[-1]

        upper_band = sma20 + 2 * std20
        lower_band = sma20 - 2 * std20
        current_price = closes.iloc[-1]

        score = 0
        signals = []

        # 밴드 폭 (스퀴즈 감지)
        band_width = (upper_band - lower_band) / sma20 * 100 if sma20 > 0 else 0

        if current_price <= lower_band:
            score = 10
            position = 'oversold'
            signals.append("💎볼린저하단(과매도)")
        elif current_price >= upper_band:
            score = -5
            position = 'overbought'
            signals.append("⚠️볼린저상단(과매수)")
        elif band_width < 5:
            score = 5
            position = 'squeeze'
            signals.append("🔧볼린저스퀴즈(돌파임박)")
        else:
            position = 'normal'

        return {
            'bb_score': score,
            'bb_position': position,
            'upper_band': round(upper_band, 4),
            'lower_band': round(lower_band, 4),
            'sma20': round(sma20, 4),
            'band_width': round(band_width, 2),
            'signals': signals,
        }

    def _get_fear_greed_score(self) -> dict:
        """공포탐욕지수 기반 점수."""
        fg = self.scraper.get_fear_greed_index()
        value = fg['value']

        score = 0
        signals = []

        if value < 25:
            score = 15
            signals.append(f"💎극도의공포({value})")
        elif value < 45:
            score = 5
            signals.append(f"😨공포({value})")
        elif value > 75:
            score = -10
            signals.append(f"⚠️극도의탐욕({value})")
        elif value > 55:
            score = -5
            signals.append(f"🔥탐욕({value})")

        return {
            'fg_value': value,
            'fg_classification': fg['classification'],
            'fg_score': score,
            'signals': signals,
        }

    def _get_kimchi_premium_score(self) -> dict:
        """김치프리미엄 기반 점수."""
        kp = self.scraper.get_kimchi_premium()
        avg_premium = kp.get('avg_premium', 0)

        score = 0
        signals = []

        if avg_premium > 5:
            score = -5
            signals.append(f"⚠️김프과열({avg_premium:+.1f}%)")
        elif avg_premium > 3:
            score = -2
        elif avg_premium < -2:
            score = 5
            signals.append(f"💎역김프({avg_premium:+.1f}%)")
        elif avg_premium < 0:
            score = 2

        return {
            'kimchi_premium': avg_premium,
            'premiums': kp.get('premiums', {}),
            'kp_score': score,
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
        """종합 추천 코인 (검증된 금융 지표 기반).

        점수 산정 (최대 ~130점):
        - 모멘텀 (24h+5d): 최대 20점
        - 거래량 급증: 최대 15점
        - 기술적 (MA+RSI): 최대 20점
        - 거래대금 순위: 최대 10점
        - 추세 지속성: 최대 10점
        - MACD (신규): 최대 15점
        - 볼린저밴드 (신규): 최대 15점
        - 공포탐욕지수 (신규): 최대 15점
        - 김치프리미엄 (신규, 업비트만): 최대 10점
        """
        top_coins = self.scraper.get_top_coins(exchange, 50)
        if top_coins.empty:
            return pd.DataFrame()

        # 시장 전체 지표 (한 번만 조회)
        fg_data = self._get_fear_greed_score()
        kp_data = self._get_kimchi_premium_score() if exchange == "upbit" else {'kp_score': 0, 'kimchi_premium': 0, 'signals': []}

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

            # 기존 분석
            tech = self._analyze_technical(candles)
            momentum = self._analyze_momentum(row['change_rate'], candles)
            volume = self._analyze_volume(candles)

            # 신규 분석
            macd_data = self._calculate_macd(candles['close']) if not candles.empty and len(candles) >= 26 else {'macd_score': 0, 'cross': 'none', 'signals': []}
            bb_data = self._analyze_bollinger(candles)

            # 거래대금 순위 보너스 (최대 10점)
            rank_score = 0
            rank_val = int(row['rank'])
            if rank_val <= 5:
                rank_score = 10
            elif rank_val <= 10:
                rank_score = 7
            elif rank_val <= 20:
                rank_score = 3

            # 추세 지속성 보너스 (최대 10점)
            trend_score = 0
            trend_signals = []
            if not candles.empty and len(candles) >= 3:
                last3 = candles.tail(3)
                green_count = sum(1 for _, c in last3.iterrows() if c['close'] > c['open'])
                if green_count >= 3:
                    trend_score = 10
                    trend_signals.append("⭐3연속양봉")
                elif green_count >= 2:
                    trend_score = 5
                    trend_signals.append("📈2연속양봉")

            # 총점
            total = (
                min(20, tech['technical_score']) +
                min(20, momentum['momentum_score']) +
                min(15, volume['volume_score']) +
                rank_score +
                trend_score +
                macd_data['macd_score'] +
                bb_data['bb_score'] +
                fg_data['fg_score'] +
                kp_data['kp_score']
            )

            all_signals = (tech['signals'] + momentum['signals'] + volume['signals'] +
                          macd_data['signals'] + bb_data['signals'] + trend_signals)
            # 시장 전체 신호는 1위에만 표시
            if i == 0:
                all_signals.extend(fg_data['signals'])
                if kp_data['signals']:
                    all_signals.extend(kp_data['signals'])

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
                    'macd_score': macd_data['macd_score'],
                    'bb_score': bb_data['bb_score'],
                    'ma5': tech['ma5'],
                    'ma20': tech['ma20'],
                    'rsi': tech['rsi'],
                    'macd_cross': macd_data.get('cross', 'none'),
                    'bb_position': bb_data.get('bb_position', 'unknown'),
                    'vol_change_pct': volume.get('vol_change_pct', 0),
                    'signals': ', '.join(all_signals) if all_signals else '',
                })

        result = pd.DataFrame(records)
        if not result.empty:
            result = result.sort_values('score', ascending=False).head(top_n)
            result['rank'] = range(1, len(result) + 1)
            result = result[['rank', 'market', 'symbol', 'name', 'price', 'change_24h',
                           'score', 'momentum_score', 'volume_score', 'technical_score',
                           'macd_score', 'bb_score',
                           'rsi', 'macd_cross', 'bb_position', 'vol_change_pct', 'signals']]

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
        macd_data = self._calculate_macd(candles['close']) if len(candles) >= 26 else {'macd': 0, 'signal': 0, 'histogram': 0, 'cross': 'none', 'macd_score': 0, 'signals': []}
        bb_data = self._analyze_bollinger(candles)

        # 이동평균선 + 볼린저밴드를 캔들 데이터에 추가
        candles = candles.copy()
        candles['ma5'] = candles['close'].rolling(5).mean()
        candles['ma20'] = candles['close'].rolling(20).mean()
        candles['bb_upper'] = candles['close'].rolling(20).mean() + 2 * candles['close'].rolling(20).std()
        candles['bb_lower'] = candles['close'].rolling(20).mean() - 2 * candles['close'].rolling(20).std()

        # MACD 데이터 추가
        if len(candles) >= 26:
            ema12 = candles['close'].ewm(span=12, adjust=False).mean()
            ema26 = candles['close'].ewm(span=26, adjust=False).mean()
            candles['macd'] = ema12 - ema26
            candles['macd_signal'] = candles['macd'].ewm(span=9, adjust=False).mean()
            candles['macd_hist'] = candles['macd'] - candles['macd_signal']

        # 코인명
        if exchange == "upbit":
            markets = self.scraper.upbit.get_krw_markets()
            name_map = dict(zip(markets['market'], markets['korean_name'])) if not markets.empty else {}
            name = name_map.get(market, market)
        else:
            base = market.replace('USDT', '')
            from src.scrapers.crypto import COIN_NAMES_KR
            name = COIN_NAMES_KR.get(base, base)

        all_signals = tech['signals'] + macd_data['signals'] + bb_data['signals']

        return {
            'market': market,
            'name': name,
            'price': candles['close'].iloc[-1] if not candles.empty else 0,
            'ma5': tech['ma5'],
            'ma20': tech['ma20'],
            'rsi': tech['rsi'],
            'trend': tech['trend'],
            'technical_score': tech['technical_score'],
            'macd': macd_data['macd'],
            'macd_signal': macd_data['signal'],
            'macd_cross': macd_data['cross'],
            'bb_upper': bb_data.get('upper_band', 0),
            'bb_lower': bb_data.get('lower_band', 0),
            'bb_position': bb_data.get('bb_position', 'unknown'),
            'signals': all_signals,
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
