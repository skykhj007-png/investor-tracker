"""연금저축 ETF 데이터 스크래퍼 (최적화 버전)."""

import pandas as pd
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import os

try:
    from pykrx import stock as krx
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False


# 캐시 파일 경로
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
ETF_CACHE_FILE = os.path.join(CACHE_DIR, 'etf_cache.json')


def get_recent_trading_date():
    """최근 거래일 반환."""
    today = datetime.now()
    if today.weekday() == 5:
        today -= timedelta(days=1)
    elif today.weekday() == 6:
        today -= timedelta(days=2)
    if today.hour < 16:
        today -= timedelta(days=1)
        if today.weekday() == 5:
            today -= timedelta(days=1)
        elif today.weekday() == 6:
            today -= timedelta(days=2)
    return today.strftime("%Y%m%d")


class ETFScraper:
    """국내 ETF 데이터 스크래퍼 (최적화)."""

    PENSION_ELIGIBLE_KEYWORDS = [
        'KODEX', 'TIGER', 'KBSTAR', 'ARIRANG', 'HANARO',
        'SOL', 'ACE', 'KOSEF', 'SMART', 'TIMEFOLIO'
    ]

    ASSET_CLASS_KEYWORDS = {
        '국내주식': ['코스피', 'KOSPI', '200', '코스닥', 'KOSDAQ', '대형', '중형', '소형', '배당', '가치', '성장'],
        '미국주식': ['미국', 'S&P', 'S&P500', '나스닥', 'NASDAQ', 'NYSE', '다우'],
        '선진국': ['선진국', 'MSCI', '유럽', '일본', '호주'],
        '신흥국': ['신흥국', '중국', '인도', '베트남', '브라질'],
        '채권': ['채권', '국채', '회사채', '단기', '중기', '장기', 'BOND', '금리'],
        '원자재': ['금', '골드', 'GOLD', '은', '원유', '구리', '원자재', '농산물'],
        '섹터': ['반도체', '2차전지', '배터리', '바이오', '헬스케어', 'IT', '금융', '자동차', 'AI', '로봇'],
        'TDF': ['TDF', 'Target'],
    }

    # 인기 연금저축 ETF 목록 (사전 정의 - 빠른 조회용)
    POPULAR_PENSION_ETFS = [
        # 국내지수
        ('069500', 'KODEX 200', '국내주식'),
        ('102110', 'TIGER 200', '국내주식'),
        ('226490', 'KODEX 코스피', '국내주식'),
        ('229200', 'KODEX 코스닥150', '국내주식'),
        ('251340', 'KODEX 코스닥150레버리지', '국내주식'),
        ('278530', 'KODEX 코스닥150선물인버스', '국내주식'),
        # 미국지수
        ('360750', 'TIGER 미국S&P500', '미국주식'),
        ('379800', 'KODEX 미국S&P500TR', '미국주식'),
        ('133690', 'TIGER 미국나스닥100', '미국주식'),
        ('379810', 'KODEX 미국나스닥100TR', '미국주식'),
        ('381180', 'TIGER 미국테크TOP10 INDXX', '미국주식'),
        # 섹터
        ('091180', 'KODEX 반도체', '섹터'),
        ('091230', 'TIGER 반도체', '섹터'),
        ('305720', 'KODEX 2차전지산업', '섹터'),
        ('364980', 'TIGER 2차전지테마', '섹터'),
        ('143860', 'TIGER 헬스케어', '섹터'),
        ('266370', 'KODEX AI반도체핵심장비', '섹터'),
        # 채권
        ('148070', 'KOSEF 국고채10년', '채권'),
        ('152380', 'KODEX 국고채3년', '채권'),
        ('114260', 'KODEX 국고채3년', '채권'),
        ('273130', 'KODEX 종합채권(AA-이상)액티브', '채권'),
        # 배당
        ('211560', 'TIGER 배당성장', '국내주식'),
        ('161510', 'ARIRANG 고배당주', '국내주식'),
        ('104530', 'KODEX 고배당', '국내주식'),
        # 원자재
        ('132030', 'KODEX 골드선물(H)', '원자재'),
        ('411060', 'ACE 금현물', '원자재'),
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """캐시 디렉토리 생성."""
        os.makedirs(CACHE_DIR, exist_ok=True)

    def get_etf_performance(self, top_n: int = 30) -> pd.DataFrame:
        """인기 ETF 수익률 조회 (최적화)."""
        if not PYKRX_AVAILABLE:
            return self._get_fallback_etf_data(top_n)

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")

            # 날짜 범위 설정 (휴일 대비)
            one_month_start = (today_dt - timedelta(days=35)).strftime("%Y%m%d")
            one_month_end = (today_dt - timedelta(days=25)).strftime("%Y%m%d")
            three_month_start = (today_dt - timedelta(days=95)).strftime("%Y%m%d")
            three_month_end = (today_dt - timedelta(days=85)).strftime("%Y%m%d")

            records = []
            for ticker, name, asset_class in self.POPULAR_PENSION_ETFS[:top_n * 2]:
                try:
                    # 현재가 조회
                    ohlcv = krx.get_etf_ohlcv_by_date(trd_date, trd_date, ticker)
                    if ohlcv.empty:
                        continue

                    current_price = int(ohlcv.iloc[-1]['종가'])
                    volume = int(ohlcv.iloc[-1]['거래량'])

                    # 1개월 전 가격 (범위 조회)
                    return_1m = 0
                    try:
                        ohlcv_1m = krx.get_etf_ohlcv_by_date(one_month_start, one_month_end, ticker)
                        if not ohlcv_1m.empty:
                            price_1m = ohlcv_1m.iloc[-1]['종가']
                            return_1m = round(((current_price - price_1m) / price_1m) * 100, 2)
                    except:
                        pass

                    # 3개월 전 가격 (범위 조회)
                    return_3m = 0
                    try:
                        ohlcv_3m = krx.get_etf_ohlcv_by_date(three_month_start, three_month_end, ticker)
                        if not ohlcv_3m.empty:
                            price_3m = ohlcv_3m.iloc[-1]['종가']
                            return_3m = round(((current_price - price_3m) / price_3m) * 100, 2)
                    except:
                        pass

                    is_pension = any(kw in name for kw in self.PENSION_ELIGIBLE_KEYWORDS)

                    records.append({
                        'symbol': ticker,
                        'name': name,
                        'price': current_price,
                        'volume': volume,
                        'return_1m': return_1m,
                        'return_3m': return_3m,
                        'asset_class': asset_class,
                        'pension_eligible': is_pension,
                    })
                except Exception as e:
                    continue

            df = pd.DataFrame(records)
            if not df.empty:
                df = df[df['volume'] > 100]
                df = df.sort_values('return_1m', ascending=False).head(top_n)
                df['rank'] = range(1, len(df) + 1)

            return df

        except Exception as e:
            print(f"ETF 수익률 조회 오류: {e}")
            return self._get_fallback_etf_data(top_n)

    def _get_fallback_etf_data(self, top_n: int) -> pd.DataFrame:
        """폴백 데이터 (캐시 또는 정적 데이터)."""
        records = []
        for i, (ticker, name, asset_class) in enumerate(self.POPULAR_PENSION_ETFS[:top_n]):
            records.append({
                'rank': i + 1,
                'symbol': ticker,
                'name': name,
                'price': 0,
                'volume': 0,
                'return_1m': 0,
                'return_3m': 0,
                'asset_class': asset_class,
                'pension_eligible': True,
            })
        return pd.DataFrame(records)

    def get_pension_etfs(self, top_n: int = 20) -> pd.DataFrame:
        """연금저축 적합 ETF."""
        df = self.get_etf_performance(top_n * 2)
        if df.empty:
            return df
        pension_df = df[df['pension_eligible'] == True].head(top_n)
        return pension_df

    def get_etfs_by_asset_class(self, asset_class: str, top_n: int = 5) -> pd.DataFrame:
        """자산군별 ETF."""
        df = self.get_etf_performance(50)
        if df.empty:
            return df
        filtered = df[df['asset_class'] == asset_class].head(top_n)
        if filtered.empty:
            # 정적 데이터에서 자산군 필터
            records = [
                {'symbol': t, 'name': n, 'asset_class': a, 'return_1m': 0, 'price': 0}
                for t, n, a in self.POPULAR_PENSION_ETFS if a == asset_class
            ][:top_n]
            return pd.DataFrame(records)
        return filtered

    def _classify_asset_class(self, name: str) -> str:
        """자산군 분류."""
        name_upper = name.upper()
        for asset_class, keywords in self.ASSET_CLASS_KEYWORDS.items():
            for keyword in keywords:
                if keyword.upper() in name_upper:
                    return asset_class
        return '기타'

    def get_etf_accumulation_signals(self, top_n: int = 15) -> pd.DataFrame:
        """ETF 매집(수급) 신호 분석.

        분석 기준:
        - 거래량 증가 추세 (최근 5일 vs 이전 5일)
        - 가격 상승 + 거래량 증가 = 강한 매집 신호
        - 가격 하락 + 거래량 증가 = 세력 매집 가능성
        """
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")

            # 날짜 범위 설정
            start_date = (today_dt - timedelta(days=20)).strftime("%Y%m%d")

            records = []
            for ticker, name, asset_class in self.POPULAR_PENSION_ETFS:
                try:
                    # 최근 20일 OHLCV 조회
                    ohlcv = krx.get_etf_ohlcv_by_date(start_date, trd_date, ticker)
                    if ohlcv.empty or len(ohlcv) < 10:
                        continue

                    # 최근 데이터
                    recent = ohlcv.tail(5)
                    prev = ohlcv.iloc[-10:-5] if len(ohlcv) >= 10 else ohlcv.head(5)

                    current_price = int(ohlcv.iloc[-1]['종가'])
                    price_5d_ago = int(ohlcv.iloc[-5]['종가']) if len(ohlcv) >= 5 else current_price

                    # 거래량 분석
                    recent_vol_avg = recent['거래량'].mean()
                    prev_vol_avg = prev['거래량'].mean() if len(prev) > 0 else recent_vol_avg

                    # 거래량 증가율
                    vol_change = 0
                    if prev_vol_avg > 0:
                        vol_change = ((recent_vol_avg - prev_vol_avg) / prev_vol_avg) * 100

                    # 가격 변화율
                    price_change = 0
                    if price_5d_ago > 0:
                        price_change = ((current_price - price_5d_ago) / price_5d_ago) * 100

                    # 매집 점수 계산
                    accumulation_score = 0
                    signals = []

                    # 거래량 증가 (가중치 40%)
                    if vol_change > 50:
                        accumulation_score += 40
                        signals.append("🔥거래량급증")
                    elif vol_change > 20:
                        accumulation_score += 25
                        signals.append("📈거래량증가")
                    elif vol_change > 0:
                        accumulation_score += 10

                    # 가격 상승 + 거래량 증가 (시너지 20%)
                    if price_change > 0 and vol_change > 20:
                        accumulation_score += 20
                        signals.append("⭐강한매집")

                    # 가격 하락 + 거래량 증가 = 세력 매집 가능성 (15%)
                    if price_change < -2 and vol_change > 30:
                        accumulation_score += 15
                        signals.append("🎯세력매집추정")

                    # 가격 상승률 (가중치 25%)
                    if price_change > 5:
                        accumulation_score += 25
                        signals.append("🚀급등")
                    elif price_change > 2:
                        accumulation_score += 15
                        signals.append("📊상승")
                    elif price_change > 0:
                        accumulation_score += 5

                    # 최소 점수 필터
                    if accumulation_score < 15:
                        continue

                    records.append({
                        'symbol': ticker,
                        'name': name,
                        'price': current_price,
                        'price_change_5d': round(price_change, 2),
                        'vol_change_pct': round(vol_change, 1),
                        'recent_vol_avg': int(recent_vol_avg),
                        'accumulation_score': accumulation_score,
                        'signals': ' '.join(signals) if signals else '관심',
                        'asset_class': asset_class,
                    })

                except Exception as e:
                    continue

            df = pd.DataFrame(records)
            if not df.empty:
                df = df.sort_values('accumulation_score', ascending=False).head(top_n)
                df['rank'] = range(1, len(df) + 1)

            return df

        except Exception as e:
            print(f"매집 신호 분석 오류: {e}")
            return pd.DataFrame()

    def get_etf_investor_trend(self, ticker: str, days: int = 10) -> dict:
        """개별 ETF 투자자별 매매 동향."""
        if not PYKRX_AVAILABLE:
            return {}

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")
            start_date = (today_dt - timedelta(days=days + 5)).strftime("%Y%m%d")

            # ETF 투자자별 거래실적
            df = krx.get_etf_portfolio_deposit_file(trd_date, ticker)

            # OHLCV로 거래량 추세 확인
            ohlcv = krx.get_etf_ohlcv_by_date(start_date, trd_date, ticker)

            result = {
                'ticker': ticker,
                'date': trd_date,
            }

            if not ohlcv.empty:
                recent_5d = ohlcv.tail(5)
                prev_5d = ohlcv.iloc[-10:-5] if len(ohlcv) >= 10 else ohlcv.head(5)

                result['current_price'] = int(ohlcv.iloc[-1]['종가'])
                result['volume_5d_avg'] = int(recent_5d['거래량'].mean())
                result['volume_prev_5d_avg'] = int(prev_5d['거래량'].mean()) if len(prev_5d) > 0 else 0
                result['volume_trend'] = 'up' if result['volume_5d_avg'] > result['volume_prev_5d_avg'] else 'down'

            return result

        except Exception as e:
            print(f"투자자 동향 조회 오류: {e}")
            return {}


class SectorLeaderData:
    """테마/섹터별 대장주 데이터."""

    # 테마별 대장주 (1등, 2등, 3등)
    SECTOR_LEADERS = {
        '반도체': [
            ('005930', '삼성전자', '메모리/파운드리 세계 1위'),
            ('000660', 'SK하이닉스', 'HBM 세계 1위'),
            ('042700', '한미반도체', 'HBM 장비 대장주'),
        ],
        '2차전지': [
            ('373220', 'LG에너지솔루션', '배터리 세계 2위'),
            ('006400', '삼성SDI', '배터리 세계 5위'),
            ('051910', 'LG화학', '양극재 대장주'),
        ],
        'AI': [
            ('005930', '삼성전자', 'AI반도체/HBM'),
            ('000660', 'SK하이닉스', 'HBM AI메모리'),
            ('035420', 'NAVER', 'AI 하이퍼클로바X'),
        ],
        '바이오': [
            ('207940', '삼성바이오로직스', '바이오CMO 세계 1위'),
            ('068270', '셀트리온', '바이오시밀러 강자'),
            ('326030', 'SK바이오팜', '뇌질환 신약'),
        ],
        '자동차': [
            ('005380', '현대차', '국내 1위 완성차'),
            ('000270', '기아', '국내 2위 완성차'),
            ('012330', '현대모비스', '자동차 부품 대장'),
        ],
        '조선': [
            ('009540', 'HD한국조선해양', '조선 지주사'),
            ('329180', 'HD현대중공업', '조선 세계 1위'),
            ('010140', '삼성중공업', 'LNG선 강자'),
        ],
        '방산': [
            ('012450', '한화에어로스페이스', '항공우주 대장'),
            ('047810', '한국항공우주', 'KF-21 개발'),
            ('079550', 'LIG넥스원', '미사일 대장'),
        ],
        '엔터': [
            ('352820', '하이브', 'BTS 소속사'),
            ('041510', 'SM', 'SM엔터테인먼트'),
            ('035900', 'JYP Ent.', 'JYP엔터테인먼트'),
        ],
        '게임': [
            ('036570', 'NCsoft', '리니지 시리즈'),
            ('263750', '펄어비스', '검은사막'),
            ('112040', '위메이드', '미르 시리즈'),
        ],
        '인터넷': [
            ('035420', 'NAVER', '검색 1위'),
            ('035720', '카카오', '메신저 1위'),
            ('251270', '넷마블', '모바일게임'),
        ],
        '금융': [
            ('055550', '신한지주', '금융지주 1위'),
            ('105560', 'KB금융', '금융지주 2위'),
            ('086790', '하나금융지주', '금융지주 3위'),
        ],
        '철강': [
            ('005490', 'POSCO홀딩스', '철강 대장주'),
            ('004020', '현대제철', '철강 2위'),
            ('001230', '동국제강', '철강 3위'),
        ],
        '화학': [
            ('051910', 'LG화학', '화학 대장주'),
            ('011170', '롯데케미칼', '석유화학'),
            ('010950', 'S-Oil', '정유/화학'),
        ],
        '건설': [
            ('000720', '현대건설', '건설 대장주'),
            ('006360', 'GS건설', '건설 2위'),
            ('047040', '대우건설', '건설 3위'),
        ],
        '유틸리티': [
            ('015760', '한국전력', '전력 독점'),
            ('036460', '한국가스공사', '가스 공급'),
            ('034020', '두산에너빌리티', '발전설비'),
        ],
        '통신': [
            ('017670', 'SK텔레콤', '통신 1위'),
            ('030200', 'KT', '통신 2위'),
            ('032640', 'LG유플러스', '통신 3위'),
        ],
        '로봇': [
            ('012450', '한화에어로스페이스', '로봇/자동화'),
            ('090460', '비에이치', '로봇부품'),
            ('108860', '셀바스AI', 'AI로봇'),
        ],
    }

    @classmethod
    def get_leaders(cls, sector: str) -> list:
        """테마별 대장주 조회."""
        return cls.SECTOR_LEADERS.get(sector, [])

    @classmethod
    def get_all_sectors(cls) -> list:
        """전체 섹터 목록."""
        return list(cls.SECTOR_LEADERS.keys())


class NewsScraper:
    """뉴스 및 시황 스크래퍼."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_market_news(self, keyword: str = "증시", limit: int = 10) -> list:
        """네이버 뉴스 검색."""
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1"
            resp = self.session.get(url, timeout=10)
            resp.encoding = 'utf-8'

            soup = BeautifulSoup(resp.text, 'html.parser')

            news_items = []
            for item in soup.select('.news_tit')[:limit]:
                title = item.get_text(strip=True)
                link = item.get('href', '')
                news_items.append({'title': title, 'url': link})

            return news_items
        except Exception as e:
            print(f"뉴스 조회 오류: {e}")
            return []

    def get_theme_news(self, theme: str, limit: int = 5) -> list:
        """테마별 관련 뉴스 검색."""
        keywords = {
            '반도체': '반도체 주식',
            '2차전지': '2차전지 배터리 주식',
            'AI': 'AI 인공지능 주식',
            '바이오': '바이오 제약 주식',
            '자동차': '자동차 전기차 주식',
            '조선': '조선 LNG선',
            '방산': '방산 방위산업',
            '로봇': '로봇 자동화',
        }
        search_term = keywords.get(theme, f"{theme} 주식")
        return self.get_market_news(search_term, limit)

    def get_trending_themes(self) -> list:
        """인기 테마/섹터 조회."""
        try:
            url = "https://finance.naver.com/sise/theme.naver"
            resp = self.session.get(url, timeout=10)
            resp.encoding = 'euc-kr'

            soup = BeautifulSoup(resp.text, 'html.parser')

            themes = []
            for row in soup.select('table.type_1 tr')[2:15]:
                cols = row.select('td')
                if len(cols) >= 4:
                    try:
                        name_tag = cols[0].select_one('a')
                        if name_tag:
                            name = name_tag.get_text(strip=True)
                            href = name_tag.get('href', '')
                            # 테마 번호 추출
                            theme_no = ''
                            if 'no=' in href:
                                theme_no = href.split('no=')[-1].split('&')[0]
                        else:
                            name = cols[0].get_text(strip=True)
                            theme_no = ''

                        change = cols[1].get_text(strip=True)
                        if name and '%' in change:
                            themes.append({
                                'name': name,
                                'change': change,
                                'theme_no': theme_no
                            })
                    except:
                        continue

            return themes
        except Exception as e:
            print(f"테마 조회 오류: {e}")
            return []

    def get_theme_stocks(self, theme_no: str, limit: int = 5) -> list:
        """테마별 관련 종목 조회."""
        if not theme_no:
            return []

        try:
            url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_no}"
            resp = self.session.get(url, timeout=10)
            resp.encoding = 'euc-kr'

            soup = BeautifulSoup(resp.text, 'html.parser')

            stocks = []
            # 종목 테이블 찾기
            table = soup.select_one('table.type_5')
            if not table:
                return []

            for row in table.select('tr')[2:]:  # 헤더 스킵
                cols = row.select('td')
                if len(cols) >= 6:
                    try:
                        name_tag = cols[0].select_one('a')
                        if not name_tag:
                            continue

                        name = name_tag.get_text(strip=True)
                        href = name_tag.get('href', '')
                        # 종목코드 추출
                        code = ''
                        if 'code=' in href:
                            code = href.split('code=')[-1].split('&')[0]

                        price = cols[1].get_text(strip=True).replace(',', '')
                        change_pct = cols[3].get_text(strip=True)

                        if name and code:
                            stocks.append({
                                'code': code,
                                'name': name,
                                'price': price,
                                'change': change_pct
                            })

                        if len(stocks) >= limit:
                            break
                    except:
                        continue

            return stocks
        except Exception as e:
            print(f"테마 종목 조회 오류: {e}")
            return []


class AssetAllocationAdvisor:
    """자산배분 추천."""

    ALLOCATION_TEMPLATES = {
        'aggressive': {
            '국내주식': 30,
            '미국주식': 40,
            '신흥국': 10,
            '채권': 10,
            '원자재': 10,
        },
        'moderate': {
            '국내주식': 25,
            '미국주식': 30,
            '신흥국': 5,
            '채권': 30,
            '원자재': 10,
        },
        'conservative': {
            '국내주식': 15,
            '미국주식': 20,
            '신흥국': 0,
            '채권': 55,
            '원자재': 10,
        },
    }

    def get_recommended_allocation(self, risk_level: str = 'moderate') -> dict:
        """리스크 수준별 자산배분."""
        return self.ALLOCATION_TEMPLATES.get(risk_level, self.ALLOCATION_TEMPLATES['moderate'])


# CLI 테스트
if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n=== ETF 스크래퍼 테스트 ===\n")

    etf_scraper = ETFScraper()

    print("[연금저축 ETF TOP 10]")
    pension_etfs = etf_scraper.get_pension_etfs(10)
    if not pension_etfs.empty:
        for _, row in pension_etfs.iterrows():
            print(f"{row['rank']:2}. {row['name'][:25]:25} | {row['return_1m']:+.1f}% | {row['asset_class']}")
    else:
        print("데이터 없음")

    print("\n[테마]")
    news = NewsScraper()
    themes = news.get_trending_themes()
    for t in themes[:5]:
        print(f"  - {t['name']}: {t['change']}")
