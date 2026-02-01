"""연금저축 투자상품 추천 분석기."""

import pandas as pd
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.pension_etf import ETFScraper, NewsScraper, AssetAllocationAdvisor, SectorLeaderData


@dataclass
class MarketSentiment:
    """시장 심리 분석 결과."""
    overall: str  # bullish, neutral, bearish
    score: int  # -100 ~ +100
    themes: list  # 유망 테마
    news_summary: str  # 뉴스 요약


class PensionRecommender:
    """연금저축 투자상품 추천기."""

    # 키워드별 감성 점수
    SENTIMENT_KEYWORDS = {
        'positive': ['상승', '호재', '급등', '신고가', '매수', '상향', '호실적', '성장', '회복', '반등'],
        'negative': ['하락', '악재', '급락', '신저가', '매도', '하향', '부진', '우려', '리스크', '조정'],
    }

    # 테마별 추천 ETF 키워드
    THEME_ETF_KEYWORDS = {
        '반도체': ['반도체', 'SEMICONDUCTOR'],
        '2차전지': ['2차전지', '배터리', 'BATTERY'],
        'AI': ['AI', '인공지능', 'GPT'],
        '바이오': ['바이오', '헬스케어', 'BIO', 'HEALTHCARE'],
        '금리': ['채권', '국채', 'BOND'],
        '인플레이션': ['금', 'GOLD', '원자재'],
        '미국': ['미국', 'S&P', 'NASDAQ', '나스닥'],
        '배당': ['배당', '고배당', 'DIVIDEND'],
    }

    def __init__(self):
        self.etf_scraper = ETFScraper()
        self.news_scraper = NewsScraper()
        self.allocator = AssetAllocationAdvisor()

    def analyze_market_sentiment(self) -> MarketSentiment:
        """시장 심리 분석."""
        # 뉴스 수집
        news_items = self.news_scraper.get_market_news("증시", 20)
        themes = self.news_scraper.get_trending_themes()

        # 감성 분석
        positive_count = 0
        negative_count = 0

        for news in news_items:
            title = news['title']
            for keyword in self.SENTIMENT_KEYWORDS['positive']:
                if keyword in title:
                    positive_count += 1
            for keyword in self.SENTIMENT_KEYWORDS['negative']:
                if keyword in title:
                    negative_count += 1

        # 점수 계산 (-100 ~ +100)
        total = positive_count + negative_count
        if total > 0:
            score = int(((positive_count - negative_count) / total) * 100)
        else:
            score = 0

        # 전체 심리 판단
        if score > 20:
            overall = 'bullish'
        elif score < -20:
            overall = 'bearish'
        else:
            overall = 'neutral'

        # 유망 테마 추출
        hot_themes = [t['name'] for t in themes[:5]] if themes else []

        # 뉴스 요약
        news_summary = "주요 뉴스: " + ", ".join([n['title'][:30] for n in news_items[:3]]) if news_items else ""

        return MarketSentiment(
            overall=overall,
            score=score,
            themes=hot_themes,
            news_summary=news_summary,
        )

    def get_sentiment_based_allocation(self) -> dict:
        """시장 심리 기반 자산배분 추천."""
        sentiment = self.analyze_market_sentiment()

        # 심리에 따른 리스크 수준 결정
        if sentiment.overall == 'bullish':
            risk_level = 'aggressive'
            advice = "시장 심리가 긍정적입니다. 주식 비중 확대를 고려할 수 있습니다."
        elif sentiment.overall == 'bearish':
            risk_level = 'conservative'
            advice = "시장 심리가 부정적입니다. 채권/현금 비중 확대를 고려하세요."
        else:
            risk_level = 'moderate'
            advice = "시장 심리가 중립적입니다. 균형 잡힌 포트폴리오를 유지하세요."

        allocation = self.allocator.get_recommended_allocation(risk_level)

        return {
            'sentiment': {
                'overall': sentiment.overall,
                'score': sentiment.score,
                'themes': sentiment.themes,
            },
            'advice': advice,
            'allocation': allocation,
            'risk_level': risk_level,
        }

    def get_theme_etfs(self, theme: str, top_n: int = 5) -> pd.DataFrame:
        """테마별 ETF 추천."""
        etfs = self.etf_scraper.get_pension_etfs(50)

        if etfs.empty:
            return pd.DataFrame()

        # 테마 키워드 매칭
        keywords = self.THEME_ETF_KEYWORDS.get(theme, [theme])

        filtered = etfs[etfs['name'].str.upper().apply(
            lambda x: any(kw.upper() in x for kw in keywords)
        )]

        if filtered.empty:
            # 매칭 실패시 자산군으로 시도
            filtered = etfs[etfs['asset_class'] == theme]

        return filtered.head(top_n)

    def get_comprehensive_recommendation(self) -> dict:
        """종합 연금저축 추천."""
        # 1. 시장 심리 분석
        sentiment = self.analyze_market_sentiment()

        # 2. 자산배분 추천
        allocation_result = self.get_sentiment_based_allocation()

        # 3. ETF 수익률 상위
        top_etfs = self.etf_scraper.get_pension_etfs(10)

        # 4. 테마별 추천
        theme_recommendations = {}
        for theme in sentiment.themes[:3]:
            theme_etfs = self.get_theme_etfs(theme, 3)
            if not theme_etfs.empty:
                theme_recommendations[theme] = theme_etfs.to_dict('records')

        # 5. 자산군별 추천
        asset_class_recommendations = {}
        for asset_class, weight in allocation_result['allocation'].items():
            if weight > 0:
                class_etfs = self.etf_scraper.get_etfs_by_asset_class(asset_class, 3)
                if not class_etfs.empty:
                    asset_class_recommendations[asset_class] = {
                        'weight': weight,
                        'etfs': class_etfs.to_dict('records'),
                    }

        return {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'market_sentiment': {
                'overall': sentiment.overall,
                'score': sentiment.score,
                'themes': sentiment.themes,
            },
            'allocation': allocation_result,
            'top_etfs': top_etfs.to_dict('records') if not top_etfs.empty else [],
            'theme_recommendations': theme_recommendations,
            'asset_class_recommendations': asset_class_recommendations,
        }

    def get_quick_picks(self, top_n: int = 5) -> pd.DataFrame:
        """빠른 추천 - 수익률 + 연금적합 ETF."""
        etfs = self.etf_scraper.get_pension_etfs(20)

        if etfs.empty:
            return pd.DataFrame()

        # 수익률 + 거래량 기반 점수
        etfs = etfs.copy()
        etfs['score'] = etfs['return_1m'] * 0.6 + etfs['return_3m'] * 0.4

        return etfs.sort_values('score', ascending=False).head(top_n)

    def get_sector_leaders(self, sector: str) -> dict:
        """섹터별 대장주 + 관련 뉴스 조회."""
        leaders = SectorLeaderData.get_leaders(sector)
        news = self.news_scraper.get_theme_news(sector, 5)

        return {
            'sector': sector,
            'leaders': [
                {'rank': i + 1, 'symbol': s, 'name': n, 'description': d}
                for i, (s, n, d) in enumerate(leaders)
            ],
            'news': news,
        }

    def get_all_sectors(self) -> list:
        """전체 섹터 목록 조회."""
        return SectorLeaderData.get_all_sectors()

    def get_promising_sectors(self, top_n: int = 5) -> list:
        """유망 섹터 + 대장주 + 뉴스 종합."""
        sentiment = self.analyze_market_sentiment()
        trending_themes = sentiment.themes[:top_n] if sentiment.themes else []

        # 기본 섹터 추가 (트렌딩 테마가 부족할 경우)
        default_sectors = ['반도체', 'AI', '2차전지', '바이오', '자동차']
        for sector in default_sectors:
            if sector not in trending_themes and len(trending_themes) < top_n:
                trending_themes.append(sector)

        results = []
        for theme in trending_themes[:top_n]:
            # 섹터명 매칭
            sector_name = self._match_sector_name(theme)
            if sector_name:
                sector_data = self.get_sector_leaders(sector_name)
                if sector_data['leaders']:
                    results.append(sector_data)

        return results

    def _match_sector_name(self, theme: str) -> str:
        """테마명을 섹터명으로 매칭."""
        theme_lower = theme.lower()
        sector_mapping = {
            '반도체': ['반도체', 'semiconductor', 'hbm', '메모리'],
            '2차전지': ['2차전지', '배터리', 'battery', '전기차'],
            'AI': ['ai', '인공지능', 'gpt', '챗봇'],
            '바이오': ['바이오', '제약', 'bio', '헬스케어'],
            '자동차': ['자동차', '전기차', 'ev', '완성차'],
            '조선': ['조선', 'lng', '해양'],
            '방산': ['방산', '방위', '국방', '무기'],
            '엔터': ['엔터', '연예', 'k-pop', 'kpop'],
            '게임': ['게임', 'game', '온라인'],
            '인터넷': ['인터넷', 'it', '플랫폼'],
            '금융': ['금융', '은행', '보험', '증권'],
            '철강': ['철강', '포스코', 'steel'],
            '화학': ['화학', '석유', '정유'],
            '건설': ['건설', '부동산', '주택'],
            '유틸리티': ['전력', '가스', '에너지'],
            '통신': ['통신', '5g', '이동통신'],
            '로봇': ['로봇', '자동화', 'automation'],
        }

        for sector, keywords in sector_mapping.items():
            for kw in keywords:
                if kw in theme_lower:
                    return sector
        return None

    def get_accumulation_signals(self, top_n: int = 15) -> pd.DataFrame:
        """ETF 매집 신호 분석.

        거래량 증가 + 가격 추세를 분석하여 매집 신호 포착.
        - 거래량 급증 + 가격 상승 = 강한 매집
        - 거래량 급증 + 가격 하락 = 세력 매집 추정
        """
        return self.etf_scraper.get_etf_accumulation_signals(top_n)

    def get_accumulation_with_news(self, top_n: int = 10) -> list:
        """매집 신호 + 관련 뉴스 종합."""
        signals_df = self.get_accumulation_signals(top_n)

        if signals_df.empty:
            return []

        results = []
        for _, row in signals_df.iterrows():
            # ETF 이름에서 테마 추출
            etf_name = row['name']
            theme = self._extract_theme_from_name(etf_name)

            # 관련 뉴스
            news = []
            if theme:
                news = self.news_scraper.get_theme_news(theme, 3)

            results.append({
                'rank': row['rank'],
                'symbol': row['symbol'],
                'name': row['name'],
                'price': row['price'],
                'price_change_5d': row['price_change_5d'],
                'vol_change_pct': row['vol_change_pct'],
                'accumulation_score': row['accumulation_score'],
                'signals': row['signals'],
                'asset_class': row['asset_class'],
                'theme': theme,
                'news': news,
            })

        return results

    def _extract_theme_from_name(self, name: str) -> str:
        """ETF 이름에서 테마 추출."""
        theme_keywords = {
            '반도체': ['반도체', 'AI반도체'],
            '2차전지': ['2차전지', '배터리'],
            'AI': ['AI', '인공지능'],
            '바이오': ['바이오', '헬스케어'],
            '미국': ['미국', 'S&P', '나스닥', 'NASDAQ'],
            '채권': ['채권', '국채'],
            '배당': ['배당', '고배당'],
            '금': ['골드', '금'],
        }

        name_upper = name.upper()
        for theme, keywords in theme_keywords.items():
            for kw in keywords:
                if kw.upper() in name_upper:
                    return theme
        return None

    def get_buy_recommendations(self, top_n: int = 10) -> dict:
        """종합 매수 추천 - 수익률 + 매집 신호 결합."""
        # 수익률 기준
        quick_picks = self.get_quick_picks(15)

        # 매집 신호 기준
        accumulation = self.get_accumulation_signals(15)

        # 양쪽에 모두 등장하는 ETF = 강력 추천
        strong_picks = []
        if not quick_picks.empty and not accumulation.empty:
            quick_symbols = set(quick_picks['symbol'].tolist())
            acc_symbols = set(accumulation['symbol'].tolist())
            overlap = quick_symbols & acc_symbols

            for symbol in overlap:
                quick_row = quick_picks[quick_picks['symbol'] == symbol].iloc[0]
                acc_row = accumulation[accumulation['symbol'] == symbol].iloc[0]

                strong_picks.append({
                    'symbol': symbol,
                    'name': quick_row['name'],
                    'price': quick_row['price'],
                    'return_1m': quick_row['return_1m'],
                    'accumulation_score': acc_row['accumulation_score'],
                    'signals': acc_row['signals'],
                    'combined_score': quick_row['score'] + acc_row['accumulation_score'],
                })

        # 정렬
        strong_picks = sorted(strong_picks, key=lambda x: x['combined_score'], reverse=True)[:top_n]

        return {
            'strong_picks': strong_picks,  # 수익률 + 매집 동시 충족
            'by_return': quick_picks.head(top_n).to_dict('records') if not quick_picks.empty else [],
            'by_accumulation': accumulation.head(top_n).to_dict('records') if not accumulation.empty else [],
        }


