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

    def _find_swing_points(self, candles_df: pd.DataFrame, window: int = 3) -> dict:
        """스윙 포인트 탐색 (로컬 최저/최고점)."""
        swing_highs = []
        swing_lows = []

        if candles_df.empty or len(candles_df) < window * 2 + 1:
            return {'swing_highs': swing_highs, 'swing_lows': swing_lows}

        highs = candles_df['high'].values
        lows = candles_df['low'].values

        for i in range(window, len(candles_df) - window):
            # 로컬 최고점
            if highs[i] == max(highs[i - window:i + window + 1]):
                swing_highs.append(float(highs[i]))
            # 로컬 최저점
            if lows[i] == min(lows[i - window:i + window + 1]):
                swing_lows.append(float(lows[i]))

        return {
            'swing_highs': sorted(swing_highs),
            'swing_lows': sorted(swing_lows),
        }

    @staticmethod
    def _cluster_levels(levels: list, threshold_pct: float = 0.02) -> list:
        """근접한 가격 수준을 클러스터링 (2% 이내 병합)."""
        if not levels:
            return []

        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]

        for lvl in sorted_levels[1:]:
            avg = sum(current_cluster) / len(current_cluster)
            if avg > 0 and abs(lvl - avg) / avg <= threshold_pct:
                current_cluster.append(lvl)
            else:
                clusters.append({
                    'price': round(sum(current_cluster) / len(current_cluster), 4),
                    'strength': len(current_cluster),
                })
                current_cluster = [lvl]

        # 마지막 클러스터
        clusters.append({
            'price': round(sum(current_cluster) / len(current_cluster), 4),
            'strength': len(current_cluster),
        })

        # 강도순 정렬
        clusters.sort(key=lambda x: x['strength'], reverse=True)
        return clusters

    def get_entry_analysis(self, market: str, exchange: str = "upbit",
                           candles_df: pd.DataFrame = None) -> dict:
        """진입점/손절라인/지지저항 종합 분석."""
        try:
            # 캔들 데이터
            if candles_df is None:
                candles_df = self.scraper.get_candles(market, exchange, 30)

            if candles_df is None or candles_df.empty or len(candles_df) < 7:
                return {'error': '데이터 부족'}

            current_price = float(candles_df['close'].iloc[-1])
            if current_price <= 0:
                return {'error': '가격 데이터 오류'}

            # 기존 지표 활용 (개별 try로 부분 실패 허용)
            try:
                bb = self._analyze_bollinger(candles_df)
            except Exception:
                bb = {'bb_score': 0, 'bb_position': 'unknown', 'upper_band': 0, 'lower_band': 0}

            try:
                tech = self._analyze_technical(candles_df)
            except Exception:
                tech = {'ma5': 0, 'ma20': 0, 'rsi': 50, 'technical_score': 0, 'signals': []}

            try:
                rsi_val = self._calculate_rsi(candles_df['close'])
            except Exception:
                rsi_val = 50

            try:
                swings = self._find_swing_points(candles_df, window=3)
            except Exception:
                swings = {'swing_highs': [], 'swing_lows': []}

            # 지지선 후보
            support_candidates = list(swings['swing_lows'])
            if bb.get('lower_band', 0) > 0:
                support_candidates.append(bb['lower_band'])
            if tech.get('ma20', 0) > 0 and tech['ma20'] < current_price:
                support_candidates.append(tech['ma20'])
            day30_low = float(candles_df['low'].min())
            support_candidates.append(day30_low)

            # 저항선 후보
            resist_candidates = list(swings['swing_highs'])
            if bb.get('upper_band', 0) > 0:
                resist_candidates.append(bb['upper_band'])
            day30_high = float(candles_df['high'].max())
            resist_candidates.append(day30_high)

            # 현재가 기준 필터링
            support_raw = [p for p in support_candidates if p < current_price * 1.01]
            resist_raw = [p for p in resist_candidates if p > current_price * 0.99]

            # 클러스터링
            support_levels = self._cluster_levels(support_raw)
            resistance_levels = self._cluster_levels(resist_raw)

            # ── 진입점 결정 ──
            if rsi_val < 35:
                # 과매도: 현재가가 곧 진입점
                entry_point = current_price
            elif support_levels:
                # 가장 가까운 지지선과 현재가 가중평균
                nearest_sup = max([s['price'] for s in support_levels if s['price'] < current_price], default=current_price * 0.97)
                entry_point = nearest_sup * 0.4 + current_price * 0.6
            else:
                entry_point = current_price * 0.98

            entry_range = (round(entry_point * 0.99, 4), round(entry_point * 1.01, 4))

            # ── 손절라인 결정 ──
            supports_below = [s['price'] for s in support_levels if s['price'] < entry_point]
            if supports_below:
                strongest_below = max(supports_below)
                stop_loss = round(strongest_below * 0.97, 4)
            else:
                stop_loss = round(entry_point * 0.95, 4)

            # 최대 7% 제한
            max_stop = entry_point * 0.93
            if stop_loss < max_stop:
                stop_loss = round(max_stop, 4)

            stop_loss_pct = round((stop_loss - entry_point) / entry_point * 100, 1) if entry_point > 0 else 0

            # ── 목표가 결정 ──
            targets = []
            resist_prices = sorted([r['price'] for r in resistance_levels if r['price'] > current_price])

            if resist_prices:
                t1 = resist_prices[0]
                targets.append({
                    'price': round(t1, 4),
                    'label': '1차 목표',
                    'pct': round((t1 - entry_point) / entry_point * 100, 1) if entry_point > 0 else 0,
                })
            if len(resist_prices) >= 2:
                t2 = resist_prices[1]
                targets.append({
                    'price': round(t2, 4),
                    'label': '2차 목표',
                    'pct': round((t2 - entry_point) / entry_point * 100, 1) if entry_point > 0 else 0,
                })
            elif bb.get('upper_band', 0) > current_price:
                t2 = bb['upper_band']
                targets.append({
                    'price': round(t2, 4),
                    'label': '2차 목표',
                    'pct': round((t2 - entry_point) / entry_point * 100, 1) if entry_point > 0 else 0,
                })

            # 목표가 없으면 기본값
            if not targets:
                t1 = current_price * 1.05
                targets.append({
                    'price': round(t1, 4),
                    'label': '1차 목표',
                    'pct': round((t1 - entry_point) / entry_point * 100, 1) if entry_point > 0 else 0,
                })

            # ── 위험/보상 비율 ──
            risk = entry_point - stop_loss
            reward = targets[0]['price'] - entry_point if targets else 0
            rr_ratio = round(reward / risk, 2) if risk > 0 else 0
            rr_ratio = min(rr_ratio, 10.0)

            return {
                'market': market,
                'price': current_price,
                'entry_point': round(entry_point, 4),
                'entry_range': entry_range,
                'stop_loss': round(stop_loss, 4),
                'stop_loss_pct': stop_loss_pct,
                'support_levels': support_levels[:5],
                'resistance_levels': resistance_levels[:5],
                'targets': targets,
                'risk_reward_ratio': rr_ratio,
            }
        except Exception as e:
            # 폴백: 기본 진입점/손절 계산 (최소한의 데이터)
            try:
                if candles_df is not None and not candles_df.empty:
                    cp = float(candles_df['close'].iloc[-1])
                    return {
                        'market': market,
                        'price': cp,
                        'entry_point': round(cp * 0.98, 4),
                        'entry_range': (round(cp * 0.97, 4), round(cp * 0.99, 4)),
                        'stop_loss': round(cp * 0.93, 4),
                        'stop_loss_pct': -7.0,
                        'support_levels': [{'price': round(cp * 0.95, 4), 'strength': 1}],
                        'resistance_levels': [{'price': round(cp * 1.05, 4), 'strength': 1}],
                        'targets': [{'price': round(cp * 1.05, 4), 'label': '1차 목표', 'pct': 5.0}],
                        'risk_reward_ratio': 1.0,
                    }
            except Exception:
                pass
            return {'error': str(e)}

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
        """종합 추천 코인 (일봉 + 4시간봉 복합 분석).

        점수 산정 (최대 ~143점):
        - 모멘텀 (24h+5d): 최대 20점
        - 거래량 급증: 최대 15점
        - 기술적 (MA+RSI): 최대 20점
        - 거래대금 순위: 최대 10점
        - 추세 지속성: 최대 10점
        - MACD: 최대 15점
        - 볼린저밴드: 최대 15점
        - 공포탐욕지수: 최대 15점
        - 김치프리미엄 (업비트만): 최대 10점
        - 4시간봉 단기 시그널: 최대 13점 (RSI 5 + MACD 5 + 연속양봉 3)
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

            # 캔들 데이터 조회 (일봉 + 4시간봉)
            candles = self.scraper.get_candles(market_id, exchange, 30)
            time.sleep(0.05)  # rate limit
            candles_4h = self.scraper.get_4h_candles(market_id, exchange, 42)
            time.sleep(0.05)  # rate limit

            # 일봉 기반 분석 (기존)
            tech = self._analyze_technical(candles)
            momentum = self._analyze_momentum(row['change_rate'], candles)
            volume = self._analyze_volume(candles)

            # 일봉 MACD/볼린저
            macd_data = self._calculate_macd(candles['close']) if not candles.empty and len(candles) >= 26 else {'macd_score': 0, 'cross': 'none', 'signals': []}
            bb_data = self._analyze_bollinger(candles)

            # 4시간봉 추가 분석 (단기 시그널 보강)
            _4h_bonus = 0
            _4h_signals = []
            if not candles_4h.empty and len(candles_4h) >= 14:
                _4h_rsi = self._calculate_rsi(candles_4h['close'], 14)
                _4h_macd = self._calculate_macd(candles_4h['close']) if len(candles_4h) >= 26 else {'macd_score': 0, 'cross': 'none', 'signals': []}

                # 4h RSI 과매도 반등 신호
                if _4h_rsi < 30:
                    _4h_bonus += 5
                    _4h_signals.append(f"⏰4h과매도(RSI:{_4h_rsi:.0f})")
                elif _4h_rsi > 70:
                    _4h_bonus -= 3
                    _4h_signals.append(f"⚠️4h과매수(RSI:{_4h_rsi:.0f})")

                # 4h MACD 골든크로스
                if _4h_macd.get('cross') == 'golden':
                    _4h_bonus += 5
                    _4h_signals.append("⏰4h골든크로스")
                elif _4h_macd.get('cross') == 'dead':
                    _4h_bonus -= 3
                    _4h_signals.append("⚠️4h데드크로스")

                # 4h 최근 3봉 연속 양봉
                last3_4h = candles_4h.tail(3)
                green_4h = sum(1 for _, c in last3_4h.iterrows() if c['close'] > c['open'])
                if green_4h >= 3:
                    _4h_bonus += 3
                    _4h_signals.append("⏰4h연속양봉")

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

            # 총점 (일봉 + 4시간봉 보너스)
            total = (
                min(20, tech['technical_score']) +
                min(20, momentum['momentum_score']) +
                min(15, volume['volume_score']) +
                rank_score +
                trend_score +
                macd_data['macd_score'] +
                bb_data['bb_score'] +
                fg_data['fg_score'] +
                kp_data['kp_score'] +
                _4h_bonus
            )

            all_signals = (tech['signals'] + momentum['signals'] + volume['signals'] +
                          macd_data['signals'] + bb_data['signals'] + trend_signals +
                          _4h_signals)
            # 시장 전체 신호는 1위에만 표시
            if i == 0:
                all_signals.extend(fg_data['signals'])
                if kp_data['signals']:
                    all_signals.extend(kp_data['signals'])

            # 진입점 분석 (v3: row['price'] 기반 - 절대 실패 불가)
            cp = float(row['price'])
            # 캔들 데이터가 있으면 더 정교한 계산
            if not candles.empty and len(candles) >= 5:
                try:
                    closes = candles['close'].astype(float)
                    highs = candles['high'].astype(float)
                    lows = candles['low'].astype(float)
                    cp = float(closes.iloc[-1])
                    low_min = float(lows.min())
                    ma20 = float(closes.tail(20).mean()) if len(closes) >= 20 else float(closes.mean())
                    high_max = float(highs.max())
                    rsi_val = tech.get('rsi', 50)
                    if rsi_val < 35:
                        entry_point = round(cp, 2)
                    elif ma20 < cp:
                        entry_point = round(ma20, 2)
                    else:
                        entry_point = round(cp * 0.98, 2)
                    stop_loss = round(max(low_min * 0.97, entry_point * 0.95), 2)
                    stop_loss_pct = round((stop_loss - entry_point) / entry_point * 100, 1) if entry_point else -5.0
                    target_1 = round(max(high_max, cp * 1.05), 2)
                    target_1_pct = round((target_1 - entry_point) / entry_point * 100, 1) if entry_point else 5.0
                    risk = abs(entry_point - stop_loss) if entry_point else 1
                    reward = abs(target_1 - entry_point) if entry_point else 1
                    rr_ratio = round(reward / risk, 2) if risk > 0 else 1.0
                except Exception:
                    entry_point = round(cp * 0.98, 2)
                    stop_loss = round(cp * 0.93, 2)
                    stop_loss_pct = -5.0
                    target_1 = round(cp * 1.05, 2)
                    target_1_pct = 5.0
                    rr_ratio = 1.0
            else:
                # 캔들 없어도 현재가 기반으로 계산
                entry_point = round(cp * 0.98, 2)
                stop_loss = round(cp * 0.93, 2)
                stop_loss_pct = -5.0
                target_1 = round(cp * 1.05, 2)
                target_1_pct = 5.0
                rr_ratio = 1.0

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
                    'entry_point': entry_point,
                    'stop_loss': stop_loss,
                    'stop_loss_pct': stop_loss_pct,
                    'target_1': target_1,
                    'target_1_pct': target_1_pct,
                    'risk_reward': rr_ratio,
                    'signals': ', '.join(all_signals) if all_signals else '',
                })

        result = pd.DataFrame(records)
        if not result.empty:
            result = result.sort_values('score', ascending=False).head(top_n)
            result['rank'] = range(1, len(result) + 1)
            result = result[['rank', 'market', 'symbol', 'name', 'price', 'change_24h',
                           'score', 'momentum_score', 'volume_score', 'technical_score',
                           'macd_score', 'bb_score',
                           'rsi', 'macd_cross', 'bb_position', 'vol_change_pct',
                           'entry_point', 'stop_loss', 'stop_loss_pct',
                           'target_1', 'target_1_pct', 'risk_reward', 'signals']]

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

        # 진입점 분석 (이미 가져온 candles 재사용)
        entry_data = self.get_entry_analysis(market, exchange, candles_df=candles)

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
            # 진입점 분석
            'entry_point': entry_data.get('entry_point', 0),
            'entry_range': entry_data.get('entry_range', (0, 0)),
            'stop_loss': entry_data.get('stop_loss', 0),
            'stop_loss_pct': entry_data.get('stop_loss_pct', 0),
            'support_levels': entry_data.get('support_levels', []),
            'resistance_levels': entry_data.get('resistance_levels', []),
            'targets': entry_data.get('targets', []),
            'risk_reward_ratio': entry_data.get('risk_reward_ratio', 0),
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
