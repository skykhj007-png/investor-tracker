"""Korean stock recommendation analyzer based on multiple signals."""

import time
import pandas as pd
import numpy as np
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.korean_stocks import KoreanStocksScraper

try:
    from pykrx import stock as krx
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False


def get_recent_trading_date() -> str:
    """Get most recent trading date (skip weekends)."""
    today = datetime.now()
    if today.hour < 18:
        today = today - timedelta(days=1)
    while today.weekday() >= 5:
        today = today - timedelta(days=1)
    return today.strftime("%Y%m%d")


@dataclass
class StockSignal:
    """Individual stock signal data."""
    symbol: str
    name: str
    foreign_rank: Optional[int] = None
    foreign_amount: float = 0
    inst_rank: Optional[int] = None
    inst_amount: float = 0
    short_ratio: float = 0
    score: float = 0
    signals: list = field(default_factory=list)
    momentum_score: float = 0
    volume_score: float = 0
    amount_score: float = 0
    consecutive_days: int = 0
    market_cap: float = 0
    per: float = 0
    pbr: float = 0
    rsi: float = 50


class KoreanStockRecommender:
    """종목 추천 분석기 - 외국인/기관/공매도/모멘텀/거래량/펀더멘탈/기술적 종합 분석."""

    def __init__(self):
        self.scraper = KoreanStocksScraper()

    def _find_swing_points(self, ohlcv: pd.DataFrame, window: int = 5) -> dict:
        """스윙 포인트 탐색 (로컬 최저/최고점)."""
        swing_highs = []
        swing_lows = []
        if ohlcv.empty or len(ohlcv) < window * 2 + 1:
            return {'swing_highs': swing_highs, 'swing_lows': swing_lows}
        highs = ohlcv['고가'].values
        lows = ohlcv['저가'].values
        for i in range(window, len(ohlcv) - window):
            if highs[i] == max(highs[i - window:i + window + 1]):
                swing_highs.append(float(highs[i]))
            if lows[i] == min(lows[i - window:i + window + 1]):
                swing_lows.append(float(lows[i]))
        return {'swing_highs': sorted(swing_highs), 'swing_lows': sorted(swing_lows)}

    @staticmethod
    def _cluster_levels(levels: list, threshold_pct: float = 0.02) -> list:
        """근접 가격 수준 병합 (threshold_pct 이내 → 하나의 클러스터)."""
        if not levels:
            return []
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        for price in sorted_levels[1:]:
            if current_cluster and abs(price - current_cluster[-1]) / current_cluster[-1] <= threshold_pct:
                current_cluster.append(price)
            else:
                avg_price = sum(current_cluster) / len(current_cluster)
                clusters.append({'price': round(avg_price), 'strength': len(current_cluster)})
                current_cluster = [price]
        if current_cluster:
            avg_price = sum(current_cluster) / len(current_cluster)
            clusters.append({'price': round(avg_price), 'strength': len(current_cluster)})
        return sorted(clusters, key=lambda x: x['strength'], reverse=True)

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

    def _calculate_macd(self, closes: pd.Series) -> dict:
        """MACD 계산 (12-EMA, 26-EMA, 9-Signal)."""
        if len(closes) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'cross': 'none'}

        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]

        # 크로스 판별
        if prev_macd <= prev_signal and current_macd > current_signal:
            cross = 'golden'  # 골든크로스
        elif prev_macd >= prev_signal and current_macd < current_signal:
            cross = 'dead'  # 데드크로스
        elif current_macd > current_signal:
            cross = 'bullish'
        else:
            cross = 'bearish'

        return {
            'macd': round(current_macd, 2),
            'signal': round(current_signal, 2),
            'histogram': round(histogram.iloc[-1], 2),
            'cross': cross,
        }

    def _get_fundamental_score(self, symbol: str, fundamentals_df: pd.DataFrame) -> dict:
        """PER/PBR 기반 밸류에이션 점수."""
        if fundamentals_df.empty or symbol not in fundamentals_df['symbol'].values:
            return {'fundamental_score': 0, 'per': 0, 'pbr': 0, 'signals': []}

        row = fundamentals_df[fundamentals_df['symbol'] == symbol].iloc[0]
        per = row.get('per', 0) or 0
        pbr = row.get('pbr', 0) or 0

        score = 0
        signals = []

        # PER 분석
        if 0 < per <= 10:
            score += 8
            signals.append(f"💎저PER({per:.1f})")
        elif 0 < per <= 15:
            score += 5
        elif per > 50:
            score -= 3
            signals.append(f"⚠️고PER({per:.0f})")

        # PBR 분석
        if 0 < pbr <= 1.0:
            score += 7
            signals.append(f"💎저PBR({pbr:.2f})")
        elif 0 < pbr <= 1.5:
            score += 3
        elif pbr > 5.0:
            score -= 2
            signals.append(f"⚠️고PBR({pbr:.1f})")

        return {
            'fundamental_score': score,
            'per': per,
            'pbr': pbr,
            'signals': signals,
        }

    def _get_technical_score(self, symbol: str) -> dict:
        """RSI + MACD 기술적 점수."""
        if not PYKRX_AVAILABLE:
            return {'rsi': 50, 'rsi_score': 0, 'macd_score': 0, 'macd_cross': 'none', 'signals': []}

        try:
            ohlcv = self.scraper.get_ohlcv(symbol, 60)
            if ohlcv.empty or len(ohlcv) < 15:
                return {'rsi': 50, 'rsi_score': 0, 'macd_score': 0, 'macd_cross': 'none', 'signals': []}

            closes = ohlcv['종가']
            rsi = self._calculate_rsi(closes)
            macd_data = self._calculate_macd(closes)

            score_rsi = 0
            score_macd = 0
            signals = []

            # RSI 점수 (최대 10점)
            if rsi < 30:
                score_rsi = 10
                signals.append(f"💎과매도(RSI:{rsi:.0f})")
            elif 50 <= rsi <= 70:
                score_rsi = 5
                signals.append(f"📈RSI강세({rsi:.0f})")
            elif rsi > 70:
                score_rsi = -5
                signals.append(f"⚠️과매수(RSI:{rsi:.0f})")
            elif 30 <= rsi < 50:
                score_rsi = 3

            # MACD 점수 (최대 10점)
            if macd_data['cross'] == 'golden':
                score_macd = 10
                signals.append("📈MACD골든크로스")
            elif macd_data['cross'] == 'bullish':
                score_macd = 5
            elif macd_data['cross'] == 'dead':
                score_macd = -5
                signals.append("📉MACD데드크로스")
            elif macd_data['cross'] == 'bearish':
                score_macd = -2

            return {
                'rsi': rsi,
                'rsi_score': score_rsi,
                'macd_score': score_macd,
                'macd_cross': macd_data['cross'],
                'signals': signals,
            }

        except Exception:
            return {'rsi': 50, 'rsi_score': 0, 'macd_score': 0, 'macd_cross': 'none', 'signals': []}

    def _get_price_momentum(self, symbol: str) -> dict:
        """가격 모멘텀 분석 (5일/20일 이동평균 기반)."""
        if not PYKRX_AVAILABLE:
            return {'momentum_score': 0, 'price_change_5d': 0, 'price_change_20d': 0, 'trend': 'unknown'}

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")
            start_date = (today_dt - timedelta(days=40)).strftime("%Y%m%d")

            ohlcv = krx.get_market_ohlcv_by_date(start_date, trd_date, symbol)
            if ohlcv.empty or len(ohlcv) < 5:
                return {'momentum_score': 0, 'price_change_5d': 0, 'price_change_20d': 0, 'trend': 'unknown'}

            closes = ohlcv['종가']
            current_price = closes.iloc[-1]

            # 5일 이동평균
            ma5 = closes.tail(5).mean()
            # 20일 이동평균
            ma20 = closes.tail(20).mean() if len(closes) >= 20 else closes.mean()

            # 5일 수익률
            price_5d_ago = closes.iloc[-5] if len(closes) >= 5 else closes.iloc[0]
            price_change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100

            # 20일 수익률
            price_20d_ago = closes.iloc[-20] if len(closes) >= 20 else closes.iloc[0]
            price_change_20d = ((current_price - price_20d_ago) / price_20d_ago) * 100

            # 모멘텀 점수 계산
            momentum_score = 0

            # 현재가 > 5일선 > 20일선 = 강한 상승 추세
            if current_price > ma5 > ma20:
                momentum_score += 15
                trend = 'strong_up'
            elif current_price > ma5:
                momentum_score += 10
                trend = 'up'
            elif current_price > ma20:
                momentum_score += 5
                trend = 'mild_up'
            elif current_price < ma5 < ma20:
                momentum_score -= 5
                trend = 'down'
            else:
                trend = 'neutral'

            # 5일 수익률 보너스
            if price_change_5d > 5:
                momentum_score += 10
            elif price_change_5d > 2:
                momentum_score += 5
            elif price_change_5d < -5:
                momentum_score -= 5

            return {
                'momentum_score': momentum_score,
                'price_change_5d': round(price_change_5d, 2),
                'price_change_20d': round(price_change_20d, 2),
                'trend': trend,
            }

        except Exception:
            return {'momentum_score': 0, 'price_change_5d': 0, 'price_change_20d': 0, 'trend': 'unknown'}

    def _get_volume_surge(self, symbol: str) -> dict:
        """거래량 급증 분석."""
        if not PYKRX_AVAILABLE:
            return {'volume_score': 0, 'vol_change_pct': 0}

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")
            start_date = (today_dt - timedelta(days=20)).strftime("%Y%m%d")

            ohlcv = krx.get_market_ohlcv_by_date(start_date, trd_date, symbol)
            if ohlcv.empty or len(ohlcv) < 10:
                return {'volume_score': 0, 'vol_change_pct': 0}

            recent_vol = ohlcv['거래량'].tail(5).mean()
            prev_vol = ohlcv['거래량'].iloc[-10:-5].mean()

            if prev_vol <= 0:
                return {'volume_score': 0, 'vol_change_pct': 0}

            vol_change = ((recent_vol - prev_vol) / prev_vol) * 100

            volume_score = 0
            if vol_change > 100:
                volume_score = 15  # 거래량 2배 이상
            elif vol_change > 50:
                volume_score = 10  # 거래량 1.5배 이상
            elif vol_change > 20:
                volume_score = 5   # 거래량 20% 이상 증가

            return {
                'volume_score': volume_score,
                'vol_change_pct': round(vol_change, 1),
            }

        except Exception:
            return {'volume_score': 0, 'vol_change_pct': 0}

    def _calculate_amount_score(self, amount: float, max_amount: float) -> float:
        """매수금액 크기 기반 점수 (0~20점)."""
        if max_amount <= 0 or amount <= 0:
            return 0
        # 최대 매수금액 대비 비율로 점수 산정 (로그 스케일)
        import math
        ratio = amount / max_amount
        return round(min(20, 20 * math.log(1 + ratio * 9) / math.log(10)), 1)

    def _get_consecutive_buying(self, symbol: str, investor_type: str = "외국인") -> int:
        """연속 매수일 수 확인 (최대 5일)."""
        if not PYKRX_AVAILABLE:
            return 0

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")
            start_date = (today_dt - timedelta(days=10)).strftime("%Y%m%d")

            df = krx.get_market_net_purchases_of_equities_by_ticker(
                start_date, trd_date, "KOSPI", investor_type
            )

            if df.empty or symbol not in df.index:
                return 0

            # 일별 데이터 확인은 제한적이므로,
            # 순매수 금액이 양수면 최소 1일 매수로 간주
            net_amount = df.loc[symbol, '순매수거래대금'] if '순매수거래대금' in df.columns else 0
            if net_amount > 0:
                return 1
            return 0

        except Exception:
            return 0

    def _get_market_cap_filter(self, symbol: str) -> dict:
        """시가총액 필터 및 점수."""
        if not PYKRX_AVAILABLE:
            return {'market_cap': 0, 'cap_score': 0, 'cap_label': ''}

        try:
            trd_date = get_recent_trading_date()
            cap_df = krx.get_market_cap_by_ticker(trd_date, market="KOSPI")

            if cap_df.empty or symbol not in cap_df.index:
                return {'market_cap': 0, 'cap_score': 0, 'cap_label': ''}

            market_cap = cap_df.loc[symbol, '시가총액']
            cap_조 = market_cap / 1e12

            # 시가총액 점수 (대형주 가산점, 소형주 감점)
            if cap_조 >= 10:
                cap_score = 10
                cap_label = '대형주'
            elif cap_조 >= 1:
                cap_score = 5
                cap_label = '중형주'
            elif cap_조 >= 0.3:
                cap_score = 0
                cap_label = '소형주'
            else:
                cap_score = -5
                cap_label = '초소형주'

            return {
                'market_cap': market_cap,
                'cap_score': cap_score,
                'cap_label': cap_label,
            }

        except Exception:
            return {'market_cap': 0, 'cap_score': 0, 'cap_label': ''}

    def get_entry_analysis(self, symbol: str, ohlcv: pd.DataFrame = None) -> dict:
        """진입점/손절라인/목표가 종합 분석 (1년 OHLCV + MA + RSI + 볼린저)."""
        try:
            if ohlcv is None:
                ohlcv = self.scraper.get_ohlcv_extended(symbol, years=1)

            if ohlcv.empty or len(ohlcv) < 20:
                return {'error': 'insufficient data'}

            closes = ohlcv['종가']
            highs = ohlcv['고가']
            lows = ohlcv['저가']
            current_price = int(closes.iloc[-1])
            if current_price <= 0:
                return {'error': 'invalid price'}

            # 이동평균
            ma20 = float(closes.tail(20).mean())
            ma60 = float(closes.tail(60).mean()) if len(closes) >= 60 else float(closes.mean())
            ma120 = float(closes.tail(120).mean()) if len(closes) >= 120 else ma60

            # RSI / 볼린저
            rsi = self._calculate_rsi(closes)
            sma20 = closes.rolling(20).mean().iloc[-1]
            std20 = closes.rolling(20).std().iloc[-1]
            bb_upper = float(sma20 + 2 * std20) if std20 > 0 else current_price * 1.05
            bb_lower = float(sma20 - 2 * std20) if std20 > 0 else current_price * 0.95

            # 스윙 포인트
            swings = self._find_swing_points(ohlcv, window=5)

            # 지지선 후보
            support_candidates = list(swings['swing_lows'])
            if bb_lower > 0 and bb_lower < current_price:
                support_candidates.append(bb_lower)
            for ma_val in [ma20, ma60, ma120]:
                if 0 < ma_val < current_price:
                    support_candidates.append(ma_val)
            support_candidates.append(float(lows.min()))

            # 저항선 후보
            resist_candidates = list(swings['swing_highs'])
            if bb_upper > current_price:
                resist_candidates.append(bb_upper)
            resist_candidates.append(float(highs.max()))

            # 현재가 기준 필터링 + 클러스터링
            support_raw = [p for p in support_candidates if p < current_price * 1.01]
            resist_raw = [p for p in resist_candidates if p > current_price * 0.99]
            support_levels = self._cluster_levels(support_raw)
            resistance_levels = self._cluster_levels(resist_raw)

            # 진입점 결정
            if rsi < 30:
                entry_point = current_price
            elif support_levels:
                nearest_sup = max([s['price'] for s in support_levels if s['price'] < current_price],
                                  default=int(current_price * 0.97))
                entry_point = int(nearest_sup * 0.4 + current_price * 0.6)
            else:
                entry_point = int(current_price * 0.98)

            # 손절라인
            supports_below = [s['price'] for s in support_levels if s['price'] < entry_point]
            if supports_below:
                stop_loss = int(max(supports_below) * 0.97)
            else:
                stop_loss = int(entry_point * 0.93)
            max_stop = int(entry_point * 0.90)
            if stop_loss < max_stop:
                stop_loss = max_stop
            stop_loss_pct = round((stop_loss - entry_point) / entry_point * 100, 1)

            # 목표가
            targets = []
            resist_prices = sorted([r['price'] for r in resistance_levels if r['price'] > current_price])
            if resist_prices:
                t1 = resist_prices[0]
                targets.append({'price': int(t1), 'label': '1차 목표',
                                'pct': round((t1 - entry_point) / entry_point * 100, 1)})
            if len(resist_prices) >= 2:
                t2 = resist_prices[1]
                targets.append({'price': int(t2), 'label': '2차 목표',
                                'pct': round((t2 - entry_point) / entry_point * 100, 1)})
            if not targets:
                t1 = current_price * 1.05
                targets.append({'price': int(t1), 'label': '1차 목표',
                                'pct': round((t1 - entry_point) / entry_point * 100, 1)})

            # 위험/보상
            risk = entry_point - stop_loss
            reward = targets[0]['price'] - entry_point if targets else 0
            rr_ratio = round(reward / risk, 2) if risk > 0 else 0
            rr_ratio = min(rr_ratio, 10.0)

            return {
                'symbol': symbol, 'price': current_price,
                'entry_point': entry_point,
                'stop_loss': stop_loss, 'stop_loss_pct': stop_loss_pct,
                'targets': targets, 'risk_reward_ratio': rr_ratio,
                'support_levels': support_levels[:5],
                'resistance_levels': resistance_levels[:5],
                'ma20': int(ma20), 'ma60': int(ma60), 'ma120': int(ma120),
                'rsi': rsi, 'bb_upper': int(bb_upper), 'bb_lower': int(bb_lower),
            }
        except Exception:
            try:
                if ohlcv is not None and not ohlcv.empty:
                    cp = int(ohlcv['종가'].iloc[-1])
                    return {
                        'symbol': symbol, 'price': cp,
                        'entry_point': int(cp * 0.98),
                        'stop_loss': int(cp * 0.93), 'stop_loss_pct': -7.0,
                        'targets': [{'price': int(cp * 1.05), 'label': '1차 목표', 'pct': 5.0}],
                        'risk_reward_ratio': 1.0,
                        'support_levels': [], 'resistance_levels': [],
                        'ma20': 0, 'ma60': 0, 'ma120': 0, 'rsi': 50,
                        'bb_upper': 0, 'bb_lower': 0,
                    }
            except Exception:
                pass
            return {'error': 'analysis failed'}

    def get_recommendations(self, market: str = "KOSPI", top_n: int = 20) -> pd.DataFrame:
        """
        종합 추천 종목 리스트 생성 (검증된 금융 지표 기반).

        점수 산정 기준 (총 ~120점 만점):
        - 외국인 순매수: 순위(0~15) + 금액(0~15) = 최대 30점
        - 기관 순매수: 순위(0~15) + 금액(0~15) = 최대 30점
        - 동반 매수 시너지: +10점
        - 가격 모멘텀 (MA): -5 ~ +15점
        - 거래량 급증: 0 ~ +10점
        - 시가총액: -5 ~ +5점
        - 공매도 비중: -5 ~ +5점
        - PER/PBR 밸류에이션 (신규): -5 ~ +15점
        - RSI (신규): -5 ~ +10점
        - MACD (신규): -5 ~ +10점
        """
        # 데이터 수집
        foreign_df = self.scraper.get_foreign_buying(50)
        inst_df = self.scraper.get_institution_buying(50)
        short_df = self.scraper.get_short_volume(market, 100)

        if foreign_df.empty and inst_df.empty:
            return pd.DataFrame()

        # 펀더멘탈 데이터 일괄 조회
        fundamentals_df = self.scraper.get_fundamentals(market)

        # 최대 매수금액 (금액 점수 정규화용)
        max_foreign_amount = foreign_df['net_amount'].max() if not foreign_df.empty else 1
        max_inst_amount = inst_df['net_amount'].max() if not inst_df.empty else 1

        # 종목별 데이터 통합
        stocks = {}

        for _, row in foreign_df.iterrows():
            symbol = row['symbol']
            if symbol not in stocks:
                stocks[symbol] = StockSignal(symbol=symbol, name=row['name'], signals=[])
            stocks[symbol].foreign_rank = int(row['rank'])
            stocks[symbol].foreign_amount = row['net_amount']

        for _, row in inst_df.iterrows():
            symbol = row['symbol']
            if symbol not in stocks:
                stocks[symbol] = StockSignal(symbol=symbol, name=row['name'], signals=[])
            stocks[symbol].inst_rank = int(row['rank'])
            stocks[symbol].inst_amount = row['net_amount']

        # 공매도 데이터
        short_dict = {}
        if not short_df.empty:
            for _, row in short_df.iterrows():
                short_dict[row['symbol']] = row['short_ratio']

        # 상세 분석 대상 (순위 30위 이내 또는 동반매수)
        priority_symbols = set()
        for symbol, stock in stocks.items():
            fr = stock.foreign_rank or 999
            ir = stock.inst_rank or 999
            if fr <= 30 or ir <= 30 or (stock.foreign_rank and stock.inst_rank):
                priority_symbols.add(symbol)

        # 모멘텀/거래량/기술적 분석 캐시
        momentum_cache = {}
        volume_cache = {}
        cap_cache = {}
        technical_cache = {}
        fundamental_cache = {}

        for symbol in priority_symbols:
            momentum_cache[symbol] = self._get_price_momentum(symbol)
            volume_cache[symbol] = self._get_volume_surge(symbol)
            technical_cache[symbol] = self._get_technical_score(symbol)
            fundamental_cache[symbol] = self._get_fundamental_score(symbol, fundamentals_df)

        # 시총 일괄 조회
        if PYKRX_AVAILABLE:
            try:
                trd_date = get_recent_trading_date()
                cap_df = krx.get_market_cap_by_ticker(trd_date, market=market)
                for symbol in priority_symbols:
                    if symbol in cap_df.index:
                        mc = cap_df.loc[symbol, '시가총액']
                        cap_조 = mc / 1e12
                        if cap_조 >= 10:
                            cap_cache[symbol] = {'market_cap': mc, 'cap_score': 5, 'cap_label': '대형주'}
                        elif cap_조 >= 1:
                            cap_cache[symbol] = {'market_cap': mc, 'cap_score': 3, 'cap_label': '중형주'}
                        elif cap_조 >= 0.3:
                            cap_cache[symbol] = {'market_cap': mc, 'cap_score': 0, 'cap_label': '소형주'}
                        else:
                            cap_cache[symbol] = {'market_cap': mc, 'cap_score': -5, 'cap_label': '초소형주'}
            except Exception:
                pass

        # 점수 계산
        for symbol, stock in stocks.items():
            score = 0
            signals = []

            # === 1. 외국인 순매수 (최대 30점) ===
            if stock.foreign_rank:
                rank_score = max(0, 16 - stock.foreign_rank) if stock.foreign_rank <= 15 else 0
                amount_score = min(15, self._calculate_amount_score(stock.foreign_amount, max_foreign_amount) * 0.75)
                score += rank_score + amount_score

                if stock.foreign_rank <= 5:
                    signals.append(f"🌍외국인 TOP{stock.foreign_rank}")
                elif stock.foreign_rank <= 10:
                    signals.append(f"🌍외국인 {stock.foreign_rank}위")
                elif stock.foreign_rank <= 30:
                    signals.append(f"외국인 {stock.foreign_rank}위")

                amount_억 = int(stock.foreign_amount / 1e8)
                if amount_억 >= 100:
                    signals.append(f"💰외국인{amount_억}억")

            # === 2. 기관 순매수 (최대 30점) ===
            if stock.inst_rank:
                rank_score = max(0, 16 - stock.inst_rank) if stock.inst_rank <= 15 else 0
                amount_score = min(15, self._calculate_amount_score(stock.inst_amount, max_inst_amount) * 0.75)
                score += rank_score + amount_score

                if stock.inst_rank <= 5:
                    signals.append(f"🏛️기관 TOP{stock.inst_rank}")
                elif stock.inst_rank <= 10:
                    signals.append(f"🏛️기관 {stock.inst_rank}위")
                elif stock.inst_rank <= 30:
                    signals.append(f"기관 {stock.inst_rank}위")

                amount_억 = int(stock.inst_amount / 1e8)
                if amount_억 >= 100:
                    signals.append(f"💰기관{amount_억}억")

            # === 3. 동반 매수 시너지 (+10점) ===
            if stock.foreign_rank and stock.inst_rank:
                if stock.foreign_rank <= 30 and stock.inst_rank <= 30:
                    score += 10
                    signals.append("⭐동반매수")

            # === 4. 가격 모멘텀 (-5 ~ +15점) ===
            if symbol in momentum_cache:
                m = momentum_cache[symbol]
                mom_score = min(15, m['momentum_score'])
                score += mom_score
                if m['trend'] == 'strong_up':
                    signals.append(f"📈강한상승({m['price_change_5d']:+.1f}%)")
                elif m['trend'] == 'up':
                    signals.append(f"📈상승추세({m['price_change_5d']:+.1f}%)")
                elif m['trend'] == 'down':
                    signals.append("📉하락추세")

            # === 5. 거래량 급증 (0 ~ +10점) ===
            if symbol in volume_cache:
                v = volume_cache[symbol]
                vol_score = min(10, v['volume_score'])
                score += vol_score
                if v['vol_change_pct'] > 100:
                    signals.append(f"🔥거래량폭증({v['vol_change_pct']:+.0f}%)")
                elif v['vol_change_pct'] > 50:
                    signals.append(f"📊거래량급증({v['vol_change_pct']:+.0f}%)")

            # === 6. 시가총액 (-5 ~ +5점) ===
            if symbol in cap_cache:
                c = cap_cache[symbol]
                score += c['cap_score']
                stock.market_cap = c['market_cap']

            # === 7. 공매도 비중 (-5 ~ +5점) ===
            short_ratio = short_dict.get(symbol, 0)
            stock.short_ratio = short_ratio
            if short_ratio > 0:
                if short_ratio <= 3:
                    score += 5
                    signals.append("✅공매도낮음")
                elif short_ratio >= 25:
                    score -= 5
                    signals.append("⚠️공매도높음")
                elif short_ratio >= 15:
                    score -= 3

            # === 8. PER/PBR 밸류에이션 (-5 ~ +15점, 신규) ===
            if symbol in fundamental_cache:
                f = fundamental_cache[symbol]
                score += f['fundamental_score']
                stock.per = f['per']
                stock.pbr = f['pbr']
                signals.extend(f['signals'])

            # === 9. RSI (-5 ~ +10점, 신규) ===
            if symbol in technical_cache:
                t = technical_cache[symbol]
                score += t['rsi_score']
                stock.rsi = t['rsi']
                # === 10. MACD (-5 ~ +10점, 신규) ===
                score += t['macd_score']
                signals.extend(t['signals'])

            stock.score = score
            stock.signals = signals

        # DataFrame 변환 및 정렬
        records = []
        for symbol, stock in stocks.items():
            if stock.score > 0:
                cap_조 = round(stock.market_cap / 1e12, 1) if stock.market_cap else '-'
                momentum = momentum_cache.get(symbol, {})
                volume = volume_cache.get(symbol, {})

                records.append({
                    'symbol': stock.symbol,
                    'name': stock.name,
                    'score': round(stock.score, 1),
                    'foreign_rank': stock.foreign_rank or '-',
                    'foreign_억': int(stock.foreign_amount / 1e8) if stock.foreign_amount else 0,
                    'inst_rank': stock.inst_rank or '-',
                    'inst_억': int(stock.inst_amount / 1e8) if stock.inst_amount else 0,
                    'short_ratio': round(stock.short_ratio, 1),
                    'per': round(stock.per, 1) if stock.per else '-',
                    'pbr': round(stock.pbr, 2) if stock.pbr else '-',
                    'rsi': round(stock.rsi, 0),
                    'price_change_5d': momentum.get('price_change_5d', 0),
                    'vol_change_pct': volume.get('vol_change_pct', 0),
                    'market_cap_조': cap_조,
                    'signals': ', '.join(stock.signals) if stock.signals else '',
                })

        result = pd.DataFrame(records)
        if not result.empty:
            result = result.sort_values('score', ascending=False).head(top_n)
            result['rank'] = range(1, len(result) + 1)

            # 진입점/손절/목표가 분석 (top_n 종목만)
            entry_points = []
            stop_losses = []
            stop_loss_pcts = []
            target_1s = []
            target_1_pcts = []
            risk_rewards = []
            for _, row in result.iterrows():
                try:
                    analysis = self.get_entry_analysis(row['symbol'])
                    entry_points.append(analysis.get('entry_point', 0))
                    stop_losses.append(analysis.get('stop_loss', 0))
                    stop_loss_pcts.append(analysis.get('stop_loss_pct', 0))
                    t = analysis.get('targets', [])
                    target_1s.append(t[0]['price'] if t else 0)
                    target_1_pcts.append(t[0]['pct'] if t else 0)
                    risk_rewards.append(analysis.get('risk_reward_ratio', 0))
                except Exception:
                    entry_points.append(0)
                    stop_losses.append(0)
                    stop_loss_pcts.append(0)
                    target_1s.append(0)
                    target_1_pcts.append(0)
                    risk_rewards.append(0)
                time.sleep(0.1)

            result['entry_point'] = entry_points
            result['stop_loss'] = stop_losses
            result['stop_loss_pct'] = stop_loss_pcts
            result['target_1'] = target_1s
            result['target_1_pct'] = target_1_pcts
            result['risk_reward'] = risk_rewards

            result = result[['rank', 'symbol', 'name', 'score', 'signals',
                           'foreign_rank', 'foreign_억', 'inst_rank', 'inst_억',
                           'short_ratio', 'per', 'pbr', 'rsi',
                           'entry_point', 'stop_loss', 'stop_loss_pct',
                           'target_1', 'target_1_pct', 'risk_reward',
                           'price_change_5d', 'vol_change_pct', 'market_cap_조']]

        return result

    def get_dual_buying_stocks(self) -> pd.DataFrame:
        """외국인+기관 동반 매수 종목만 추출."""
        recommendations = self.get_recommendations(top_n=50)

        if recommendations.empty:
            return pd.DataFrame()

        dual = recommendations[recommendations['signals'].str.contains('동반매수', na=False)]
        return dual

    def get_contrarian_picks(self, market: str = "KOSPI") -> pd.DataFrame:
        """
        역발상 매수 후보 - 공매도 비중 높지만 외국인/기관이 매수하는 종목.
        """
        foreign_df = self.scraper.get_foreign_buying(50)
        inst_df = self.scraper.get_institution_buying(50)
        short_df = self.scraper.get_short_volume(market, 50)

        if short_df.empty:
            return pd.DataFrame()

        high_short = short_df[short_df['short_ratio'] >= 15].copy()

        if high_short.empty:
            return pd.DataFrame()

        foreign_symbols = set(foreign_df['symbol'].tolist()) if not foreign_df.empty else set()
        inst_symbols = set(inst_df['symbol'].tolist()) if not inst_df.empty else set()
        buying_symbols = foreign_symbols | inst_symbols

        contrarian = high_short[high_short['symbol'].isin(buying_symbols)].copy()

        if contrarian.empty:
            return pd.DataFrame()

        contrarian['외국인매수'] = contrarian['symbol'].apply(
            lambda x: '✓' if x in foreign_symbols else ''
        )
        contrarian['기관매수'] = contrarian['symbol'].apply(
            lambda x: '✓' if x in inst_symbols else ''
        )

        contrarian = contrarian.sort_values('short_ratio', ascending=False)
        contrarian['rank'] = range(1, len(contrarian) + 1)

        return contrarian[['rank', 'symbol', 'name', 'short_ratio', '외국인매수', '기관매수']]

    def get_recommendation_summary(self, market: str = "KOSPI") -> dict:
        """추천 요약 정보."""
        recommendations = self.get_recommendations(market)
        dual = self.get_dual_buying_stocks()
        contrarian = self.get_contrarian_picks(market)

        return {
            'top_picks': recommendations.head(5) if not recommendations.empty else pd.DataFrame(),
            'dual_buying': dual.head(10) if not dual.empty else pd.DataFrame(),
            'contrarian': contrarian.head(5) if not contrarian.empty else pd.DataFrame(),
            'total_analyzed': len(recommendations),
        }

    def get_accumulation_signals(self, market: str = "KOSPI", top_n: int = 20) -> pd.DataFrame:
        """주식 매집 신호 분석."""
        return self.scraper.get_accumulation_signals(market, top_n)

    def get_strong_buy_candidates(self, market: str = "KOSPI", top_n: int = 10) -> dict:
        """강력 매수 후보 - 수급 추천 + 매집 신호 결합."""
        recommendations = self.get_recommendations(market, 30)
        accumulation = self.get_accumulation_signals(market, 30)

        strong_picks = []
        if not recommendations.empty and not accumulation.empty:
            rec_symbols = set(recommendations['symbol'].tolist())
            acc_symbols = set(accumulation['symbol'].tolist())
            overlap = rec_symbols & acc_symbols

            for symbol in overlap:
                rec_row = recommendations[recommendations['symbol'] == symbol].iloc[0]
                acc_row = accumulation[accumulation['symbol'] == symbol].iloc[0]

                strong_picks.append({
                    'symbol': symbol,
                    'name': rec_row['name'],
                    'rec_score': rec_row['score'],
                    'rec_signals': rec_row['signals'],
                    'acc_score': acc_row['accumulation_score'],
                    'acc_signals': acc_row['signals'],
                    'combined_score': rec_row['score'] + acc_row['accumulation_score'],
                    'price': acc_row['price'],
                    'price_change_5d': acc_row['price_change_5d'],
                    'vol_change_pct': acc_row['vol_change_pct'],
                })

        strong_picks = sorted(strong_picks, key=lambda x: x['combined_score'], reverse=True)[:top_n]

        return {
            'strong_picks': strong_picks,
            'by_recommendation': recommendations.head(top_n).to_dict('records') if not recommendations.empty else [],
            'by_accumulation': accumulation.head(top_n).to_dict('records') if not accumulation.empty else [],
        }


