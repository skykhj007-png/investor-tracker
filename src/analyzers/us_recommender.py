"""US stock recommendation analyzer based on super investor data from Dataroma."""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.dataroma import DataromaScraper


FAMOUS_INVESTORS = {
    'BRK': '워렌 버핏',
    'icahn': '칼 아이칸',
    'soros': '조지 소로스',
    'BRIDGEWATER': '레이 달리오',
    'einhorn': '데이비드 아인혼',
    'ackman': '빌 애크먼',
    'BERKOWITZ': '브루스 버코위츠',
    'tepper': '데이비드 테퍼',
    'THIRD POINT': '댄 로브',
    'BAUPOST': '세스 클라만',
    'gates': '빌 게이츠',
}


@dataclass
class USStockSignal:
    """Individual US stock signal data."""
    symbol: str
    name: str
    num_owners: int = 0
    percent_total: float = 0
    hold_price: float = 0
    current_price: float = 0
    score: float = 0
    signals: list = field(default_factory=list)
    # Activity breakdown
    new_buys: int = 0
    adds: int = 0
    reduces: int = 0
    sells: int = 0
    # Conviction
    avg_conviction: float = 0
    max_conviction: float = 0
    famous_holders: list = field(default_factory=list)


class USStockRecommender:
    """미국주식 추천 분석기 - 슈퍼투자자 보유/매매 활동 종합 분석."""

    def __init__(self):
        self.scraper = DataromaScraper()

    def get_recommendations(self, top_n: int = 20) -> pd.DataFrame:
        """
        슈퍼투자자 데이터 기반 미국주식 종합 추천.

        점수 산정:
        - 보유 투자자 수: 최대 30점
        - 최근 매수 활동 (신규/추가): 최대 25점
        - 포트폴리오 비중 (확신도): 최대 20점
        - 가격 분석 (현재가 vs 매수가): 최대 15점
        - 유명 투자자 보유: 최대 10점
        """
        grand = self.scraper.get_grand_portfolio()
        if grand.empty:
            return pd.DataFrame()

        # Collect activity data from top investors
        investors = self.scraper.get_investor_list()
        activity_map = self._collect_activity(investors, grand)

        signals = []
        max_owners = grand['num_owners'].max() if not grand.empty else 1

        for _, row in grand.iterrows():
            symbol = row['symbol']
            signal = USStockSignal(
                symbol=symbol,
                name=row.get('stock', symbol),
                num_owners=int(row.get('num_owners', 0)),
                percent_total=float(row.get('percent_total', 0)),
                hold_price=self._safe_float(row.get('hold_price', 0)),
                current_price=self._safe_float(row.get('current_price', 0)),
            )

            # Activity data
            act = activity_map.get(symbol, {})
            signal.new_buys = act.get('new', 0)
            signal.adds = act.get('add', 0)
            signal.reduces = act.get('reduce', 0)
            signal.sells = act.get('sell', 0)
            signal.avg_conviction = act.get('avg_conviction', 0)
            signal.max_conviction = act.get('max_conviction', 0)
            signal.famous_holders = act.get('famous_holders', [])

            # --- Scoring ---
            score = 0

            # 1) Ownership count (max 30)
            ownership_score = min(30, (signal.num_owners / max(max_owners, 1)) * 30)
            if signal.num_owners >= 15:
                ownership_score = 30
            score += ownership_score
            if signal.num_owners >= 10:
                signal.signals.append(f"👥{signal.num_owners}명 보유")

            # 2) Recent buy activity (max 25)
            activity_score = 0
            activity_score += signal.new_buys * 8  # New position = strong signal
            activity_score += signal.adds * 4       # Adding = moderate signal
            activity_score -= signal.reduces * 2    # Reducing = mild negative
            activity_score -= signal.sells * 5      # Selling = negative
            activity_score = max(0, min(25, activity_score))
            score += activity_score
            if signal.new_buys > 0:
                signal.signals.append(f"🆕신규매수 {signal.new_buys}건")
            if signal.adds > 0:
                signal.signals.append(f"📈추가매수 {signal.adds}건")
            if signal.reduces > 0:
                signal.signals.append(f"📉일부매도 {signal.reduces}건")

            # 3) Conviction / portfolio weight (max 20)
            conviction_score = 0
            if signal.avg_conviction > 0:
                conviction_score = min(20, signal.avg_conviction * 2)
            if signal.max_conviction >= 10:
                conviction_score = min(20, conviction_score + 5)
                signal.signals.append(f"💪최대비중 {signal.max_conviction:.1f}%")
            score += conviction_score

            # 4) Price analysis: current vs hold (max 15)
            price_score = 0
            if signal.hold_price > 0 and signal.current_price > 0:
                price_change = ((signal.current_price - signal.hold_price) / signal.hold_price) * 100
                if price_change < -10:
                    # Trading below avg buy price = potential value
                    price_score = min(15, abs(price_change) * 0.5)
                    signal.signals.append(f"💰매수가대비 {price_change:+.1f}%")
                elif price_change > 20:
                    # Up significantly from buy price
                    price_score = 5
                    signal.signals.append(f"🚀+{price_change:.0f}% 상승")
                else:
                    price_score = 8
            score += price_score

            # 5) Famous investor holdings (max 10)
            famous_score = len(signal.famous_holders) * 3
            famous_score = min(10, famous_score)
            score += famous_score
            if signal.famous_holders:
                names = [FAMOUS_INVESTORS.get(h, h) for h in signal.famous_holders[:3]]
                signal.signals.append(f"⭐{'·'.join(names)}")

            signal.score = round(score, 1)
            signals.append(signal)

        # Sort by score
        signals.sort(key=lambda x: x.score, reverse=True)
        signals = signals[:top_n]

        # Build DataFrame
        rows = []
        for i, s in enumerate(signals, 1):
            rows.append({
                'rank': i,
                'symbol': s.symbol,
                'name': s.name,
                'score': s.score,
                'num_owners': s.num_owners,
                'new_buys': s.new_buys,
                'adds': s.adds,
                'reduces': s.reduces,
                'avg_conviction': round(s.avg_conviction, 1),
                'hold_price': s.hold_price,
                'current_price': s.current_price,
                'famous_holders': ', '.join([FAMOUS_INVESTORS.get(h, h) for h in s.famous_holders]),
                'signals': ', '.join(s.signals) if s.signals else '-',
            })

        return pd.DataFrame(rows)

    def get_new_buys(self, top_n: int = 15) -> pd.DataFrame:
        """최근 신규 매수 종목 (New position)."""
        investors = self.scraper.get_investor_list()
        if investors.empty:
            return pd.DataFrame()

        new_positions = []

        for _, inv in investors.head(20).iterrows():
            inv_id = inv['investor_id']
            inv_name = inv['name']
            try:
                portfolio = self.scraper.get_portfolio(inv_id)
                if portfolio.empty:
                    continue
                for _, h in portfolio.iterrows():
                    activity = str(h.get('activity', '')).strip().lower()
                    if 'new' in activity or 'buy' in activity:
                        new_positions.append({
                            'symbol': h['symbol'],
                            'name': h['stock'],
                            'investor_id': inv_id,
                            'investor_name': inv_name,
                            'percent_portfolio': h.get('percent_portfolio', 0),
                            'value': h.get('value', 0),
                            'activity': h.get('activity', ''),
                        })
            except Exception:
                continue

        if not new_positions:
            return pd.DataFrame()

        df = pd.DataFrame(new_positions)

        # Group by symbol, count investors
        summary = df.groupby(['symbol', 'name']).agg(
            buyer_count=('investor_name', 'count'),
            buyers=('investor_name', lambda x: ', '.join(x.unique())),
            avg_conviction=('percent_portfolio', 'mean'),
            total_value=('value', 'sum'),
        ).reset_index()

        summary = summary.sort_values('buyer_count', ascending=False).head(top_n)
        summary.insert(0, 'rank', range(1, len(summary) + 1))

        return summary

    def get_high_conviction(self, top_n: int = 15) -> pd.DataFrame:
        """고확신 종목 (포트폴리오 비중 높은 종목)."""
        investors = self.scraper.get_investor_list()
        if investors.empty:
            return pd.DataFrame()

        holdings = []

        for _, inv in investors.head(20).iterrows():
            inv_id = inv['investor_id']
            inv_name = inv['name']
            try:
                portfolio = self.scraper.get_portfolio(inv_id)
                if portfolio.empty:
                    continue
                for _, h in portfolio.iterrows():
                    pct = h.get('percent_portfolio', 0)
                    if pct >= 5:  # 5% or more of portfolio
                        holdings.append({
                            'symbol': h['symbol'],
                            'name': h['stock'],
                            'investor_id': inv_id,
                            'investor_name': inv_name,
                            'percent_portfolio': pct,
                            'value': h.get('value', 0),
                        })
            except Exception:
                continue

        if not holdings:
            return pd.DataFrame()

        df = pd.DataFrame(holdings)

        summary = df.groupby(['symbol', 'name']).agg(
            holder_count=('investor_name', 'count'),
            holders=('investor_name', lambda x: ', '.join(x.unique())),
            avg_conviction=('percent_portfolio', 'mean'),
            max_conviction=('percent_portfolio', 'max'),
            total_value=('value', 'sum'),
        ).reset_index()

        summary = summary.sort_values('max_conviction', ascending=False).head(top_n)
        summary.insert(0, 'rank', range(1, len(summary) + 1))
        summary['avg_conviction'] = summary['avg_conviction'].round(1)
        summary['max_conviction'] = summary['max_conviction'].round(1)

        return summary

    def _collect_activity(self, investors: pd.DataFrame, grand: pd.DataFrame) -> dict:
        """Collect activity data from top investor portfolios."""
        activity_map = {}  # symbol -> {new, add, reduce, sell, avg_conviction, famous_holders}

        # Initialize from grand portfolio
        for _, row in grand.iterrows():
            symbol = row['symbol']
            activity_map[symbol] = {
                'new': 0, 'add': 0, 'reduce': 0, 'sell': 0,
                'avg_conviction': 0, 'max_conviction': 0,
                'convictions': [], 'famous_holders': [],
            }

        if investors.empty:
            return activity_map

        # Sample top 15 investors to avoid too many requests
        for _, inv in investors.head(15).iterrows():
            inv_id = inv['investor_id']
            try:
                portfolio = self.scraper.get_portfolio(inv_id)
                if portfolio.empty:
                    continue

                for _, h in portfolio.iterrows():
                    symbol = h['symbol']
                    if symbol not in activity_map:
                        activity_map[symbol] = {
                            'new': 0, 'add': 0, 'reduce': 0, 'sell': 0,
                            'avg_conviction': 0, 'max_conviction': 0,
                            'convictions': [], 'famous_holders': [],
                        }

                    act = activity_map[symbol]
                    activity = str(h.get('activity', '')).strip().lower()

                    if 'new' in activity:
                        act['new'] += 1
                    elif 'add' in activity:
                        act['add'] += 1
                    elif 'reduce' in activity:
                        act['reduce'] += 1
                    elif 'sold' in activity or 'sell' in activity:
                        act['sell'] += 1

                    pct = h.get('percent_portfolio', 0)
                    if pct > 0:
                        act['convictions'].append(pct)

                    if inv_id in FAMOUS_INVESTORS and inv_id not in act['famous_holders']:
                        act['famous_holders'].append(inv_id)

            except Exception:
                continue

        # Compute averages
        for symbol, act in activity_map.items():
            if act['convictions']:
                act['avg_conviction'] = sum(act['convictions']) / len(act['convictions'])
                act['max_conviction'] = max(act['convictions'])
            del act['convictions']

        return activity_map

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(str(value).replace(',', '').replace('$', '').strip())
        except (ValueError, TypeError):
            return 0.0


if __name__ == "__main__":
    recommender = USStockRecommender()

    print("=== US Stock Recommendations ===")
    recs = recommender.get_recommendations(10)
    print(recs.to_string(index=False))

    print("\n=== New Buys ===")
    new_buys = recommender.get_new_buys(5)
    print(new_buys.to_string(index=False))

    print("\n=== High Conviction ===")
    high_conv = recommender.get_high_conviction(5)
    print(high_conv.to_string(index=False))
