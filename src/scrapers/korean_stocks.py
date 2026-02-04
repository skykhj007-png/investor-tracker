"""Korean stocks scraper - using pykrx for KRX data."""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import requests
from bs4 import BeautifulSoup
import re

try:
    from pykrx import stock as krx
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("Warning: pykrx not installed. Run: pip install pykrx")


def get_recent_trading_date() -> str:
    """Get most recent trading date (skip weekends)."""
    today = datetime.now()

    # If before market close, use yesterday
    if today.hour < 18:
        today = today - timedelta(days=1)

    # Skip weekends
    while today.weekday() >= 5:
        today = today - timedelta(days=1)

    return today.strftime("%Y%m%d")


class KrxDataScraper:
    """KRX data scraper using pykrx library."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_foreign_net_buying(self, top_n: int = 30) -> pd.DataFrame:
        """외국인 순매수 상위 종목."""
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()
            df = krx.get_market_net_purchases_of_equities_by_ticker(
                trd_date, trd_date, "KOSPI", "외국인"
            )

            if df.empty:
                return pd.DataFrame()

            # Sort by net purchase amount
            df = df.sort_values("순매수거래대금", ascending=False).head(top_n)
            df = df.reset_index()

            # Rename columns
            result = pd.DataFrame({
                'rank': range(1, len(df) + 1),
                'symbol': df['티커'],
                'name': df['종목명'],
                'buy_volume': df['매수거래량'],
                'sell_volume': df['매도거래량'],
                'net_volume': df['매수거래량'] - df['매도거래량'],
                'net_amount': df['순매수거래대금'],
            })

            return result

        except Exception as e:
            print(f"외국인 데이터 오류: {e}")
            return pd.DataFrame()

    def get_institution_net_buying(self, top_n: int = 30) -> pd.DataFrame:
        """기관 순매수 상위 종목."""
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()
            df = krx.get_market_net_purchases_of_equities_by_ticker(
                trd_date, trd_date, "KOSPI", "기관합계"
            )

            if df.empty:
                return pd.DataFrame()

            # Sort by net purchase amount
            df = df.sort_values("순매수거래대금", ascending=False).head(top_n)
            df = df.reset_index()

            result = pd.DataFrame({
                'rank': range(1, len(df) + 1),
                'symbol': df['티커'],
                'name': df['종목명'],
                'buy_volume': df['매수거래량'],
                'sell_volume': df['매도거래량'],
                'net_volume': df['매수거래량'] - df['매도거래량'],
                'net_amount': df['순매수거래대금'],
            })

            return result

        except Exception as e:
            print(f"기관 데이터 오류: {e}")
            return pd.DataFrame()

    def get_market_cap_top(self, market: str = "KOSPI", top_n: int = 30) -> pd.DataFrame:
        """시가총액 상위 종목."""
        if not PYKRX_AVAILABLE:
            return self._get_market_cap_from_naver(market, top_n)

        try:
            trd_date = get_recent_trading_date()
            df = krx.get_market_cap_by_ticker(trd_date, market=market)

            if df.empty:
                return pd.DataFrame()

            df = df.sort_values("시가총액", ascending=False).head(top_n)
            df = df.reset_index()

            result = pd.DataFrame({
                'rank': range(1, len(df) + 1),
                'symbol': df['티커'],
                'name': [krx.get_market_ticker_name(t) for t in df['티커']],
                'close': df['종가'],
                'market_cap': df['시가총액'],
                'volume': df['거래량'],
            })

            return result

        except Exception as e:
            print(f"시총 데이터 오류: {e}")
            return self._get_market_cap_from_naver(market, top_n)

    def _get_market_cap_from_naver(self, market: str, top_n: int) -> pd.DataFrame:
        """네이버 금융에서 시총 상위 스크래핑 (백업)."""
        try:
            sosok = "0" if market.upper() == "KOSPI" else "1"
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}"

            resp = self.session.get(url, timeout=30)
            resp.encoding = 'euc-kr'

            from io import StringIO
            dfs = pd.read_html(StringIO(resp.text))

            for df in dfs:
                if len(df) > 10 and 'N' in df.columns:
                    df = df.dropna(subset=['N'])
                    df = df[df['N'].apply(lambda x: str(x).replace('.0', '').isdigit())]

                    records = []
                    for i, row in df.head(top_n).iterrows():
                        records.append({
                            'rank': int(float(row['N'])),
                            'symbol': '',
                            'name': row['종목명'] if '종목명' in row else '',
                            'close': row['현재가'] if '현재가' in row else 0,
                            'market_cap': row['시가총액'] if '시가총액' in row else 0,
                            'volume': 0,
                        })

                    return pd.DataFrame(records)

            return pd.DataFrame()

        except Exception as e:
            print(f"네이버 시총 스크래핑 오류: {e}")
            return pd.DataFrame()

    def get_stock_price(self, symbol: str) -> dict:
        """개별 종목 현재가 조회."""
        if not PYKRX_AVAILABLE:
            return {}

        try:
            trd_date = get_recent_trading_date()
            df = krx.get_market_ohlcv_by_date(
                trd_date, trd_date, symbol
            )

            if df.empty:
                return {}

            row = df.iloc[0]
            name = krx.get_market_ticker_name(symbol)

            return {
                'symbol': symbol,
                'name': name,
                'close': row['종가'],
                'open': row['시가'],
                'high': row['고가'],
                'low': row['저가'],
                'volume': row['거래량'],
                'change': row['등락률'] if '등락률' in row else 0,
            }

        except Exception as e:
            print(f"종목 조회 오류: {e}")
            return {}

    def search_stock(self, query: str) -> pd.DataFrame:
        """종목 검색."""
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()

            # Get all tickers
            kospi = krx.get_market_ticker_list(trd_date, market="KOSPI")
            kosdaq = krx.get_market_ticker_list(trd_date, market="KOSDAQ")

            results = []
            for ticker in kospi + kosdaq:
                name = krx.get_market_ticker_name(ticker)
                if query.upper() in ticker or query in name:
                    results.append({
                        'symbol': ticker,
                        'name': name,
                        'market': 'KOSPI' if ticker in kospi else 'KOSDAQ',
                    })

                if len(results) >= 20:
                    break

            return pd.DataFrame(results)

        except Exception as e:
            print(f"검색 오류: {e}")
            return pd.DataFrame()

    def get_short_volume_top(self, market: str = "KOSPI", top_n: int = 30) -> pd.DataFrame:
        """공매도 거래량 상위 종목."""
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()

            # 공매도 거래량 Top 50
            df = krx.get_shorting_volume_top50(trd_date, market)

            if df.empty:
                # Fallback: 전체 종목에서 조회
                df = krx.get_shorting_volume_by_ticker(trd_date, market)
                if not df.empty:
                    df = df.sort_values('비중', ascending=False)

            if df.empty:
                return pd.DataFrame()

            df = df.reset_index()
            df = df.head(top_n)

            # 컬럼명 확인
            symbol_col = '티커' if '티커' in df.columns else df.columns[0]

            # 컬럼 매핑 (인코딩 문제로 위치 인덱스로 접근)
            # reset_index 후: [0]=ticker, [1]=순위, [2]=공매도거래대금, [3]=총거래대금, [4]=공매도비중, ...
            result = pd.DataFrame({
                'rank': df.iloc[:, 1].values,  # 순위
                'symbol': df.iloc[:, 0].values,  # 티커
                'name': [krx.get_market_ticker_name(str(t)) for t in df.iloc[:, 0]],
                'short_amount': df.iloc[:, 2].values,  # 공매도거래대금
                'total_amount': df.iloc[:, 3].values,  # 총거래대금
                'short_ratio': df.iloc[:, 4].values,  # 공매도비중 (%)
            })

            return result

        except Exception as e:
            print(f"공매도 거래량 오류: {e}")
            return pd.DataFrame()

    def get_short_balance_top(self, market: str = "KOSPI", top_n: int = 30) -> pd.DataFrame:
        """공매도 잔고 상위 종목."""
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()

            # 공매도 잔고 Top 50
            df = krx.get_shorting_balance_top50(trd_date, market)

            if df.empty:
                return pd.DataFrame()

            df = df.reset_index()

            if '티커' in df.columns:
                symbol_col = '티커'
            elif 'index' in df.columns:
                symbol_col = 'index'
            else:
                symbol_col = df.columns[0]

            result = pd.DataFrame({
                'rank': range(1, min(len(df), top_n) + 1),
                'symbol': df[symbol_col].head(top_n),
                'name': [krx.get_market_ticker_name(t) for t in df[symbol_col].head(top_n)],
                'short_balance': df['공매도잔고'].head(top_n) if '공매도잔고' in df.columns else 0,
                'short_amount': df['공매도금액'].head(top_n) if '공매도금액' in df.columns else 0,
                'balance_ratio': df['비중'].head(top_n) if '비중' in df.columns else 0,
            })

            return result

        except Exception as e:
            print(f"공매도 잔고 오류: {e}")
            return pd.DataFrame()

    def get_fundamentals(self, market: str = "KOSPI") -> pd.DataFrame:
        """PER/PBR/배당수익률 등 펀더멘탈 지표 조회."""
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()
            df = krx.get_market_fundamental_by_ticker(trd_date, market=market)

            if df.empty:
                return pd.DataFrame()

            df = df.reset_index()
            df = df.rename(columns={
                '티커': 'symbol',
                'PER': 'per',
                'PBR': 'pbr',
                'EPS': 'eps',
                'BPS': 'bps',
                'DIV': 'div_yield',
            })

            return df

        except Exception as e:
            print(f"펀더멘탈 데이터 오류: {e}")
            return pd.DataFrame()

    def get_ohlcv(self, symbol: str, days: int = 40) -> pd.DataFrame:
        """개별 종목 OHLCV 조회 (RSI/MACD 계산용)."""
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")
            start_date = (today_dt - timedelta(days=days)).strftime("%Y%m%d")

            df = krx.get_market_ohlcv_by_date(start_date, trd_date, symbol)
            return df

        except Exception as e:
            print(f"OHLCV 조회 오류: {e}")
            return pd.DataFrame()

    def get_accumulation_signals(self, market: str = "KOSPI", top_n: int = 20) -> pd.DataFrame:
        """주식 매집 신호 분석 - 거래량 급증 + 외국인/기관 순매수 종목.

        분석 기준:
        - 거래량 증가 추세 (최근 5일 vs 이전 5일)
        - 가격 상승 + 거래량 증가 = 강한 매집 신호
        - 외국인/기관 순매수 + 거래량 증가 = 세력 매집
        """
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        try:
            trd_date = get_recent_trading_date()
            today_dt = datetime.strptime(trd_date, "%Y%m%d")
            start_date = (today_dt - timedelta(days=20)).strftime("%Y%m%d")

            # 시총 상위 100 종목 대상
            cap_df = krx.get_market_cap_by_ticker(trd_date, market)
            if cap_df.empty:
                return pd.DataFrame()

            cap_df = cap_df.sort_values('시가총액', ascending=False).head(100)
            target_tickers = cap_df.index.tolist()

            # 외국인 순매수 데이터
            foreign_df = self.get_foreign_net_buying(50)
            foreign_symbols = set(foreign_df['symbol'].tolist()) if not foreign_df.empty else set()

            # 기관 순매수 데이터
            inst_df = self.get_institution_net_buying(50)
            inst_symbols = set(inst_df['symbol'].tolist()) if not inst_df.empty else set()

            records = []
            for ticker in target_tickers[:50]:  # 상위 50개만 분석 (속도)
                try:
                    # 최근 20일 OHLCV 조회
                    ohlcv = krx.get_market_ohlcv_by_date(start_date, trd_date, ticker)
                    if ohlcv.empty or len(ohlcv) < 10:
                        continue

                    name = krx.get_market_ticker_name(ticker)

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

                    # 거래량 증가 (가중치 30%)
                    if vol_change > 100:
                        accumulation_score += 30
                        signals.append("🔥거래량폭증")
                    elif vol_change > 50:
                        accumulation_score += 25
                        signals.append("📈거래량급증")
                    elif vol_change > 20:
                        accumulation_score += 15
                        signals.append("📊거래량증가")

                    # 외국인 순매수 (가중치 25%)
                    if ticker in foreign_symbols:
                        accumulation_score += 25
                        signals.append("🌍외국인매수")

                    # 기관 순매수 (가중치 25%)
                    if ticker in inst_symbols:
                        accumulation_score += 25
                        signals.append("🏛️기관매수")

                    # 가격 상승 + 거래량 증가 시너지 (15%)
                    if price_change > 0 and vol_change > 20:
                        accumulation_score += 15
                        signals.append("⭐강한매집")

                    # 가격 상승률 (가중치 20%)
                    if price_change > 10:
                        accumulation_score += 20
                        signals.append("🚀급등")
                    elif price_change > 5:
                        accumulation_score += 15
                        signals.append("📈상승")
                    elif price_change > 2:
                        accumulation_score += 10

                    # 최소 점수 필터
                    if accumulation_score < 20:
                        continue

                    # 시가총액
                    market_cap = cap_df.loc[ticker, '시가총액'] if ticker in cap_df.index else 0

                    records.append({
                        'symbol': ticker,
                        'name': name,
                        'price': current_price,
                        'price_change_5d': round(price_change, 2),
                        'vol_change_pct': round(vol_change, 1),
                        'market_cap': market_cap,
                        'accumulation_score': accumulation_score,
                        'signals': ' '.join(signals) if signals else '관심',
                        'foreign_buy': ticker in foreign_symbols,
                        'inst_buy': ticker in inst_symbols,
                    })

                except Exception as e:
                    continue

            df = pd.DataFrame(records)
            if not df.empty:
                df = df.sort_values('accumulation_score', ascending=False).head(top_n)
                df['rank'] = range(1, len(df) + 1)
                df['market_cap_조'] = (df['market_cap'] / 1e12).round(1)

            return df

        except Exception as e:
            print(f"매집 신호 분석 오류: {e}")
            return pd.DataFrame()


class DartScraper:
    """DART 전자공시 스크래퍼."""

    BASE_URL = "https://dart.fss.or.kr"

    REPORT_TYPES = {
        'major_holdings': 'B001',   # 대량보유상황보고서
        'annual': 'A001',           # 사업보고서
        'semi_annual': 'A002',      # 반기보고서
        'quarterly': 'A003',        # 분기보고서
        'major_events': 'C',        # 주요사항보고서
        'fair_disclosure': 'D',     # 공정공시
        'other': 'E',               # 기타공시
        'audit': 'F',               # 외부감사관련
    }

    REPORT_TYPE_LABELS = {
        'B001': '대량보유',
        'A001': '사업보고서',
        'A002': '반기보고서',
        'A003': '분기보고서',
        'C': '주요사항',
        'D': '공정공시',
        'E': '기타공시',
        'F': '외부감사',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _search_disclosures(self, days: int = 7, report_type: str = '',
                             company_name: str = '', max_results: int = 50) -> pd.DataFrame:
        """DART 공시 범용 검색."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        search_url = f"{self.BASE_URL}/dsab001/search.ax"

        data = {
            'currentPage': 1,
            'maxResults': max_results,
            'maxLinks': 10,
            'sort': 'date',
            'series': 'desc',
            'textCrpNm': company_name,
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d'),
            'reportType': report_type,
        }

        try:
            resp = self.session.post(search_url, data=data, timeout=30)

            if resp.headers.get('content-type', '').startswith('application/json'):
                result = resp.json()
                records = []

                for item in result.get('list', []):
                    report_nm = item.get('report_nm', '')
                    type_label = self.REPORT_TYPE_LABELS.get(report_type, '')
                    if not type_label and report_nm:
                        for code, label in self.REPORT_TYPE_LABELS.items():
                            if label in report_nm:
                                type_label = label
                                break
                        if not type_label:
                            type_label = report_nm.split('(')[0][:10] if '(' in report_nm else report_nm[:10]

                    records.append({
                        'date': item.get('rcept_dt', ''),
                        'company': item.get('corp_name', ''),
                        'report_type': type_label,
                        'title': report_nm,
                        'url': f"{self.BASE_URL}/dsaf001/main.do?rcpNo={item.get('rcept_no', '')}",
                    })

                return pd.DataFrame(records)

            return pd.DataFrame(columns=['date', 'company', 'report_type', 'title', 'url'])

        except Exception as e:
            print(f"DART 조회 오류: {e}")
            return pd.DataFrame(columns=['date', 'company', 'report_type', 'title', 'url'])

    def get_major_holdings(self, days: int = 7) -> pd.DataFrame:
        """최근 대량보유 공시 조회 (5% 이상 지분 변동)."""
        return self._search_disclosures(days=days, report_type='B001')

    def get_recent_disclosures(self, days: int = 7, report_types: list = None) -> pd.DataFrame:
        """최근 주요 공시 조회. report_types가 None이면 대량보유+주요사항+공정공시."""
        if report_types is None:
            report_types = ['B001', 'C', 'D']

        all_records = []
        for rt in report_types:
            df = self._search_disclosures(days=days, report_type=rt, max_results=30)
            if not df.empty:
                all_records.append(df)

        if not all_records:
            return pd.DataFrame(columns=['date', 'company', 'report_type', 'title', 'url'])

        combined = pd.concat(all_records, ignore_index=True)
        combined = combined.sort_values('date', ascending=False).reset_index(drop=True)
        return combined

    def search_company_disclosures(self, company_name: str, days: int = 30) -> pd.DataFrame:
        """특정 기업의 최근 공시 검색."""
        return self._search_disclosures(days=days, company_name=company_name, max_results=30)

    def get_disclosures_for_stocks(self, stock_names: list, days: int = 14) -> pd.DataFrame:
        """추천 종목들의 최근 공시 일괄 조회."""
        import time

        all_records = []
        for name in stock_names[:10]:
            df = self.search_company_disclosures(name, days=days)
            if not df.empty:
                all_records.append(df)
            time.sleep(0.3)

        if not all_records:
            return pd.DataFrame(columns=['date', 'company', 'report_type', 'title', 'url'])

        combined = pd.concat(all_records, ignore_index=True)
        combined = combined.sort_values('date', ascending=False).reset_index(drop=True)
        return combined