# CLI 테스트
if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    recommender = KoreanStockRecommender()

    print("\n" + "="*60)
    print("[종목 추천 분석] 외국인/기관/공매도/모멘텀/거래량 종합")
    print("="*60)

    print("\n[종합 추천 TOP 10]")
    print("-"*60)
    recs = recommender.get_recommendations(top_n=10)
    if not recs.empty:
        for _, row in recs.iterrows():
            signals = row['signals'].replace('🌍', '[외]').replace('🏛️', '[기]').replace('⭐', '[*]').replace('📈', '[+]').replace('⚠️', '[!]')
            print(f"{row['rank']:2}. {row['name']:12} ({row['symbol']}) "
                  f"점수:{row['score']:5.1f} | {signals}")
    else:
        print("데이터 없음")

    print("\n[외국인+기관 동반 매수]")
    print("-"*60)
    dual = recommender.get_dual_buying_stocks()
    if not dual.empty:
        for _, row in dual.head(5).iterrows():
            print(f"  {row['name']:12} | 외국인 {row['foreign_억']:,}억 | 기관 {row['inst_억']:,}억")
    else:
        print("해당 종목 없음")

    print("\n[역발상 매수 - 공매도 높지만 수급 유입]")
    print("-"*60)
    contra = recommender.get_contrarian_picks()
    if not contra.empty:
        for _, row in contra.head(5).iterrows():
            print(f"  {row['name']:12} | 공매도 {row['short_ratio']}% "
                  f"| 외국인{row['외국인매수']} 기관{row['기관매수']}")
    else:
        print("해당 종목 없음")