# CLI 테스트
if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n" + "=" * 60)
    print("[연금저축 투자상품 추천]")
    print("=" * 60)

    recommender = PensionRecommender()

    # 시장 심리
    print("\n[시장 심리 분석]")
    print("-" * 60)
    sentiment = recommender.analyze_market_sentiment()
    print(f"전체 심리: {sentiment.overall} (점수: {sentiment.score})")
    print(f"유망 테마: {', '.join(sentiment.themes[:5])}")

    # 자산배분 추천
    print("\n[자산배분 추천]")
    print("-" * 60)
    allocation = recommender.get_sentiment_based_allocation()
    print(f"추천 성향: {allocation['risk_level']}")
    print(f"조언: {allocation['advice']}")
    print("추천 배분:")
    for asset, weight in allocation['allocation'].items():
        if weight > 0:
            print(f"  - {asset}: {weight}%")

    # 빠른 추천
    print("\n[연금저축 ETF 추천 TOP 5]")
    print("-" * 60)
    picks = recommender.get_quick_picks(5)
    if not picks.empty:
        for _, row in picks.iterrows():
            print(f"{row['rank']:2}. {row['name'][:25]:25} | 1M: {row['return_1m']:+.1f}% | {row['asset_class']}")
    else:
        print("데이터 없음")