class CreditBalanceScraper:
    """신용잔고 스크래퍼 (금융투자협회 데이터)."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_credit_balance_top(self, top_n: int = 30) -> pd.DataFrame:
        """신용잔고 상위 종목 (네이버 금융에서 스크래핑)."""
        try:
            # 네이버 금융 신용잔고 페이지
            url = "https://finance.naver.com/sise/sise_credit.naver"

            resp = self.session.get(url, timeout=30)
            resp.encoding = 'euc-kr'

            from io import StringIO
            dfs = pd.read_html(StringIO(resp.text))

            for df in dfs:
                if len(df) > 10 and len(df.columns) >= 5:
                    df = df.dropna(how='all')
                    # 숫자 행만 선택
                    df = df[df.iloc[:, 0].apply(lambda x: str(x).replace('.0', '').isdigit() if pd.notna(x) else False)]

                    if len(df) < 5:
                        continue

                    records = []
                    for idx, row in df.head(top_n).iterrows():
                        try:
                            records.append({
                                'rank': int(float(row.iloc[0])),
                                'name': str(row.iloc[1]) if pd.notna(row.iloc[1]) else '',
                                'credit_balance': self._parse_number(str(row.iloc[2])) if len(row) > 2 else 0,
                                'credit_change': self._parse_number(str(row.iloc[3])) if len(row) > 3 else 0,
                                'credit_ratio': float(str(row.iloc[4]).replace('%', '')) if len(row) > 4 and pd.notna(row.iloc[4]) else 0,
                            })
                        except:
                            continue

                    if records:
                        return pd.DataFrame(records)

            return pd.DataFrame()

        except Exception as e:
            print(f"신용잔고 스크래핑 오류: {e}")
            return pd.DataFrame()

    def _parse_number(self, text: str) -> int:
        """숫자 문자열 파싱."""
        if not text or text == 'nan':
            return 0
        text = re.sub(r'[^\d\-]', '', str(text))
        try:
            return int(text) if text else 0
        except ValueError:
            return 0


class KoreanStocksScraper:
    """통합 한국 주식 스크래퍼."""

    def __init__(self):
        self.krx = KrxDataScraper()
        self.dart = DartScraper()
        self.credit = CreditBalanceScraper()

    def get_foreign_buying(self, top_n: int = 30) -> pd.DataFrame:
        """외국인 순매수 상위."""
        return self.krx.get_foreign_net_buying(top_n)

    def get_institution_buying(self, top_n: int = 30) -> pd.DataFrame:
        """기관 순매수 상위."""
        return self.krx.get_institution_net_buying(top_n)

    def get_market_cap_top(self, market: str = "KOSPI", top_n: int = 30) -> pd.DataFrame:
        """시총 상위 종목."""
        return self.krx.get_market_cap_top(market, top_n)

    def get_stock_price(self, symbol: str) -> dict:
        """종목 현재가."""
        return self.krx.get_stock_price(symbol)

    def search_stock(self, query: str) -> pd.DataFrame:
        """종목 검색."""
        return self.krx.search_stock(query)

    def get_major_holdings(self, days: int = 7) -> pd.DataFrame:
        """DART 대량보유 공시."""
        return self.dart.get_major_holdings(days)

    def get_short_volume(self, market: str = "KOSPI", top_n: int = 30) -> pd.DataFrame:
        """공매도 거래량 상위."""
        return self.krx.get_short_volume_top(market, top_n)

    def get_short_balance(self, market: str = "KOSPI", top_n: int = 30) -> pd.DataFrame:
        """공매도 잔고 상위."""
        return self.krx.get_short_balance_top(market, top_n)

    def get_credit_balance(self, top_n: int = 30) -> pd.DataFrame:
        """신용잔고 상위."""
        return self.credit.get_credit_balance_top(top_n)

    def get_fundamentals(self, market: str = "KOSPI") -> pd.DataFrame:
        """PER/PBR/배당수익률 펀더멘탈 지표."""
        return self.krx.get_fundamentals(market)

    def get_ohlcv(self, symbol: str, days: int = 40) -> pd.DataFrame:
        """개별 종목 OHLCV 조회."""
        return self.krx.get_ohlcv(symbol, days)

    def get_accumulation_signals(self, market: str = "KOSPI", top_n: int = 20) -> pd.DataFrame:
        """주식 매집 신호 분석."""
        return self.krx.get_accumulation_signals(market, top_n)

    def get_recent_disclosures(self, days: int = 7, report_types: list = None) -> pd.DataFrame:
        """최근 주요 공시."""
        return self.dart.get_recent_disclosures(days, report_types)

    def search_company_disclosures(self, company_name: str, days: int = 30) -> pd.DataFrame:
        """기업별 공시 검색."""
        return self.dart.search_company_disclosures(company_name, days)

    def get_disclosures_for_stocks(self, stock_names: list, days: int = 14) -> pd.DataFrame:
        """추천 종목 공시 일괄 조회."""
        return self.dart.get_disclosures_for_stocks(stock_names, days)


# CLI 테스트
if __name__ == "__main__":
    scraper = KoreanStocksScraper()

    print(f"\n거래일: {get_recent_trading_date()}")

    print("\n=== 외국인 순매수 TOP 10 ===")
    foreign = scraper.get_foreign_buying(10)
    if not foreign.empty:
        # Format large numbers
        foreign['net_amount_억'] = (foreign['net_amount'] / 100000000).round(0).astype(int)
        print(foreign[['rank', 'symbol', 'name', 'net_amount_억']].to_string(index=False))
    else:
        print("데이터 없음")

    print("\n=== 기관 순매수 TOP 10 ===")
    inst = scraper.get_institution_buying(10)
    if not inst.empty:
        inst['net_amount_억'] = (inst['net_amount'] / 100000000).round(0).astype(int)
        print(inst[['rank', 'symbol', 'name', 'net_amount_억']].to_string(index=False))
    else:
        print("데이터 없음")

    print("\n=== 시총 상위 TOP 10 ===")
    cap = scraper.get_market_cap_top("KOSPI", 10)
    if not cap.empty:
        cap['market_cap_조'] = (cap['market_cap'] / 1000000000000).round(1)
        print(cap[['rank', 'symbol', 'name', 'close', 'market_cap_조']].to_string(index=False))
    else:
        print("데이터 없음")

    print("\n=== DART 대량보유 공시 ===")
    holdings = scraper.get_major_holdings(days=30)
    if not holdings.empty:
        print(holdings.head(10).to_string(index=False))
    else:
        print("데이터 없음")
