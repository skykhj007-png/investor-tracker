"""Korean stock recommendation analyzer based on multiple signals."""

import pandas as pd
from typing import Optional
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.korean_stocks import KoreanStocksScraper


@dataclass
class StockSignal:
    """Individual stock signal data."""
    symbol: str
    name: str
    foreign_rank: Optional[int] = None  # 외국인 순매수 순위
    foreign_amount: float = 0  # 외국인 순매수 금액
    inst_rank: Optional[int] = None  # 기관 순매수 순위
    inst_amount: float = 0  # 기관 순매수 금액
    short_ratio: float = 0  # 공매도 비중
    score: float = 0  # 종합 점수
    signals: list = None  # 시그널 목록


class KoreanStockRecommender:
    """종목 추천 분석기 - 외국인/기관/공매도 데이터 종합 분석."""

    def __init__(self):
        self.scraper = KoreanStocksScraper()

    def get_recommendations(self, market: str = "KOSPI", top_n: int = 20) -> pd.DataFrame:
        """
        종합 추천 종목 리스트 생성.

        점수 산정 기준:
        - 외국인 순매수 상위 30위 내: +30점 (순위에 따라 가중)
        - 기관 순매수 상위 30위 내: +30점 (순위에 따라 가중)
        - 외국인+기관 동반 매수: +20점 (시너지 보너스)
        - 공매도 비중 10% 이하: +10점
        - 공매도 비중 20% 이상: -10점

        Returns:
            DataFrame with recommended stocks and scores
        """
        # 데이터 수집
        foreign_df = self.scraper.get_foreign_buying(50)
        inst_df = self.scraper.get_institution_buying(50)
        short_df = self.scraper.get_short_volume(market, 100)

        if foreign_df.empty and inst_df.empty:
            return pd.DataFrame()

        # 종목별 데이터 통합
        stocks = {}

        # 외국인 순매수 데이터
        for _, row in foreign_df.iterrows():
            symbol = row['symbol']
            if symbol not in stocks:
                stocks[symbol] = StockSignal(
                    symbol=symbol,
                    name=row['name'],
                    signals=[]
                )
            stocks[symbol].foreign_rank = int(row['rank'])
            stocks[symbol].foreign_amount = row['net_amount']

        # 기관 순매수 데이터
        for _, row in inst_df.iterrows():
            symbol = row['symbol']
            if symbol not in stocks:
                stocks[symbol] = StockSignal(
                    symbol=symbol,
                    name=row['name'],
                    signals=[]
                )
            stocks[symbol].inst_rank = int(row['rank'])
            stocks[symbol].inst_amount = row['net_amount']

        # 공매도 데이터 (비중)
        short_dict = {}
        if not short_df.empty:
            for _, row in short_df.iterrows():
                short_dict[row['symbol']] = row['short_ratio']

        # 점수 계산
        for symbol, stock in stocks.items():
            score = 0
            signals = []

            # 외국인 순매수 점수 (순위가 높을수록 높은 점수)
            if stock.foreign_rank:
                foreign_score = max(0, 30 - stock.foreign_rank + 1)  # 1위=30점, 30위=1점
                score += foreign_score
                if stock.foreign_rank <= 10:
                    signals.append(f"🌍외국인 TOP{stock.foreign_rank}")
                elif stock.foreign_rank <= 30:
                    signals.append(f"외국인 {stock.foreign_rank}위")

            # 기관 순매수 점수
            if stock.inst_rank:
                inst_score = max(0, 30 - stock.inst_rank + 1)
                score += inst_score
                if stock.inst_rank <= 10:
                    signals.append(f"🏛️기관 TOP{stock.inst_rank}")
                elif stock.inst_rank <= 30:
                    signals.append(f"기관 {stock.inst_rank}위")

            # 동반 매수 시너지 보너스
            if stock.foreign_rank and stock.inst_rank:
                if stock.foreign_rank <= 30 and stock.inst_rank <= 30:
                    score += 20
                    signals.append("⭐동반매수")

            # 공매도 비중
            short_ratio = short_dict.get(symbol, 0)
            stock.short_ratio = short_ratio

            if short_ratio > 0:
                if short_ratio <= 5:
                    score += 10
                    signals.append("📈공매도 낮음")
                elif short_ratio >= 20:
                    score -= 10
                    signals.append("⚠️공매도 높음")

            stock.score = score
            stock.signals = signals

        # DataFrame 변환 및 정렬
        records = []
        for symbol, stock in stocks.items():
            if stock.score > 0:  # 점수가 있는 종목만
                records.append({
                    'symbol': stock.symbol,
                    'name': stock.name,
                    'score': stock.score,
                    'foreign_rank': stock.foreign_rank or '-',
                    'foreign_억': int(stock.foreign_amount / 100000000) if stock.foreign_amount else 0,
                    'inst_rank': stock.inst_rank or '-',
                    'inst_억': int(stock.inst_amount / 100000000) if stock.inst_amount else 0,
                    'short_ratio': round(stock.short_ratio, 1),
                    'signals': ', '.join(stock.signals) if stock.signals else '',
                })

        result = pd.DataFrame(records)
        if not result.empty:
            result = result.sort_values('score', ascending=False).head(top_n)
            result['rank'] = range(1, len(result) + 1)
            result = result[['rank', 'symbol', 'name', 'score', 'signals',
                           'foreign_rank', 'foreign_억', 'inst_rank', 'inst_억', 'short_ratio']]

        return result

    def get_dual_buying_stocks(self) -> pd.DataFrame:
        """외국인+기관 동반 매수 종목만 추출."""
        recommendations = self.get_recommendations(top_n=50)

        if recommendations.empty:
            return pd.DataFrame()

        # 동반매수 시그널이 있는 종목만 필터
        dual = recommendations[recommendations['signals'].str.contains('동반매수', na=False)]
        return dual

    def get_contrarian_picks(self, market: str = "KOSPI") -> pd.DataFrame:
        """
        역발상 매수 후보 - 공매도 비중 높지만 외국인/기관이 매수하는 종목.
        (숏 스퀴즈 가능성)
        """
        foreign_df = self.scraper.get_foreign_buying(50)
        inst_df = self.scraper.get_institution_buying(50)
        short_df = self.scraper.get_short_volume(market, 50)

        if short_df.empty:
            return pd.DataFrame()

        # 공매도 비중 높은 종목 (15% 이상)
        high_short = short_df[short_df['short_ratio'] >= 15].copy()

        if high_short.empty:
            return pd.DataFrame()

        # 외국인/기관 매수 종목과 교집합
        foreign_symbols = set(foreign_df['symbol'].tolist()) if not foreign_df.empty else set()
        inst_symbols = set(inst_df['symbol'].tolist()) if not inst_df.empty else set()
        buying_symbols = foreign_symbols | inst_symbols

        # 공매도 높지만 매수세 유입
        contrarian = high_short[high_short['symbol'].isin(buying_symbols)].copy()

        if contrarian.empty:
            return pd.DataFrame()

        # 외국인/기관 매수 정보 추가
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
        """강력 매수 후보 - 수급 추천 + 매집 신호 결합.

        양쪽 조건을 모두 만족하는 종목을 강력 매수 후보로 추천.
        """
        # 수급 기반 추천
        recommendations = self.get_recommendations(market, 30)

        # 매집 신호
        accumulation = self.get_accumulation_signals(market, 30)

        # 양쪽에 모두 등장하는 종목 = 강력 추천
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

        # 정렬
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
    print("[종목 추천 분석] 외국인/기관/공매도 종합")
    print("="*60)

    print("\n[종합 추천 TOP 10]")
    print("-"*60)
    recs = recommender.get_recommendations(top_n=10)
    if not recs.empty:
        for _, row in recs.iterrows():
            signals = row['signals'].replace('🌍', '[외]').replace('🏛️', '[기]').replace('⭐', '[*]').replace('📈', '[+]').replace('⚠️', '[!]')
            print(f"{row['rank']:2}. {row['name']:12} ({row['symbol']}) "
                  f"점수:{row['score']:3} | {signals}")
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
