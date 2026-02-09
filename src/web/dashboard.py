"""Streamlit web dashboard for Investor Tracker."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ── 지연 로딩 (Lazy Import) - 시작 속도 최적화 ──
# Scraper/Analyzer 모듈은 실제 사용 시에만 import됨 (pykrx 등 무거운 의존성)

@st.cache_resource
def get_dataroma_scraper():
    """DataromaScraper 지연 로딩."""
    from src.scrapers.dataroma import DataromaScraper
    return DataromaScraper()

@st.cache_resource
def get_kr_scraper():
    """KoreanStocksScraper 지연 로딩."""
    from src.scrapers.korean_stocks import KoreanStocksScraper
    return KoreanStocksScraper()

@st.cache_resource
def get_crypto_scraper():
    """CryptoScraper 지연 로딩."""
    from src.scrapers.crypto import CryptoScraper
    return CryptoScraper()

@st.cache_resource
def get_overlap_analyzer():
    """OverlapAnalyzer 지연 로딩."""
    from src.analyzers.overlap import OverlapAnalyzer
    return OverlapAnalyzer()

@st.cache_resource
def get_changes_analyzer():
    """ChangesAnalyzer 지연 로딩."""
    from src.analyzers.changes import ChangesAnalyzer
    return ChangesAnalyzer()

@st.cache_resource
def get_recommender():
    """KoreanStockRecommender 지연 로딩."""
    from src.analyzers.korean_recommender import KoreanStockRecommender
    return KoreanStockRecommender()

@st.cache_resource
def get_pension_recommender():
    """PensionRecommender 지연 로딩."""
    from src.analyzers.pension_recommender import PensionRecommender
    return PensionRecommender()

@st.cache_resource
def get_crypto_recommender():
    """CryptoRecommender 지연 로딩."""
    from src.analyzers.crypto_recommender import CryptoRecommender
    return CryptoRecommender()

@st.cache_resource
def get_us_recommender():
    """USStockRecommender 지연 로딩."""
    from src.analyzers.us_recommender import USStockRecommender
    return USStockRecommender()

@st.cache_resource
def get_database():
    """Database 지연 로딩."""
    from src.storage.database import Database
    db = Database()
    db.init_db()
    return db

# Page config
st.set_page_config(
    page_title="Investor Tracker",
    page_icon="📊",
    layout="wide",
)

# Auto refresh every 5 minutes (300 seconds) + 모바일 viewport 설정
st.markdown(
    '''<meta http-equiv="refresh" content="300">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">''',
    unsafe_allow_html=True,
)

# 모바일 사이드바 토글 버튼 강조 CSS
st.markdown("""
<style>
/* 사이드바 접힌 상태: 열기 버튼 강조 */
[data-testid="collapsedControl"] {
    background-color: #FF4B4B !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    box-shadow: 0 2px 8px rgba(255, 75, 75, 0.4) !important;
}
[data-testid="collapsedControl"] svg {
    width: 24px !important;
    height: 24px !important;
    color: white !important;
    stroke: white !important;
}

/* 사이드바 열린 상태: 닫기 버튼 */
[data-testid="stSidebarCollapseButton"] button {
    background-color: rgba(255, 75, 75, 0.8) !important;
    border-radius: 8px !important;
    color: white !important;
}
[data-testid="stSidebarCollapseButton"] button svg {
    color: white !important;
    stroke: white !important;
}

/* 메뉴 버튼에 텍스트 추가 (모든 화면) */
[data-testid="collapsedControl"]::after {
    content: " 메뉴" !important;
    color: white !important;
    font-size: 14px !important;
    font-weight: bold !important;
    margin-left: 4px !important;
}

/* 모바일에서 메뉴 버튼 더 크게 */
@media (max-width: 768px) {
    [data-testid="collapsedControl"] {
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 999 !important;
        padding: 12px 16px !important;
        font-size: 18px !important;
    }
}

/* 로딩 스피너 중앙 강조 */
.stSpinner {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    min-height: 120px !important;
}
.stSpinner > div {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #FF4B4B !important;
}

/* ========== 모바일 최적화 스타일 ========== */
@media (max-width: 768px) {
    /* 메인 컨텐츠 영역 패딩 축소 */
    .main .block-container {
        padding: 1rem 0.5rem !important;
        max-width: 100% !important;
    }

    /* 제목 크기 조정 */
    h1 {
        font-size: 1.5rem !important;
        line-height: 1.3 !important;
    }
    h2 {
        font-size: 1.25rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
    }

    /* 메트릭 카드 컴팩트화 */
    [data-testid="stMetric"] {
        padding: 0.5rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.7rem !important;
    }

    /* 버튼 터치 친화적 크기 */
    .stButton > button {
        padding: 0.6rem 1rem !important;
        font-size: 0.9rem !important;
        min-height: 44px !important;
        width: 100% !important;
    }

    /* 테이블 가로 스크롤 */
    [data-testid="stDataFrame"],
    .stDataFrame {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    [data-testid="stDataFrame"] table {
        font-size: 0.75rem !important;
    }

    /* 탭 버튼 컴팩트화 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        flex-wrap: wrap !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 0.6rem !important;
        font-size: 0.75rem !important;
        flex: 1 1 auto !important;
        min-width: fit-content !important;
    }

    /* 셀렉트박스, 인풋 필드 */
    .stSelectbox, .stTextInput, .stNumberInput {
        font-size: 16px !important; /* iOS 확대 방지 */
    }

    /* 차트 높이 조정 */
    .js-plotly-plot {
        height: auto !important;
        min-height: 250px !important;
    }

    /* 컬럼 스택 (2열 이상 → 1열) */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* expander 컴팩트화 */
    .streamlit-expanderHeader {
        font-size: 0.9rem !important;
        padding: 0.5rem !important;
    }

    /* 마크다운 텍스트 */
    .stMarkdown p {
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
    }

    /* info/warning/error 박스 */
    .stAlert {
        padding: 0.5rem !important;
        font-size: 0.85rem !important;
    }
}

/* 중간 화면 (태블릿) */
@media (min-width: 769px) and (max-width: 1024px) {
    .main .block-container {
        padding: 1rem 1rem !important;
    }

    h1 {
        font-size: 1.75rem !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.6rem 0.8rem !important;
        font-size: 0.85rem !important;
    }
}

/* 터치 디바이스 호버 효과 제거 */
@media (hover: none) {
    .stButton > button:hover {
        transform: none !important;
        box-shadow: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── 캐시 래퍼 함수들 (로딩 속도 개선) ──────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def cached_investor_list():
    return get_dataroma_scraper().get_investor_list()

@st.cache_data(ttl=300, show_spinner=False)
def cached_grand_portfolio():
    return get_dataroma_scraper().get_grand_portfolio()

@st.cache_data(ttl=300, show_spinner=False)
def cached_portfolio(investor_id):
    return get_dataroma_scraper().get_portfolio(investor_id)

@st.cache_data(ttl=300, show_spinner=False)
def cached_foreign_buying(top_n):
    return get_kr_scraper().get_foreign_buying(top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_institution_buying(top_n):
    return get_kr_scraper().get_institution_buying(top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_market_cap_top(market, top_n):
    return get_kr_scraper().get_market_cap_top(market, top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_short_volume(market, top_n):
    return get_kr_scraper().get_short_volume(market, top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_recommendations(top_n):
    return get_recommender().get_recommendations(top_n=top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_dual_buying():
    return get_recommender().get_dual_buying_stocks()

@st.cache_data(ttl=300, show_spinner=False)
def cached_contrarian():
    return get_recommender().get_contrarian_picks()

@st.cache_data(ttl=300, show_spinner=False)
def cached_accumulation_signals(market, top_n):
    return get_recommender().get_accumulation_signals(market, top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_strong_buy(market, top_n):
    return get_recommender().get_strong_buy_candidates(market, top_n)

@st.cache_data(ttl=600, show_spinner=False)
def cached_recent_disclosures(days, report_types_tuple):
    report_types = list(report_types_tuple) if report_types_tuple else None
    return get_kr_scraper().get_recent_disclosures(days=days, report_types=report_types)

@st.cache_data(ttl=600, show_spinner=False)
def cached_company_disclosures(company_name, days):
    return get_kr_scraper().search_company_disclosures(company_name, days=days)

@st.cache_data(ttl=600, show_spinner=False)
def cached_disclosures_for_stocks(stock_names_tuple, days):
    return get_kr_scraper().get_disclosures_for_stocks(list(stock_names_tuple), days=days)

@st.cache_data(ttl=300, show_spinner=False)
def cached_top_coins(exchange, top_n):
    return get_crypto_scraper().get_top_coins(exchange, top_n)

@st.cache_data(ttl=180, show_spinner=False)
def cached_crypto_recommendations(exchange, top_n):
    """v3: entry/stop/target inline calculation"""
    recommender = get_crypto_recommender()
    result = recommender.get_recommendations(exchange, top_n)
    return result

@st.cache_data(ttl=300, show_spinner=False)
def cached_volume_surge(exchange, top_n):
    return get_crypto_recommender().get_volume_surge_coins(exchange, top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_movers(exchange, top_n):
    return get_crypto_scraper().get_movers(exchange, top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_quick_picks(top_n):
    return get_pension_recommender().get_quick_picks(top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_pension_accumulation(top_n):
    return get_pension_recommender().get_accumulation_signals(top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_us_recommendations(top_n):
    return get_us_recommender().get_recommendations(top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_us_new_buys(top_n):
    return get_us_recommender().get_new_buys(top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_us_high_conviction(top_n):
    return get_us_recommender().get_high_conviction(top_n)

@st.cache_data(ttl=300, show_spinner=False)
def cached_us_stock_analysis(symbol):
    """미국 주식 분석 결과 캐시 (5분)."""
    return get_us_recommender().analyze_stock(symbol)

@st.cache_resource(show_spinner=False)
def cached_kr_ticker_list():
    """전체 국내 주식 티커 목록 캐시 (세션 영구) - 검색 속도 향상용."""
    try:
        from pykrx import stock as krx
        from datetime import datetime, timedelta

        # 최근 거래일 찾기
        trd_date = None
        for i in range(7):
            test_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            try:
                test_list = krx.get_market_ticker_list(test_date, market="KOSPI")
                if test_list:
                    trd_date = test_date
                    break
            except:
                continue

        if not trd_date:
            return pd.DataFrame()

        # 시가총액 데이터로 한 번에 조회 (훨씬 빠름)
        kospi_cap = krx.get_market_cap_by_ticker(trd_date, market="KOSPI")
        kosdaq_cap = krx.get_market_cap_by_ticker(trd_date, market="KOSDAQ")

        ticker_data = []

        # KOSPI - 인덱스가 티커 코드
        for ticker in kospi_cap.index:
            name = krx.get_market_ticker_name(ticker)
            ticker_data.append({'symbol': ticker, 'name': name, 'market': 'KOSPI'})

        # KOSDAQ
        for ticker in kosdaq_cap.index:
            name = krx.get_market_ticker_name(ticker)
            ticker_data.append({'symbol': ticker, 'name': name, 'market': 'KOSDAQ'})

        return pd.DataFrame(ticker_data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def cached_kr_search_stock(query):
    """국내 주식 검색 - 코드 직접 검색 우선 (빠름)."""
    from pykrx import stock as krx

    results = []
    query_clean = query.strip()

    # 1) 종목코드로 직접 검색 (6자리 숫자) - 즉시 응답
    if query_clean.isdigit() and len(query_clean) == 6:
        try:
            name = krx.get_market_ticker_name(query_clean)
            if name:
                return pd.DataFrame([{
                    'symbol': query_clean,
                    'name': name,
                    'market': 'KOSPI/KOSDAQ'
                }])
        except:
            pass

    # 2) 이름 검색 - 캐시된 전체 목록 사용
    all_tickers = cached_kr_ticker_list()
    if all_tickers.empty:
        return pd.DataFrame()

    query_upper = query_clean.upper()
    # 종목코드나 종목명에 검색어가 포함된 것 찾기
    mask = all_tickers['symbol'].str.contains(query_upper, na=False) | \
           all_tickers['name'].str.contains(query_clean, na=False)
    results = all_tickers[mask].head(20).copy()
    return results

@st.cache_data(ttl=300, show_spinner=False)
def cached_kr_stock_price(symbol):
    """국내 주식 현재가 캐시 (5분)."""
    try:
        from pykrx import stock as krx
        from datetime import datetime, timedelta

        # 최근 거래일 찾기
        for i in range(7):
            trd_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            try:
                df = krx.get_market_ohlcv_by_date(trd_date, trd_date, symbol)
                if not df.empty:
                    break
            except:
                continue

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
            'change': row.get('등락률', 0),
        }
    except Exception:
        return {}

@st.cache_data(ttl=300, show_spinner=False)
def cached_kr_stock_ohlcv(symbol):
    """국내 주식 OHLCV 캐시 (5분)."""
    try:
        from pykrx import stock as krx
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")

        ohlcv = krx.get_market_ohlcv_by_date(start_date, end_date, symbol)
        if ohlcv.empty:
            return None

        ohlcv = ohlcv.reset_index()
        ohlcv.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'value', 'change']

        # 이동평균선
        ohlcv['ma5'] = ohlcv['close'].rolling(window=5).mean()
        ohlcv['ma20'] = ohlcv['close'].rolling(window=20).mean()
        ohlcv['ma60'] = ohlcv['close'].rolling(window=60).mean()

        # 볼린저밴드
        ohlcv['bb_mid'] = ohlcv['close'].rolling(window=20).mean()
        ohlcv['bb_std'] = ohlcv['close'].rolling(window=20).std()
        ohlcv['bb_upper'] = ohlcv['bb_mid'] + (ohlcv['bb_std'] * 2)
        ohlcv['bb_lower'] = ohlcv['bb_mid'] - (ohlcv['bb_std'] * 2)

        # RSI
        delta = ohlcv['close'].diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / loss
        ohlcv['rsi'] = 100 - (100 / (1 + rs))

        return ohlcv
    except Exception:
        return None

@st.cache_data(ttl=600, show_spinner=False)
def cached_kr_stock_ohlcv_3y(symbol):
    """국내 주식 3년 OHLCV 캐시 (10분)."""
    return get_kr_scraper().get_ohlcv_extended(symbol, years=3)


# 주요 슈퍼투자자 정보 (전역)
FAMOUS_INVESTORS = {
    'BRK': ('워렌 버핏', 'Berkshire Hathaway CEO. "가치투자의 아버지". 장기 우량주 집중 투자.'),
    'icahn': ('칼 아이칸', '행동주의 투자자. 저평가 기업 인수 후 경영 개선 요구.'),
    'soros': ('조지 소로스', '헤지펀드의 전설. 매크로 전략, "영란은행을 무너뜨린 남자".'),
    'BRIDGEWATER': ('레이 달리오', 'Bridgewater Associates 설립자. 올웨더 포트폴리오 전략.'),
    'einhorn': ('데이비드 아인혼', 'Greenlight Capital. 가치투자 + 숏 셀링 전문.'),
    'ackman': ('빌 애크먼', 'Pershing Square. 소수 종목 집중 투자.'),
    'BERKOWITZ': ('브루스 버코위츠', 'Fairholme Fund. 역발상 가치투자.'),
    'tepper': ('데이비드 테퍼', 'Appaloosa Management. 부실채권·주식 투자.'),
    'THIRD POINT': ('댄 로브', 'Third Point. 행동주의 + 이벤트 드리븐.'),
    'BAUPOST': ('세스 클라만', 'Baupost Group. 안전마진 투자 철학.'),
    'gates': ('빌 게이츠', 'Microsoft 공동창업자. 다양한 산업 분산 투자.'),
}

def get_investor_display_name(investor_id: str, name: str) -> str:
    """투자자 ID와 영문명을 한글 포함 표시명으로 변환."""
    if investor_id in FAMOUS_INVESTORS:
        kr_name, _ = FAMOUS_INVESTORS[investor_id]
        return f"{kr_name} / {name} ({investor_id})"
    return f"{name} ({investor_id})"

# 영문 Activity → 한글 변환
ACTIVITY_KR = {
    'Add': '➕ 추가 매수',
    'New': '🆕 신규 매수',
    'Reduce': '📉 일부 매도',
    'Sold Out': '🔴 전량 매도',
    'Unchanged': '— 변동 없음',
}

def translate_activity(activity: str) -> str:
    """Dataroma 영문 activity를 한글로 변환."""
    if not activity or pd.isna(activity):
        return '— 변동 없음'
    activity = str(activity).strip()
    for eng, kr in ACTIVITY_KR.items():
        if eng.lower() in activity.lower():
            return kr
    return activity  # 매칭 안 되면 원문 그대로

# 메뉴 목록
MENU_ITEMS = ["🏠 홈", "📌 내 관심종목", "💼 포트폴리오", "🔍 공통 종목", "📈 변화 분석", "🌐 Grand Portfolio", "🇰🇷 국내주식", "🎯 종목 추천", "📊 진입/손절 분석", "🌍 해외 종목 추천", "💰 연금저축", "🪙 현물코인"]

# 네비게이션 콜백 함수
def navigate_to(page_name):
    st.session_state.nav_menu = page_name

# Sidebar
st.sidebar.title("📊 Investor Tracker")
page = st.sidebar.radio(
    "메뉴",
    MENU_ITEMS,
    key="nav_menu"
)
st.sidebar.markdown("---")
st.sidebar.markdown("Made with Streamlit")
st.sidebar.markdown("[GitHub](https://github.com/skykhj007-png/investor-tracker)")


# Home page
if page == "🏠 홈":
    st.title("🎯 Investor Tracker")
    st.markdown("슈퍼투자자들의 포트폴리오를 추적하고 분석합니다.")

    # Quick stats (정적 값 - API 호출 없이 즉시 표시)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("추적 투자자 수", "80+")
    with col2:
        st.metric("대표 투자자", "Warren Buffett")
    with col3:
        st.metric("데이터 소스", "Dataroma / SEC")

    st.markdown("---")
    st.subheader("메뉴 바로가기")

    # 모바일용 메뉴 버튼 (2열 배치)
    menu_buttons = [
        ("📌", "내 관심종목", "보유/관심 종목 실시간 알림", "📌 내 관심종목"),
        ("💼", "포트폴리오", "개별 투자자 보유 종목 조회", "💼 포트폴리오"),
        ("🔍", "공통 종목", "투자자 공통 보유 종목", "🔍 공통 종목"),
        ("📈", "변화 분석", "분기별 매수/매도 추적", "📈 변화 분석"),
        ("🌐", "Grand Portfolio", "전체 통합 포트폴리오", "🌐 Grand Portfolio"),
        ("🇰🇷", "국내주식", "투자자 동향/공매도/매집", "🇰🇷 국내주식"),
        ("🎯", "종목 추천", "AI 종합 종목 추천", "🎯 종목 추천"),
        ("📊", "진입/손절 분석", "주식 진입점·손절·목표가", "📊 진입/손절 분석"),
        ("🌍", "해외 종목 추천", "슈퍼투자자 기반 미국주식", "🌍 해외 종목 추천"),
        ("💰", "연금저축", "ETF 추천/심리분석", "💰 연금저축"),
        ("🪙", "현물코인", "업비트/바이낸스 분석", "🪙 현물코인"),
    ]

    for i in range(0, len(menu_buttons), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(menu_buttons):
                icon, name, desc, page_key = menu_buttons[i + j]
                with col:
                    st.button(
                        f"{icon} {name}\n{desc}",
                        key=f"menu_{page_key}",
                        use_container_width=True,
                        on_click=navigate_to,
                        args=(page_key,)
                    )

    st.markdown("---")
    st.subheader("사용 가이드")

    with st.expander("해외주식 (미국 슈퍼투자자 추적)", expanded=False):
        st.markdown("""
**SEC 공시 기반 슈퍼투자자 포트폴리오 분석**

- **포트폴리오**: 워렌 버핏, 레이 달리오 등 82명의 슈퍼투자자가 보유한 종목을 실시간 확인
- **공통 종목**: 여러 투자자가 동시에 보유한 종목을 찾아 시장 컨센서스 파악
- **변화 분석**: 분기별 매수/매도 내역을 추적하여 자금 흐름 확인
- **Grand Portfolio**: 전체 투자자의 보유 종목을 통합하여 인기 종목 순위 확인
        """)

    with st.expander("국내주식 분석", expanded=False):
        st.markdown("""
**외국인/기관 수급 + 기술적 지표 종합 분석**

- **국내주식**: 외국인/기관 순매수 현황, 공매도 비중, 매집 신호 등 투자자 동향
- **종목 추천**: 아래 지표를 종합하여 점수화한 추천 종목 (KOSPI/KOSDAQ)
  - 외국인/기관 순매수 순위 및 금액
  - PER/PBR 밸류에이션 (저평가 종목 가점)
  - RSI (과매도 구간 매수 신호)
  - MACD 골든크로스/데드크로스
  - 거래량 급증, 공매도 비중, 시가총액
        """)

    with st.expander("연금저축 ETF", expanded=False):
        st.markdown("""
**연금저축 계좌용 ETF 추천 + 시장 심리 분석**

- **빠른 추천**: 샤프 비율, MDD(최대낙폭), RSI를 종합한 ETF 추천
  - 샤프 비율 > 1.0 : 위험 대비 수익 우수
  - MDD > -10% : 안정적 상품
  - RSI < 30 : 과매도 구간 = 매수 적기
- **테마별 추천**: 미국주식, 반도체, 2차전지 등 테마 ETF
- **시장 심리**: 뉴스 기반 투자 심리 분석 및 자산 배분 제안
        """)

    with st.expander("현물코인 (암호화폐)", expanded=False):
        st.markdown("""
**업비트 + 바이낸스 실시간 분석**

- **시세 현황**: 거래대금 상위 코인 실시간 가격/등락률 + 공포탐욕지수
- **종목 추천**: 아래 지표를 종합한 코인 추천
  - 24시간/5일 모멘텀, 거래량 급증
  - RSI, MACD 골든크로스/데드크로스
  - 볼린저 밴드 (과매도/과매수/스퀴즈)
  - 공포탐욕지수 (극도의 공포 시 역발상 매수)
  - 김치프리미엄 (업비트 vs 바이낸스 가격 차이)
- **기술적 분석**: 개별 코인 캔들차트, MACD, 볼린저밴드 차트
        """)

    with st.expander("용어 설명", expanded=False):
        st.markdown("""
| 용어 | 설명 |
|------|------|
| **PER** | 주가수익비율. 낮을수록 저평가 (10 이하 매력적) |
| **PBR** | 주가순자산비율. 1 이하면 자산 대비 저평가 |
| **RSI** | 상대강도지수(0~100). 30 이하 과매도, 70 이상 과매수 |
| **MACD** | 추세 전환 지표. 골든크로스=매수신호, 데드크로스=매도신호 |
| **샤프 비율** | 위험 대비 수익률. 1.0 이상이면 우수 |
| **MDD** | 최대낙폭. 고점 대비 최대 하락률 (작을수록 안정적) |
| **볼린저밴드** | 변동성 기반 밴드. 하단 근처=매수, 상단 돌파=매도 |
| **공포탐욕지수** | 시장 심리(0~100). 극도의 공포 시 역발상 매수 유효 |
| **김치프리미엄** | 국내 vs 해외 코인 가격 차이. 5% 이상이면 과열 |
        """)

    st.markdown("---")
    st.caption("데이터는 5분마다 자동 갱신됩니다. 왼쪽 사이드바 또는 위 버튼으로 메뉴를 이동하세요.")
    st.stop()


# 내 관심종목 page
elif page == "📌 내 관심종목":
    st.title("📌 내 관심종목 모니터링")
    st.markdown("*보유/관심 종목을 등록하면 공시, 매집신호, 기술적 분석을 한 곳에서 확인할 수 있습니다*")

    # 세션에 관심종목 저장
    if "watchlist_kr" not in st.session_state:
        st.session_state.watchlist_kr = []
    if "watchlist_us" not in st.session_state:
        st.session_state.watchlist_us = []

    # 종목 추가 UI
    st.subheader("➕ 관심종목 추가")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🇰🇷 국내주식**")
        kr_input = st.text_input("종목코드 (6자리)", placeholder="005930", key="kr_add_input")
        if st.button("추가", key="add_kr"):
            if kr_input and len(kr_input.strip()) == 6 and kr_input.strip().isdigit():
                code = kr_input.strip()
                if code not in st.session_state.watchlist_kr:
                    st.session_state.watchlist_kr.append(code)
                    st.success(f"{code} 추가됨")
                    st.rerun()
                else:
                    st.warning("이미 등록된 종목입니다.")
            else:
                st.error("6자리 숫자를 입력하세요")

    with col2:
        st.markdown("**🇺🇸 미국주식**")
        us_input = st.text_input("티커 (예: AAPL)", placeholder="AAPL", key="us_add_input")
        if st.button("추가", key="add_us"):
            if us_input and us_input.strip():
                ticker = us_input.strip().upper()
                if ticker not in st.session_state.watchlist_us:
                    st.session_state.watchlist_us.append(ticker)
                    st.success(f"{ticker} 추가됨")
                    st.rerun()
                else:
                    st.warning("이미 등록된 종목입니다.")
            else:
                st.error("티커를 입력하세요")

    # 현재 등록된 종목 표시
    st.markdown("---")
    st.subheader("📋 등록된 관심종목")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🇰🇷 국내주식**")
        if st.session_state.watchlist_kr:
            for code in st.session_state.watchlist_kr:
                c1, c2 = st.columns([3, 1])
                c1.write(f"• {code}")
                if c2.button("❌", key=f"del_kr_{code}"):
                    st.session_state.watchlist_kr.remove(code)
                    st.rerun()
        else:
            st.caption("등록된 국내주식이 없습니다")

    with col2:
        st.markdown("**🇺🇸 미국주식**")
        if st.session_state.watchlist_us:
            for ticker in st.session_state.watchlist_us:
                c1, c2 = st.columns([3, 1])
                c1.write(f"• {ticker}")
                if c2.button("❌", key=f"del_us_{ticker}"):
                    st.session_state.watchlist_us.remove(ticker)
                    st.rerun()
        else:
            st.caption("등록된 미국주식이 없습니다")

    # 관심종목 분석 결과
    if st.session_state.watchlist_kr or st.session_state.watchlist_us:
        st.markdown("---")
        st.subheader("📊 관심종목 분석")

        tab1, tab2, tab3 = st.tabs(["📋 전자공시", "💎 매집신호", "📈 기술적 분석"])

        # ─── 전자공시 탭 ───
        with tab1:
            if st.session_state.watchlist_kr:
                st.markdown("### 🇰🇷 국내주식 최근 공시")
                try:
                    # 종목명 조회
                    from pykrx import stock as krx
                    stock_names = []
                    for code in st.session_state.watchlist_kr:
                        try:
                            name = krx.get_market_ticker_name(code)
                            if name:
                                stock_names.append(name)
                        except:
                            pass

                    if stock_names:
                        with st.spinner("공시 조회 중..."):
                            disclosures = cached_disclosures_for_stocks(tuple(stock_names), 30)

                        if not disclosures.empty:
                            for _, row in disclosures.iterrows():
                                report_type = row.get('report_type', '')
                                # 공시 유형별 아이콘
                                if '대량보유' in str(report_type):
                                    icon = "📊"
                                elif '주요사항' in str(report_type):
                                    icon = "⚡"
                                elif '공정공시' in str(report_type):
                                    icon = "📢"
                                else:
                                    icon = "📄"

                                st.markdown(f"""
                                {icon} **{row.get('company', '')}** - {row.get('title', '')}
                                - 📅 {row.get('date', '')} | {report_type}
                                - [DART 원문 보기]({row.get('url', '#')})
                                """)
                            st.caption(f"최근 30일 내 {len(disclosures)}건의 공시")
                        else:
                            st.info("최근 30일 내 관련 공시가 없습니다.")
                    else:
                        st.warning("종목명을 확인할 수 없습니다.")
                except Exception as e:
                    st.error(f"공시 조회 오류: {e}")
            else:
                st.info("국내주식을 등록하면 DART 전자공시를 확인할 수 있습니다.")

        # ─── 매집신호 탭 ───
        with tab2:
            if st.session_state.watchlist_kr:
                st.markdown("### 🇰🇷 국내주식 매집 신호")
                for code in st.session_state.watchlist_kr:
                    try:
                        with st.spinner(f"{code} 분석 중..."):
                            ohlcv = cached_kr_stock_ohlcv(code)
                            stock_info = cached_kr_stock_price(code)

                        if ohlcv is not None and not ohlcv.empty and stock_info:
                            name = stock_info.get('name', code)
                            latest = ohlcv.iloc[-1]
                            price = latest['close']

                            # 매집 신호 분석
                            signals = []
                            score = 50

                            # 거래량 분석
                            if len(ohlcv) > 20:
                                avg_vol = ohlcv['volume'].tail(20).mean()
                                today_vol = latest['volume']
                                if today_vol > avg_vol * 2:
                                    signals.append("🔥 거래량 폭증 (2배 이상)")
                                    score += 15
                                elif today_vol > avg_vol * 1.5:
                                    signals.append("📈 거래량 급증 (1.5배)")
                                    score += 10

                            # RSI 분석
                            rsi = latest.get('rsi', 50)
                            if pd.notna(rsi):
                                if rsi < 30:
                                    signals.append(f"💚 RSI {rsi:.0f} 과매도")
                                    score += 15
                                elif rsi > 70:
                                    signals.append(f"🔴 RSI {rsi:.0f} 과매수")
                                    score -= 10

                            # 이평선 분석
                            ma5 = latest.get('ma5', 0)
                            ma20 = latest.get('ma20', 0)
                            if pd.notna(ma5) and pd.notna(ma20) and ma5 > 0 and ma20 > 0:
                                if price > ma5 > ma20:
                                    signals.append("📈 정배열")
                                    score += 10
                                elif price < ma5 < ma20:
                                    signals.append("📉 역배열")
                                    score -= 10

                            # 결과 표시
                            with st.expander(f"**{name}** ({code}) - 매집점수: {score}", expanded=True):
                                col1, col2 = st.columns([1, 2])
                                col1.metric("현재가", f"{int(price):,}원", f"{stock_info.get('change', 0):+.2f}%")
                                col2.write("**신호:**")
                                if signals:
                                    for sig in signals:
                                        col2.write(f"• {sig}")
                                else:
                                    col2.write("• 특이 신호 없음")
                    except Exception as e:
                        st.warning(f"{code} 분석 실패: {e}")

            if st.session_state.watchlist_us:
                st.markdown("### 🇺🇸 미국주식 슈퍼투자자 보유 현황")
                for ticker in st.session_state.watchlist_us:
                    try:
                        with st.spinner(f"{ticker} 분석 중..."):
                            analysis = cached_us_stock_analysis(ticker)

                        if not analysis.get('error'):
                            with st.expander(f"**{analysis['name']}** ({ticker}) - 슈퍼투자자 {analysis['num_super_investors']}명", expanded=True):
                                col1, col2 = st.columns([1, 2])
                                col1.metric("현재가", f"${analysis['current_price']:.2f}", f"{analysis['change_pct']:+.2f}%")

                                if analysis['super_investors']:
                                    col2.write("**보유 투자자:**")
                                    for inv in analysis['super_investors'][:5]:
                                        col2.write(f"• {inv['name']} ({inv['percent']:.1f}%)")
                                else:
                                    col2.write("• 슈퍼투자자 보유 없음")
                        else:
                            st.warning(f"{ticker}: {analysis['error']}")
                    except Exception as e:
                        st.warning(f"{ticker} 분석 실패: {e}")

            if not st.session_state.watchlist_kr and not st.session_state.watchlist_us:
                st.info("종목을 등록하면 매집 신호를 분석합니다.")

        # ─── 기술적 분석 탭 ───
        with tab3:
            if st.session_state.watchlist_kr:
                st.markdown("### 🇰🇷 국내주식 기술적 지표")
                kr_data = []
                for code in st.session_state.watchlist_kr:
                    try:
                        ohlcv = cached_kr_stock_ohlcv(code)
                        stock_info = cached_kr_stock_price(code)
                        if ohlcv is not None and not ohlcv.empty and stock_info:
                            latest = ohlcv.iloc[-1]
                            kr_data.append({
                                '종목': stock_info.get('name', code),
                                '코드': code,
                                '현재가': f"{int(latest['close']):,}",
                                'RSI': f"{latest.get('rsi', 50):.0f}" if pd.notna(latest.get('rsi')) else '-',
                                'MA5': f"{int(latest.get('ma5', 0)):,}" if pd.notna(latest.get('ma5')) else '-',
                                'MA20': f"{int(latest.get('ma20', 0)):,}" if pd.notna(latest.get('ma20')) else '-',
                            })
                    except:
                        pass
                if kr_data:
                    st.dataframe(pd.DataFrame(kr_data), use_container_width=True, hide_index=True)

            if st.session_state.watchlist_us:
                st.markdown("### 🇺🇸 미국주식 기술적 지표")
                us_data = []
                for ticker in st.session_state.watchlist_us:
                    try:
                        analysis = cached_us_stock_analysis(ticker)
                        if not analysis.get('error'):
                            us_data.append({
                                '종목': analysis['name'],
                                '티커': ticker,
                                '현재가': f"${analysis['current_price']:.2f}",
                                'RSI': f"{analysis['rsi']:.0f}",
                                '매수점수': analysis['buy_score'],
                                '판단': analysis['recommendation'],
                            })
                    except:
                        pass
                if us_data:
                    st.dataframe(pd.DataFrame(us_data), use_container_width=True, hide_index=True)

            if not st.session_state.watchlist_kr and not st.session_state.watchlist_us:
                st.info("종목을 등록하면 기술적 분석을 제공합니다.")

    else:
        st.info("👆 위에서 관심종목을 추가하면 실시간 분석 결과를 확인할 수 있습니다.")

    st.markdown("---")
    st.caption("💡 관심종목은 브라우저 세션에 저장되며, 페이지를 새로고침하면 초기화됩니다.")
    st.stop()


# Portfolio page
elif page == "💼 포트폴리오":
    st.title("💼 투자자 포트폴리오")

    with st.expander("💡 **주요 슈퍼투자자 소개** (클릭하여 펼치기)", expanded=False):
        st.markdown("SEC 13F 공시 기반으로 82명의 슈퍼투자자 포트폴리오를 추적합니다.")
        for inv_id, (name, desc) in FAMOUS_INVESTORS.items():
            st.markdown(f"- **{name}** (`{inv_id}`) — {desc}")
        st.caption("위 투자자 외에도 다양한 헤지펀드·기관 투자자의 포트폴리오를 확인할 수 있습니다.")

    # Get investor list
    with st.spinner("투자자 목록 로딩..."):
        investors_df = cached_investor_list()

    if investors_df.empty:
        st.error("투자자 목록을 가져올 수 없습니다.")
    else:
        # Investor selector with Korean names
        investor_options = {
            get_investor_display_name(row['investor_id'], row['name']): row['investor_id']
            for _, row in investors_df.iterrows()
        }

        col1, col2 = st.columns([3, 1])
        with col1:
            selected = st.selectbox("투자자 선택", list(investor_options.keys()))
        with col2:
            top_n = st.number_input("상위 종목 수", min_value=5, max_value=50, value=15)

        investor_id = investor_options[selected]

        # 선택된 투자자 설명 표시
        if investor_id in FAMOUS_INVESTORS:
            kr_name, desc = FAMOUS_INVESTORS[investor_id]
            st.caption(f"ℹ️ **{kr_name}**: {desc}")

        # Load portfolio
        with st.spinner(f"{investor_id} 포트폴리오 로딩..."):
            portfolio = cached_portfolio(investor_id)

        if portfolio.empty:
            st.warning("포트폴리오 데이터가 없습니다.")
        else:
            # Summary
            total_value = portfolio["value"].sum()
            st.metric("총 포트폴리오 가치", f"${total_value:,.0f}")

            # Pie chart
            col1, col2 = st.columns([1, 1])

            with col1:
                fig = px.pie(
                    portfolio.head(top_n),
                    values="percent_portfolio",
                    names="symbol",
                    title=f"포트폴리오 구성 (Top {top_n})",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    portfolio.head(top_n),
                    x="symbol",
                    y="percent_portfolio",
                    title="종목별 비중 (%)",
                    color="percent_portfolio",
                    color_continuous_scale="Blues",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Table
            st.subheader("보유 종목 목록")
            display_df = portfolio.head(top_n)[["symbol", "stock", "percent_portfolio", "shares", "value", "activity"]].copy()
            display_df["activity"] = display_df["activity"].apply(translate_activity)
            display_df.columns = ["티커", "종목명", "비중(%)", "보유 주수", "평가금액($)", "최근 활동"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.caption("💡 **비중(%)**: 전체 포트폴리오에서 해당 종목이 차지하는 비율 | **최근 활동**: 직전 분기 대비 매수/매도 변화")
    st.stop()


# Overlap page
elif page == "🔍 공통 종목":
    st.title("🔍 공통 종목 분석")

    # Get investor list
    with st.spinner("투자자 목록 로딩..."):
        investors_df = cached_investor_list()

    if investors_df.empty:
        st.error("투자자 목록을 가져올 수 없습니다.")
    else:
        investor_options = {
            get_investor_display_name(row['investor_id'], row['name']): row['investor_id']
            for _, row in investors_df.iterrows()
        }

        selected_investors = st.multiselect(
            "분석할 투자자 선택 (2명 이상)",
            list(investor_options.keys()),
            default=list(investor_options.keys())[:3] if len(investor_options) >= 3 else list(investor_options.keys())
        )

        st.caption("💡 여러 슈퍼투자자가 동시에 보유한 종목 = 시장의 공통된 판단. 많은 투자자가 보유할수록 신뢰도 높음.")

        col1, col2 = st.columns(2)
        with col1:
            min_owners = st.slider("최소 보유자 수", 2, len(selected_investors) if selected_investors else 2, 2)
        with col2:
            use_conviction = st.checkbox("확신도 점수 사용", value=False,
                                          help="확신도 = 투자자들이 해당 종목에 포트폴리오의 몇 %를 투자했는지 가중 평균한 점수")

        if len(selected_investors) >= 2:
            investor_ids = [investor_options[s] for s in selected_investors]

            with st.spinner("분석 중..."):
                analyzer = OverlapAnalyzer(scraper=scraper)
                if use_conviction:
                    result = analyzer.calculate_conviction_score(investor_ids)
                else:
                    result = analyzer.rank_by_ownership_count(investor_ids)

            if not result.empty:
                result = result[result["num_owners"] >= min_owners]

                if not result.empty:
                    # Chart
                    y_col = "num_owners" if not use_conviction else "conviction_score"
                    y_title = "보유 투자자 수" if not use_conviction else "확신도 점수"
                    fig = px.bar(
                        result.head(20),
                        x="symbol",
                        y=y_col,
                        title="공통 보유 종목",
                        color="avg_percent",
                        color_continuous_scale="Greens",
                        hover_data=["stock", "avg_percent"],
                    )
                    fig.update_layout(yaxis_title=y_title, xaxis_title="종목 티커")
                    st.plotly_chart(fig, use_container_width=True)

                    # Table - 컬럼명 한글화
                    overlap_display = result.head(30).copy()
                    col_rename = {
                        'symbol': '티커', 'stock': '종목명',
                        'num_owners': '보유 투자자 수', 'avg_percent': '평균 비중(%)',
                        'conviction_score': '확신도 점수', 'owners': '보유 투자자',
                    }
                    overlap_display = overlap_display.rename(columns={k: v for k, v in col_rename.items() if k in overlap_display.columns})
                    st.dataframe(overlap_display, use_container_width=True, hide_index=True)
                else:
                    st.info(f"{min_owners}명 이상이 공통 보유한 종목이 없습니다.")
            else:
                st.warning("분석 결과가 없습니다.")
        else:
            st.info("2명 이상의 투자자를 선택하세요.")
    st.stop()


# Changes page
elif page == "📈 변화 분석":
    st.title("📈 분기별 변화 분석")

    # 투자자 목록 로딩
    with st.spinner("투자자 목록 로딩..."):
        changes_investors_df = cached_investor_list()

    if not changes_investors_df.empty:
        changes_investor_options = {
            get_investor_display_name(row['investor_id'], row['name']): row['investor_id']
            for _, row in changes_investors_df.iterrows()
        }

        col1, col2 = st.columns(2)

        with col1:
            changes_selected = st.selectbox("투자자 선택", list(changes_investor_options.keys()), key="changes_investor")
            investor_id = changes_investor_options[changes_selected]

            # 선택된 투자자 설명
            if investor_id in FAMOUS_INVESTORS:
                kr_name, desc = FAMOUS_INVESTORS[investor_id]
                st.caption(f"ℹ️ **{kr_name}**: {desc}")
        with col2:
            # Check available quarters
            quarters = get_database().get_available_quarters(investor_id)
            st.write(f"저장된 분기: {quarters if quarters else '없음'}")
    else:
        st.error("투자자 목록을 가져올 수 없습니다.")
        investor_id = "BRK"

    st.caption("💡 **사용법**: ① '현재 데이터 저장' 클릭 → 현재 포트폴리오를 해당 분기로 저장 ② 두 분기를 비교하여 매수/매도 변화를 확인")

    col1, col2, col3 = st.columns(3)
    with col1:
        q1 = st.text_input("이전 분기 (예: 2024Q3)", value="2024Q3")
    with col2:
        q2 = st.text_input("현재 분기 (예: 2024Q4)", value="2024Q4")
    with col3:
        if st.button("📥 현재 데이터 저장", help="선택한 투자자의 현재 포트폴리오를 '현재 분기'로 저장합니다"):
            with st.spinner("동기화 중..."):
                analyzer = ChangesAnalyzer(db=db, scraper=scraper)
                analyzer.sync_portfolio(investor_id, q2)
                st.success(f"{investor_id} 포트폴리오를 {q2}로 저장했습니다.")
                st.rerun()

    if st.button("🔍 분기 비교 분석", help="이전 분기와 현재 분기의 포트폴리오를 비교합니다"):
        analyzer = ChangesAnalyzer(db=db, scraper=scraper)
        changes = analyzer.compare_quarters(investor_id, q1, q2)

        if changes.empty:
            st.info("변화가 없거나 데이터가 부족합니다. 먼저 '현재 데이터 저장'으로 분기 데이터를 저장해주세요.")
        else:
            # Summary
            summary = analyzer.get_activity_summary(investor_id, q1, q2)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🆕 신규 매수", summary["new_positions"], delta_color="normal")
            col2.metric("🔴 완전 매도", summary["exits"], delta_color="inverse")
            col3.metric("📈 비중 증가", summary["increases"])
            col4.metric("📉 비중 감소", summary["decreases"])

            # Charts
            col1, col2 = st.columns(2)

            with col1:
                new_df = changes[changes["change_type"] == "NEW"]
                if not new_df.empty:
                    fig = px.bar(new_df, x="symbol", y="curr_percent", title="🆕 신규 매수 종목 (현재 비중%)", color_discrete_sequence=["green"])
                    fig.update_layout(xaxis_title="종목 티커", yaxis_title="포트폴리오 비중(%)")
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                exit_df = changes[changes["change_type"] == "EXIT"]
                if not exit_df.empty:
                    fig = px.bar(exit_df, x="symbol", y="prev_percent", title="🔴 매도 종목 (이전 비중%)", color_discrete_sequence=["red"])
                    fig.update_layout(xaxis_title="종목 티커", yaxis_title="이전 비중(%)")
                    st.plotly_chart(fig, use_container_width=True)

            # Full table - 한글화
            st.subheader("전체 변화 내역")
            changes_display = changes.copy()
            change_type_kr = {'NEW': '🆕 신규 매수', 'EXIT': '🔴 전량 매도', 'INCREASE': '📈 비중 증가', 'DECREASE': '📉 비중 감소', 'UNCHANGED': '— 변동 없음'}
            if 'change_type' in changes_display.columns:
                changes_display['change_type'] = changes_display['change_type'].map(change_type_kr).fillna(changes_display['change_type'])
            col_rename = {
                'symbol': '티커', 'stock': '종목명',
                'change_type': '변화 유형',
                'prev_percent': f'{q1} 비중(%)',
                'curr_percent': f'{q2} 비중(%)',
                'change_amount': '변화량(%)',
            }
            changes_display = changes_display.rename(columns={k: v for k, v in col_rename.items() if k in changes_display.columns})
            st.dataframe(changes_display, use_container_width=True, hide_index=True)
    st.stop()


# Grand Portfolio page
elif page == "🌐 Grand Portfolio":
    st.title("🌐 Grand Portfolio (슈퍼투자자 통합 포트폴리오)")
    st.markdown("*82명의 슈퍼투자자가 가장 많이 보유한 종목 순위 — 투자자 수가 많을수록 시장의 합의가 높은 종목*")

    with st.spinner("Grand Portfolio 로딩..."):
        grand = cached_grand_portfolio()

    if grand.empty:
        st.error("데이터를 가져올 수 없습니다.")
    else:
        st.info("💡 **보유 투자자 수**가 많을수록 많은 슈퍼투자자가 해당 종목을 신뢰한다는 의미입니다. **매입가**는 투자자들의 평균 매입 가격입니다.")

        # Chart
        fig = px.bar(
            grand.head(30),
            x="symbol",
            y="num_owners",
            title="슈퍼투자자 보유 현황 (Top 30)",
            color="num_owners",
            color_continuous_scale="Viridis",
            hover_data=["stock", "percent_total"],
        )
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="보유 투자자 수", xaxis_title="종목 티커")
        st.plotly_chart(fig, use_container_width=True)

        # Table
        display_cols = ["symbol", "stock", "num_owners", "percent_total"]
        col_names = ["티커", "종목명", "보유 투자자 수", "전체 비중(%)"]

        if "current_price" in grand.columns:
            display_cols.append("current_price")
            col_names.append("현재가($)")
        if "hold_price" in grand.columns:
            display_cols.append("hold_price")
            col_names.append("평균 매입가($)")

        display_df = grand.head(50)[display_cols].copy()
        display_df.columns = col_names
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.caption("💡 **전체 비중(%)**: 전체 슈퍼투자자 합산 포트폴리오에서 차지하는 비율 | **평균 매입가**: 투자자들의 평균 매수 가격")
    st.stop()


# Korean Stocks page
elif page == "🇰🇷 국내주식":
    st.title("🇰🇷 국내주식 투자자 동향")

    # 이 페이지에서만 인스턴스 생성
    kr_scraper = get_kr_scraper()
    kr_recommender = get_recommender()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 외국인/기관 순매수", "📈 시총 상위", "📉 공매도", "💎 매집 신호", "🔍 종목 검색", "📋 전자공시"])

    with tab1:
        st.subheader("투자자별 순매수 상위 종목")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🌍 외국인 순매수")
            with st.spinner("외국인 데이터 로딩..."):
                foreign_df = cached_foreign_buying(20)

            if not foreign_df.empty:
                # Format amounts
                foreign_df['순매수(억)'] = (foreign_df['net_amount'] / 100000000).round(0).astype(int)

                # Chart
                fig = px.bar(
                    foreign_df.head(15),
                    x='name',
                    y='순매수(억)',
                    title="외국인 순매수 TOP 15",
                    color='순매수(억)',
                    color_continuous_scale="Blues",
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

                # Table
                display_cols = ['rank', 'symbol', 'name', '순매수(억)']
                st.dataframe(foreign_df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.warning("외국인 데이터를 가져올 수 없습니다.")

        with col2:
            st.markdown("### 🏛️ 기관 순매수")
            with st.spinner("기관 데이터 로딩..."):
                inst_df = cached_institution_buying(20)

            if not inst_df.empty:
                inst_df['순매수(억)'] = (inst_df['net_amount'] / 100000000).round(0).astype(int)

                fig = px.bar(
                    inst_df.head(15),
                    x='name',
                    y='순매수(억)',
                    title="기관 순매수 TOP 15",
                    color='순매수(억)',
                    color_continuous_scale="Greens",
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

                display_cols = ['rank', 'symbol', 'name', '순매수(억)']
                st.dataframe(inst_df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.warning("기관 데이터를 가져올 수 없습니다.")

    with tab2:
        st.subheader("시가총액 상위 종목")

        col1, col2 = st.columns([1, 3])
        with col1:
            market = st.selectbox("시장", ["KOSPI", "KOSDAQ"])
        with col2:
            top_n = st.slider("종목 수", 10, 50, 30)

        with st.spinner(f"{market} 시총 상위 로딩..."):
            cap_df = cached_market_cap_top(market, top_n)

        if not cap_df.empty:
            cap_df['시총(조)'] = (cap_df['market_cap'] / 1000000000000).round(1)
            cap_df['현재가'] = cap_df['close'].apply(lambda x: f"{x:,}")

            # Chart
            fig = px.bar(
                cap_df.head(20),
                x='name',
                y='시총(조)',
                title=f"{market} 시가총액 TOP 20",
                color='시총(조)',
                color_continuous_scale="Viridis",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Table
            display_cols = ['rank', 'symbol', 'name', '현재가', '시총(조)']
            st.dataframe(cap_df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.warning("시총 데이터를 가져올 수 없습니다.")

    with tab3:
        st.subheader("📉 공매도 현황")
        st.markdown("*공매도 비중이 높은 종목 - 숏 포지션이 많은 종목*")

        col1, col2 = st.columns([1, 3])
        with col1:
            short_market = st.selectbox("시장 선택", ["KOSPI", "KOSDAQ"], key="short_market")

        with st.spinner("공매도 데이터 로딩..."):
            short_df = cached_short_volume(short_market, 30)

        if not short_df.empty:
            short_df['공매도(억)'] = (short_df['short_amount'] / 100000000).round(0).astype(int)
            short_df['비중(%)'] = short_df['short_ratio'].round(2)

            # Chart
            fig = px.bar(
                short_df.head(20),
                x='name',
                y='비중(%)',
                title=f"{short_market} 공매도 비중 TOP 20",
                color='비중(%)',
                color_continuous_scale="Reds",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Info box
            st.info("💡 **공매도 비중이 높은 종목**: 숏 포지션이 많아 하락 압력이 있을 수 있음. 단, 숏 스퀴즈 가능성도 존재.")

            # Table
            display_cols = ['rank', 'symbol', 'name', '공매도(억)', '비중(%)']
            st.dataframe(short_df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.warning("공매도 데이터를 가져올 수 없습니다.")

    with tab4:
        st.subheader("💎 주식 매집 신호")
        st.markdown("*거래량 급증 + 외국인/기관 순매수 종합 분석*")

        st.info("""
        **매집 신호 분석 기준:**
        - 🔥거래량폭증: 거래량 100% 이상 급증
        - 📈거래량급증: 거래량 50% 이상 증가
        - 🌍외국인매수: 외국인 순매수 상위 종목
        - 🏛️기관매수: 기관 순매수 상위 종목
        - ⭐강한매집: 가격 + 거래량 동반 상승
        - 🚀급등: 5일 수익률 10% 이상
        """)

        col1, col2 = st.columns([1, 3])
        with col1:
            acc_market = st.selectbox("시장", ["KOSPI", "KOSDAQ"], key="acc_market")

        with st.spinner("매집 신호 분석 중..."):
            acc_signals = cached_accumulation_signals(acc_market, 20)

        if not acc_signals.empty:
            # 매집 점수 차트
            fig = px.bar(
                acc_signals.head(15),
                x='name',
                y='accumulation_score',
                title=f"{acc_market} 매집 신호 TOP 15",
                color='accumulation_score',
                color_continuous_scale="YlOrRd",
                hover_data=['price_change_5d', 'vol_change_pct', 'signals'],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # 상세 카드
            st.subheader("📋 매집 신호 상세")

            for _, row in acc_signals.head(10).iterrows():
                with st.expander(f"{row['rank']}. {row['name']} ({row['symbol']}) - 점수: {row['accumulation_score']}"):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("현재가", f"{row['price']:,}원")
                    col2.metric("5일 변화", f"{row['price_change_5d']:+.1f}%")
                    col3.metric("거래량 변화", f"{row['vol_change_pct']:+.1f}%")
                    col4.metric("시가총액", f"{row['market_cap_조']}조")

                    st.markdown(f"**신호**: {row['signals']}")

                    # 외국인/기관 매수 여부
                    buy_info = []
                    if row.get('foreign_buy'):
                        buy_info.append("🌍 외국인 순매수 중")
                    if row.get('inst_buy'):
                        buy_info.append("🏛️ 기관 순매수 중")
                    if buy_info:
                        st.success(" | ".join(buy_info))

            # 전체 테이블
            st.subheader("📊 전체 매집 신호 목록")
            display_df = acc_signals[['rank', 'symbol', 'name', 'price', 'price_change_5d', 'vol_change_pct', 'market_cap_조', 'accumulation_score', 'signals']].copy()
            display_df.columns = ['순위', '코드', '종목명', '현재가', '5일변화(%)', '거래량변화(%)', '시총(조)', '매집점수', '신호']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("매집 신호 데이터를 가져올 수 없습니다.")

        # 강력 매수 후보
        st.markdown("---")
        st.subheader("🏆 강력 매수 후보")
        st.markdown("*수급 추천 + 매집 신호 모두 충족하는 종목*")

        with st.spinner("종합 분석 중..."):
            strong_candidates = cached_strong_buy(acc_market, 5)

        if strong_candidates['strong_picks']:
            st.success(f"✅ 강력 매수 후보 {len(strong_candidates['strong_picks'])}개 발견!")

            for i, pick in enumerate(strong_candidates['strong_picks'], 1):
                st.markdown(f"""
                **{i}. {pick['name']}** (`{pick['symbol']}`)
                - 현재가: {pick['price']:,}원 | 5일 변화: {pick['price_change_5d']:+.1f}%
                - 수급 점수: {pick['rec_score']} | 매집 점수: {pick['acc_score']}
                - 수급 신호: {pick['rec_signals']}
                - 매집 신호: {pick['acc_signals']}
                """)
        else:
            st.info("현재 수급과 매집 신호를 동시에 만족하는 종목이 없습니다.")

    with tab5:
        st.subheader("🔍 종목 검색 및 분석")
        st.markdown("*종목명/코드를 입력하면 차트, 기술적 지표, 매수 판단 정보를 제공합니다*")

        st.info("💡 **빠른 검색 팁**: 종목코드 6자리(예: 005930)를 입력하면 즉시 검색됩니다!")

        # 인기 종목 바로가기
        st.markdown("**🔥 인기 종목 바로가기:**")
        popular_kr = [
            ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("373220", "LG에너지솔루션"),
            ("035420", "NAVER"), ("005380", "현대차"), ("000270", "기아"),
            ("035720", "카카오"), ("006400", "삼성SDI")
        ]

        # 인기 종목 버튼 클릭 시 설정된 값 확인
        default_kr_query = st.session_state.get("_selected_kr_stock", "")
        if default_kr_query:
            del st.session_state["_selected_kr_stock"]

        cols = st.columns(4)
        for i, (code, name) in enumerate(popular_kr):
            if cols[i % 4].button(f"{name}", key=f"pop_kr_{code}"):
                st.session_state["_selected_kr_stock"] = code
                st.rerun()

        query = st.text_input("종목명 또는 코드 입력", value=default_kr_query, placeholder="005930, 삼성전자, SK하이닉스...")

        if query:
            # 종목코드 직접 입력 시 빠른 검색
            if query.strip().isdigit() and len(query.strip()) == 6:
                with st.spinner("종목 조회 중..."):
                    results = cached_kr_search_stock(query)
            else:
                with st.spinner("종목 검색 중... (첫 검색 시 목록 로딩으로 시간이 걸릴 수 있습니다)"):
                    results = cached_kr_search_stock(query)

            if not results.empty:
                # 종목 선택
                selected_symbol = st.selectbox(
                    "분석할 종목 선택",
                    results['symbol'].tolist(),
                    format_func=lambda x: f"{x} - {results[results['symbol']==x]['name'].values[0]}"
                )

                if selected_symbol:
                    selected_name = results[results['symbol']==selected_symbol]['name'].values[0]

                    with st.spinner(f"{selected_name} 분석 중..."):
                        # 기본 정보 (캐시 사용)
                        stock_info = cached_kr_stock_price(selected_symbol)

                        # 차트 데이터 (캐시 사용)
                        ohlcv = cached_kr_stock_ohlcv(selected_symbol)

                        if ohlcv is not None and not ohlcv.empty:
                            latest = ohlcv.iloc[-1]
                            price = latest['close']
                            ma5 = latest['ma5'] if pd.notna(latest['ma5']) else 0
                            ma20 = latest['ma20'] if pd.notna(latest['ma20']) else 0
                            ma60 = latest['ma60'] if pd.notna(latest['ma60']) else 0
                            rsi = latest['rsi'] if pd.notna(latest['rsi']) else 50
                            bb_upper = latest['bb_upper'] if pd.notna(latest['bb_upper']) else 0
                            bb_lower = latest['bb_lower'] if pd.notna(latest['bb_lower']) else 0

                            # 기본 정보 표시
                            st.markdown(f"## {selected_name} ({selected_symbol})")

                            if stock_info:
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("현재가", f"{stock_info.get('close', 0):,}원", f"{stock_info.get('change', 0):+.2f}%")
                                col2.metric("거래량", f"{stock_info.get('volume', 0):,}")
                                col3.metric("시가", f"{stock_info.get('open', 0):,}원")
                                col4.metric("고가/저가", f"{stock_info.get('high', 0):,} / {stock_info.get('low', 0):,}")

                            # ─── 매수 신호 분석 ───
                            st.markdown("---")
                            signals = []
                            buy_score = 50

                            # 이동평균선 분석
                            if ma5 > 0 and ma20 > 0:
                                if price > ma5 > ma20:
                                    signals.append('📈 정배열 (상승 추세)')
                                    buy_score += 10
                                elif price < ma5 < ma20:
                                    signals.append('📉 역배열 (하락 추세)')
                                    buy_score -= 10
                                # 골든크로스 체크
                                if len(ohlcv) > 2:
                                        prev_ma5 = ohlcv['ma5'].iloc[-2]
                                        prev_ma20 = ohlcv['ma20'].iloc[-2]
                                        if pd.notna(prev_ma5) and pd.notna(prev_ma20):
                                            if ma5 > ma20 and prev_ma5 <= prev_ma20:
                                                signals.append('🌟 골든크로스!')
                                                buy_score += 15

                                # RSI 분석
                                if rsi < 30:
                                    signals.append(f'💚 RSI {rsi:.0f} 과매도 (매수 기회)')
                                    buy_score += 15
                                elif rsi > 70:
                                    signals.append(f'🔴 RSI {rsi:.0f} 과매수')
                                    buy_score -= 10

                                # 볼린저밴드 분석
                                if bb_lower > 0:
                                    if price <= bb_lower:
                                        signals.append('💰 볼린저밴드 하단 (저점 매수 기회)')
                                        buy_score += 10
                                    elif price >= bb_upper:
                                        signals.append('⚠️ 볼린저밴드 상단 (과열)')
                                        buy_score -= 5

                                # 외국인/기관 수급 체크
                                try:
                                    foreign_df = cached_foreign_buying(50)
                                    inst_df = cached_institution_buying(50)
                                    if not foreign_df.empty and selected_symbol in foreign_df['symbol'].values:
                                        signals.append('🌍 외국인 순매수 상위')
                                        buy_score += 10
                                    if not inst_df.empty and selected_symbol in inst_df['symbol'].values:
                                        signals.append('🏛️ 기관 순매수 상위')
                                        buy_score += 10
                                except Exception:
                                    pass

                                buy_score = max(0, min(100, buy_score))

                                col1, col2 = st.columns([1, 2])
                                with col1:
                                    if buy_score >= 75:
                                        rec = "🟢 적극 매수 고려"
                                        score_color = "🟢"
                                    elif buy_score >= 60:
                                        rec = "🟡 매수 관망"
                                        score_color = "🟡"
                                    elif buy_score >= 40:
                                        rec = "🟠 중립"
                                        score_color = "🟠"
                                    else:
                                        rec = "🔴 매수 비추천"
                                        score_color = "🔴"
                                    st.metric("매수 점수", f"{score_color} {buy_score}점 / 100점")
                                    st.markdown(f"### {rec}")

                                with col2:
                                    st.markdown("**📊 분석 신호:**")
                                    if signals:
                                        for sig in signals:
                                            st.markdown(f"- {sig}")
                                    else:
                                        st.markdown("- 특별한 신호 없음")

                                # 기술적 지표
                                st.markdown("---")
                                st.subheader("📈 기술적 지표")

                                col1, col2, col3, col4, col5 = st.columns(5)
                                col1.metric("MA5", f"{ma5:,.0f}원" if ma5 > 0 else "-")
                                col2.metric("MA20", f"{ma20:,.0f}원" if ma20 > 0 else "-")
                                col3.metric("MA60", f"{ma60:,.0f}원" if ma60 > 0 else "-")
                                rsi_status = "과매수" if rsi > 70 else "과매도" if rsi < 30 else "중립"
                                col4.metric(f"RSI ({rsi_status})", f"{rsi:.1f}")
                                col5.metric("볼린저 위치", f"{((price - bb_lower) / (bb_upper - bb_lower) * 100):.0f}%" if bb_upper > bb_lower else "-")

                                # 차트 표시
                                st.markdown("---")
                                st.subheader("📊 6개월 차트")

                                fig = go.Figure()

                                fig.add_trace(go.Candlestick(
                                    x=ohlcv['date'],
                                    open=ohlcv['open'], high=ohlcv['high'],
                                    low=ohlcv['low'], close=ohlcv['close'],
                                    name="가격"
                                ))

                                fig.add_trace(go.Scatter(x=ohlcv['date'], y=ohlcv['ma5'], name='MA5', line=dict(color='orange', width=1)))
                                fig.add_trace(go.Scatter(x=ohlcv['date'], y=ohlcv['ma20'], name='MA20', line=dict(color='blue', width=1)))
                                fig.add_trace(go.Scatter(x=ohlcv['date'], y=ohlcv['ma60'], name='MA60', line=dict(color='purple', width=1)))

                                # 볼린저밴드
                                fig.add_trace(go.Scatter(x=ohlcv['date'], y=ohlcv['bb_upper'], name='BB상단', line=dict(color='rgba(255,0,0,0.3)', width=1, dash='dot')))
                                fig.add_trace(go.Scatter(x=ohlcv['date'], y=ohlcv['bb_lower'], name='BB하단', line=dict(color='rgba(0,128,0,0.3)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(173,216,230,0.1)'))

                                fig.update_layout(
                                    title=f"{selected_name} 일봉 차트",
                                    xaxis_rangeslider_visible=False,
                                    height=500,
                                    yaxis_title="가격 (원)",
                                )
                                st.plotly_chart(fig, use_container_width=True)

                                # RSI 차트
                                st.subheader("📉 RSI 차트")
                                fig_rsi = px.line(ohlcv.dropna(subset=['rsi']), x='date', y='rsi', title='RSI (14일)')
                                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="과매수 (70)")
                                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="과매도 (30)")
                                fig_rsi.update_layout(height=300, yaxis_title="RSI")
                                st.plotly_chart(fig_rsi, use_container_width=True)

                        else:
                            st.warning("차트 데이터를 가져올 수 없습니다.")
            else:
                st.info("검색 결과가 없습니다.")
        else:
            st.info("💡 종목명(예: 삼성전자) 또는 코드(예: 005930)를 입력하세요.")

    with tab6:
        st.subheader("📋 DART 전자공시")

        dart_mode = st.radio(
            "조회 방식",
            ["📰 최근 공시", "🔍 기업 검색", "📌 관심 종목 공시"],
            horizontal=True,
            key="dart_mode"
        )

        type_options = {
            '대량보유': 'B001',
            '주요사항': 'C001',
            '공정공시': 'D001',
            '사업보고서': 'A001',
            '분기보고서': 'A003',
        }

        if dart_mode == "📰 최근 공시":
            st.markdown("*최근 주요 공시 (대량보유, 주요사항, 공정공시 등)*")

            col_period, col_types = st.columns([1, 3])
            with col_period:
                dart_days = st.selectbox("조회 기간", [3, 7, 14, 30], index=1,
                                          format_func=lambda x: f"최근 {x}일",
                                          key="dart_days")

            with col_types:
                selected_labels = st.multiselect(
                    "공시 유형",
                    options=list(type_options.keys()),
                    default=['대량보유', '주요사항'],
                    key="dart_types"
                )

            selected_types = [type_options[label] for label in selected_labels] if selected_labels else None

            with st.spinner("DART 공시 로딩..."):
                types_tuple = tuple(selected_types) if selected_types else None
                disclosures = cached_recent_disclosures(days=dart_days, report_types_tuple=types_tuple)

            if not disclosures.empty:
                st.success(f"총 {len(disclosures)}건의 공시")

                # 필터 키워드
                keyword_filter = st.text_input("🔎 제목 필터 (선택)", placeholder="예: 대량, 취득, 처분, 유상증자...", key="dart_title_filter")

                filtered = disclosures
                if keyword_filter:
                    filtered = disclosures[disclosures['title'].str.contains(keyword_filter, case=False, na=False)]
                    st.info(f"'{keyword_filter}' 포함 공시: {len(filtered)}건")

                for _, row in filtered.iterrows():
                    date_str = str(row['date'])
                    if len(date_str) == 8:
                        date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    type_badge = f"`{row['report_type']}`" if row.get('report_type') else ""
                    st.markdown(
                        f"**{date_str}** {type_badge} **{row['company']}** - "
                        f"[{row['title']}]({row['url']})"
                    )
            else:
                st.info("해당 기간의 공시가 없습니다.")

        elif dart_mode == "🔍 기업 검색":
            st.markdown("*기업명을 입력하여 관련 공시를 검색합니다 (정확한 기업명 입력)*")

            col_search, col_days = st.columns([3, 1])
            with col_search:
                company_query = st.text_input("기업명 입력", placeholder="삼성전자, SK하이닉스, LG에너지솔루션...", key="dart_company_search")
            with col_days:
                search_days = st.selectbox("검색 기간", [7, 14, 30, 60, 90], index=2,
                                            format_func=lambda x: f"최근 {x}일",
                                            key="dart_search_days")

            # 공시 유형 필터
            search_types = st.multiselect(
                "공시 유형 필터 (비워두면 전체)",
                options=list(type_options.keys()),
                default=[],
                key="dart_search_types"
            )

            if company_query:
                with st.spinner(f"'{company_query}' 공시 검색 중..."):
                    company_disclosures = cached_company_disclosures(company_query, days=search_days)

                if not company_disclosures.empty:
                    # 유형 필터 적용
                    if search_types:
                        search_type_codes = [type_options[t] for t in search_types]
                        # report_type 컬럼으로 필터
                        type_name_map = {v: k for k, v in type_options.items()}
                        company_disclosures = company_disclosures[
                            company_disclosures['report_type'].isin(search_types) |
                            company_disclosures['report_type'].isin(search_type_codes)
                        ]

                    st.success(f"'{company_query}' 관련 공시 {len(company_disclosures)}건")

                    # 테이블 형태
                    display_df = company_disclosures.copy()
                    display_df['공시일'] = display_df['date'].apply(
                        lambda x: f"{str(x)[:4]}-{str(x)[4:6]}-{str(x)[6:]}" if len(str(x)) == 8 else str(x)
                    )
                    display_df['기업명'] = display_df['company']
                    display_df['유형'] = display_df['report_type']
                    display_df['공시제목'] = display_df['title']

                    st.dataframe(
                        display_df[['공시일', '기업명', '유형', '공시제목']],
                        use_container_width=True, hide_index=True
                    )

                    # 원문 링크
                    st.subheader("📄 공시 원문 링크")
                    for _, row in company_disclosures.iterrows():
                        date_str = str(row['date'])
                        if len(date_str) == 8:
                            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                        st.markdown(
                            f"- **{date_str}** [{row['company']} - {row['title']}]({row['url']})"
                        )
                else:
                    st.info(f"'{company_query}' 관련 최근 {search_days}일 공시가 없습니다.")
                    st.caption("💡 DART는 정확한 기업명이 필요합니다. (예: '삼성' → '삼성전자')")

        elif dart_mode == "📌 관심 종목 공시":
            st.markdown("*여러 종목을 한 번에 입력하여 관련 공시를 조회합니다*")

            stocks_input = st.text_area(
                "종목명 입력 (쉼표로 구분)",
                placeholder="삼성전자, SK하이닉스, LG에너지솔루션, 현대자동차",
                key="dart_multi_stocks",
                height=68,
            )

            col_d, col_t = st.columns([1, 3])
            with col_d:
                multi_days = st.selectbox("검색 기간", [7, 14, 30], index=1,
                                           format_func=lambda x: f"최근 {x}일",
                                           key="dart_multi_days")

            if stocks_input:
                stock_names = [s.strip() for s in stocks_input.split(",") if s.strip()]
                if stock_names:
                    with st.spinner(f"{len(stock_names)}개 종목 공시 조회 중..."):
                        multi_disclosures = cached_disclosures_for_stocks(tuple(stock_names), days=multi_days)

                    if not multi_disclosures.empty:
                        st.success(f"총 {len(multi_disclosures)}건의 공시")

                        # 종목별 탭
                        found_companies = multi_disclosures['company'].unique().tolist()
                        if len(found_companies) > 1:
                            company_filter = st.multiselect(
                                "종목 필터",
                                options=found_companies,
                                default=found_companies,
                                key="dart_multi_filter"
                            )
                            multi_disclosures = multi_disclosures[multi_disclosures['company'].isin(company_filter)]

                        for _, row in multi_disclosures.iterrows():
                            date_str = str(row['date'])
                            if len(date_str) == 8:
                                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                            type_badge = f"`{row['report_type']}`" if row.get('report_type') else ""
                            st.markdown(
                                f"**{date_str}** {type_badge} **{row['company']}** - "
                                f"[{row['title']}]({row['url']})"
                            )
                    else:
                        st.info(f"입력한 종목의 최근 {multi_days}일 공시가 없습니다.")
                        st.caption("💡 DART는 정확한 기업명이 필요합니다. (예: '삼성' → '삼성전자')")
    st.stop()


# Recommendation page
elif page == "🎯 종목 추천":
    st.title("🎯 AI 종목 추천")
    st.markdown("*외국인/기관 수급과 공매도 데이터를 종합 분석한 매수 추천*")

    # 이 페이지에서만 인스턴스 생성
    recommender = get_recommender()

    st.info("""
    **점수 산정 기준 (최대 ~120점):**
    - 외국인 순매수: 최대 30점 (순위+금액)
    - 기관 순매수: 최대 30점 (순위+금액)
    - 동반 매수 시너지: +10점
    - 가격 모멘텀 (MA5/MA20): 최대 15점
    - 거래량 급증: 최대 10점
    - 시가총액/공매도: ±5점
    - **PER/PBR 밸류에이션**: 최대 15점
    - **RSI (14일)**: 최대 10점
    - **MACD 크로스**: 최대 10점
    """)

    tab1, tab2, tab3, tab4 = st.tabs(["🏆 종합 추천", "⭐ 동반 매수", "🔥 역발상 매수", "📊 기술적 분석"])

    with tab1:
        st.subheader("종합 추천 TOP 20")

        with st.spinner("데이터 분석 중..."):
            recs = cached_recommendations(top_n=20)

        if not recs.empty:
            # 진입점 0인 경우 대시보드 폴백 (서버 호환성)
            if 'entry_point' in recs.columns:
                for idx in recs.index:
                    if recs.at[idx, 'entry_point'] == 0:
                        try:
                            sym = recs.at[idx, 'symbol']
                            price_info = get_kr_scraper().get_stock_price(sym)
                            p = price_info.get('close', 0)
                            if p > 0:
                                rsi_v = float(recs.at[idx, 'rsi']) if 'rsi' in recs.columns else 50
                                if rsi_v < 30:
                                    recs.at[idx, 'entry_point'] = p
                                else:
                                    recs.at[idx, 'entry_point'] = int(p * 0.98)
                                recs.at[idx, 'stop_loss'] = int(p * 0.93)
                                recs.at[idx, 'stop_loss_pct'] = -7.0
                                recs.at[idx, 'target_1'] = int(p * 1.05)
                                recs.at[idx, 'target_1_pct'] = 5.0
                                recs.at[idx, 'risk_reward'] = 1.0
                        except Exception:
                            pass

            # Score chart
            fig = px.bar(
                recs.head(15),
                x='name',
                y='score',
                title="종합 점수 TOP 15",
                color='score',
                color_continuous_scale="Bluered",
                hover_data=['symbol', 'signals'],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # 추천 상세 카드
            st.subheader("📋 추천 상세")
            for _, row in recs.head(10).iterrows():
                with st.expander(f"{row['rank']}. {row['name']} ({row['symbol']}) - 점수: {row['score']}"):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("외국인", f"{row.get('foreign_억', '-')}억")
                    c2.metric("기관", f"{row.get('inst_억', '-')}억")
                    c3.metric("RSI", f"{row.get('rsi', 0):.0f}")
                    c4.metric("PER", f"{row.get('per', 0):.1f}")
                    c5.metric("총점", f"{row['score']:.1f}")

                    if row.get('entry_point', 0) > 0:
                        st.markdown("---")
                        e1, e2, e3, e4 = st.columns(4)
                        e1.metric("🎯 진입점", f"{row['entry_point']:,.0f}원")
                        e2.metric("🛑 손절", f"{row['stop_loss']:,.0f}원", f"{row['stop_loss_pct']:+.1f}%")
                        if row.get('target_1', 0) > 0:
                            e3.metric("📈 1차 목표", f"{row['target_1']:,.0f}원", f"+{row['target_1_pct']:.1f}%")
                        _rr = row.get('risk_reward', 0)
                        _rr_icon = "🟢" if _rr >= 2 else "🟡" if _rr >= 1 else "🔴"
                        e4.metric("위험/보상", f"{_rr_icon} {_rr:.1f}:1")

                    st.markdown(f"**신호**: {row['signals']}")

            # Detailed table
            st.subheader("📊 전체 추천 목록")
            available_cols = ['rank', 'symbol', 'name', 'score', 'foreign_억', 'inst_억', 'short_ratio']
            col_names = ['순위', '코드', '종목명', '점수', '외국인(억)', '기관(억)', '공매도(%)']

            if 'entry_point' in recs.columns:
                available_cols.extend(['entry_point', 'stop_loss', 'stop_loss_pct', 'target_1', 'risk_reward'])
                col_names.extend(['진입점', '손절', '손절(%)', '1차목표', 'R/R'])
            if 'per' in recs.columns:
                available_cols.append('per')
                col_names.append('PER')
            if 'pbr' in recs.columns:
                available_cols.append('pbr')
                col_names.append('PBR')
            if 'rsi' in recs.columns:
                available_cols.append('rsi')
                col_names.append('RSI')

            avail = [c for c in available_cols if c in recs.columns]
            avail_names = [col_names[available_cols.index(c)] for c in avail]
            display_df = recs[avail].copy()
            display_df.columns = avail_names
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # 추천 종목 최근 공시
            st.markdown("---")
            st.subheader("📋 추천 종목 최근 공시")

            top_stock_names = recs.head(5)['name'].tolist()

            with st.spinner("추천 종목 공시 조회 중..."):
                rec_disclosures = cached_disclosures_for_stocks(tuple(top_stock_names), days=14)

            if not rec_disclosures.empty:
                for _, drow in rec_disclosures.head(15).iterrows():
                    date_str = str(drow['date'])
                    if len(date_str) == 8:
                        date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    type_badge = f"`{drow['report_type']}`" if drow.get('report_type') else ""
                    st.markdown(
                        f"**{date_str}** {type_badge} **{drow['company']}** - "
                        f"[{drow['title']}]({drow['url']})"
                    )
            else:
                st.info("최근 14일간 추천 종목 관련 공시가 없습니다.")
        else:
            st.warning("추천 데이터를 가져올 수 없습니다.")

    with tab2:
        st.subheader("⭐ 외국인 + 기관 동반 매수")
        st.markdown("*외국인과 기관이 동시에 순매수하는 종목 - 가장 강력한 시그널*")

        with st.spinner("분석 중..."):
            dual = cached_dual_buying()

        if not dual.empty:
            # Chart
            fig = px.scatter(
                dual,
                x='foreign_억',
                y='inst_억',
                size='score',
                color='score',
                text='name',
                title="외국인 vs 기관 순매수 (버블 크기 = 점수)",
                color_continuous_scale="Viridis",
            )
            fig.update_traces(textposition='top center')
            fig.update_layout(
                xaxis_title="외국인 순매수 (억원)",
                yaxis_title="기관 순매수 (억원)",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Table
            display_df = dual[['rank', 'symbol', 'name', 'score', 'foreign_억', 'inst_억']]
            display_df.columns = ['순위', '코드', '종목명', '점수', '외국인(억)', '기관(억)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("현재 외국인+기관 동반 매수 종목이 없습니다.")

    with tab3:
        st.subheader("🔥 역발상 매수 후보")
        st.markdown("*공매도 비중이 높지만 외국인/기관이 매수하는 종목 - 숏 스퀴즈 가능성*")

        st.warning("⚠️ 고위험 투자 전략입니다. 공매도 비중이 높다는 것은 하락 압력이 있다는 의미이기도 합니다.")

        with st.spinner("분석 중..."):
            contra = cached_contrarian()

        if not contra.empty:
            # Chart
            fig = px.bar(
                contra,
                x='name',
                y='short_ratio',
                title="공매도 비중 (외국인/기관 매수 유입 종목)",
                color='short_ratio',
                color_continuous_scale="Reds",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Table
            st.dataframe(contra, use_container_width=True, hide_index=True)
        else:
            st.info("현재 역발상 매수 후보 종목이 없습니다.")

    with tab4:
        st.subheader("📊 개별 종목 기술적 분석")
        st.markdown("*추천 종목의 3년 차트 데이터를 분석하여 진입점/손절/목표가를 산출합니다.*")

        if not recs.empty:
            stock_options = {f"{row['name']} ({row['symbol']})": row['symbol']
                            for _, row in recs.head(20).iterrows()}
            selected_label = st.selectbox("종목 선택", list(stock_options.keys()), key="kr_tech_select")
            selected_sym = stock_options[selected_label]

            with st.spinner("3년 차트 분석 중..."):
                ohlcv_3y = cached_kr_stock_ohlcv_3y(selected_sym)
                recommender = get_recommender()
                entry_data = recommender.get_entry_analysis(selected_sym, ohlcv_3y)

            if 'error' not in entry_data:
                # 메트릭
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("현재가", f"{entry_data['price']:,.0f}원")
                m2.metric("🎯 진입점", f"{entry_data['entry_point']:,.0f}원")
                m3.metric("🛑 손절", f"{entry_data['stop_loss']:,.0f}원", f"{entry_data['stop_loss_pct']:+.1f}%")
                if entry_data.get('targets'):
                    t = entry_data['targets'][0]
                    m4.metric(f"📈 {t['label']}", f"{t['price']:,.0f}원", f"+{t['pct']:.1f}%")
                rr = entry_data.get('risk_reward_ratio', 0)
                rr_icon = "🟢" if rr >= 2 else "🟡" if rr >= 1 else "🔴"
                m5.metric("위험/보상", f"{rr_icon} {rr:.1f}:1")

                # MA / RSI 정보
                st.markdown(f"**MA20**: {entry_data.get('ma20', 0):,.0f}원 | "
                            f"**MA60**: {entry_data.get('ma60', 0):,.0f}원 | "
                            f"**MA120**: {entry_data.get('ma120', 0):,.0f}원 | "
                            f"**RSI**: {entry_data.get('rsi', 0):.0f}")

                # 지지/저항
                sup_col, res_col = st.columns(2)
                with sup_col:
                    st.markdown("**🟢 주요 지지선**")
                    for lvl in entry_data.get('support_levels', [])[:4]:
                        st.markdown(f"- {lvl['price']:,.0f}원 (강도: {'●' * min(lvl['strength'], 5)})")
                with res_col:
                    st.markdown("**🔴 주요 저항선**")
                    for lvl in entry_data.get('resistance_levels', [])[:4]:
                        st.markdown(f"- {lvl['price']:,.0f}원 (강도: {'●' * min(lvl['strength'], 5)})")

                # 캔들차트 (최근 6개월) + 오버레이
                if ohlcv_3y is not None and not ohlcv_3y.empty:
                    import plotly.graph_objects as go
                    chart_data = ohlcv_3y.tail(120).reset_index()
                    col_map = {'날짜': 'date'}
                    if '날짜' in chart_data.columns:
                        chart_data = chart_data.rename(columns=col_map)
                    elif chart_data.columns[0] != 'date':
                        chart_data = chart_data.rename(columns={chart_data.columns[0]: 'date'})

                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=chart_data['date'],
                        open=chart_data['시가'], high=chart_data['고가'],
                        low=chart_data['저가'], close=chart_data['종가'],
                        name="가격"
                    ))
                    # MA
                    all_closes = ohlcv_3y['종가']
                    ma20_s = all_closes.rolling(20).mean().tail(120)
                    ma60_s = all_closes.rolling(60).mean().tail(120)
                    fig.add_trace(go.Scatter(x=chart_data['date'], y=ma20_s.values,
                                            name='MA20', line=dict(color='orange', width=1)))
                    fig.add_trace(go.Scatter(x=chart_data['date'], y=ma60_s.values,
                                            name='MA60', line=dict(color='blue', width=1)))
                    # 진입/손절/목표 수평선
                    fig.add_hline(y=entry_data['entry_point'], line_dash="dash",
                                  line_color="green", line_width=2,
                                  annotation_text="진입점", annotation_position="bottom left")
                    fig.add_hline(y=entry_data['stop_loss'], line_dash="dot",
                                  line_color="red", line_width=2,
                                  annotation_text="손절", annotation_position="bottom left")
                    if entry_data.get('targets'):
                        fig.add_hline(y=entry_data['targets'][0]['price'], line_dash="dash",
                                      line_color="gold", line_width=2,
                                      annotation_text="1차 목표", annotation_position="bottom left")
                    if len(entry_data.get('targets', [])) >= 2:
                        fig.add_hline(y=entry_data['targets'][1]['price'], line_dash="dot",
                                      line_color="cyan", line_width=1,
                                      annotation_text="2차 목표", annotation_position="bottom left")
                    fig.update_layout(
                        title=f"{selected_label} 최근 6개월 차트 (진입/손절/목표)",
                        xaxis_rangeslider_visible=False,
                        height=500,
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("기술적 분석 데이터를 가져올 수 없습니다.")
        else:
            st.info("먼저 '종합 추천' 탭에서 추천 데이터를 로드해 주세요.")

    # Disclaimer
    st.markdown("---")
    st.caption("⚠️ **투자 유의사항**: 이 추천은 참고용이며 투자 권유가 아닙니다. 투자 결정은 본인의 판단과 책임하에 하시기 바랍니다.")
    st.stop()


# ═══════════════ 진입/손절 분석 페이지 ═══════════════
elif page == "📊 진입/손절 분석":
    st.title("📊 진입/손절/목표가 분석")
    st.markdown("*3년 차트 + 기술적 지표를 분석하여 매매 포인트를 산출합니다.*")

    st.info("""
    **분석 방법:**
    - 📈 **1년 스윙 포인트**: 로컬 최저/최고점에서 지지·저항선 추출
    - 📊 **이동평균선**: MA20, MA60, MA120을 동적 지지/저항으로 활용
    - 📉 **볼린저밴드**: 상/하단 밴드를 추가 레벨로 참고
    - 🔢 **RSI**: 과매도(30 이하) 시 적극 매수, 과매수(70 이상) 시 주의
    """)

    analysis_tab1, analysis_tab2 = st.tabs(["🔍 종목 검색", "🏆 추천 종목 분석"])

    with analysis_tab1:
        st.subheader("🔍 종목 직접 검색")

        # 인기 종목 빠른 선택
        st.markdown("**인기 종목 빠른 선택:**")
        popular_kr = [
            ("삼성전자", "005930"), ("SK하이닉스", "000660"), ("LG에너지솔루션", "373220"),
            ("삼성바이오로직스", "207940"), ("현대차", "005380"), ("기아", "000270"),
            ("셀트리온", "068270"), ("KB금융", "105560"), ("POSCO홀딩스", "005490"),
            ("NAVER", "035420"), ("카카오", "035720"), ("삼성SDI", "006400"),
        ]
        pcols = st.columns(6)
        for i, (name, sym) in enumerate(popular_kr):
            if pcols[i % 6].button(name, key=f"entry_pop_{sym}", use_container_width=True):
                st.session_state._selected_entry_stock = sym
                st.session_state._selected_entry_name = name

        # 직접 입력
        manual_code = st.text_input("종목 코드 직접 입력 (6자리)", placeholder="005930", key="entry_manual_code")
        if manual_code and len(manual_code) == 6:
            st.session_state._selected_entry_stock = manual_code
            try:
                from pykrx import stock as krx
                st.session_state._selected_entry_name = krx.get_market_ticker_name(manual_code)
            except Exception:
                st.session_state._selected_entry_name = manual_code

        selected_sym = st.session_state.get('_selected_entry_stock', None)
        selected_name = st.session_state.get('_selected_entry_name', '')

        if selected_sym:
            st.markdown(f"### 분석 대상: **{selected_name}** (`{selected_sym}`)")

            with st.spinner(f"{selected_name} 3년 차트 분석 중..."):
                ohlcv_3y = cached_kr_stock_ohlcv_3y(selected_sym)
                recommender = get_recommender()
                entry_data = recommender.get_entry_analysis(selected_sym, ohlcv_3y)

            if 'error' not in entry_data:
                # 핵심 메트릭
                st.markdown("### 🎯 매매 포인트")
                m1, m2, m3 = st.columns(3)
                m1.metric("현재가", f"{entry_data['price']:,.0f}원")
                rr = entry_data.get('risk_reward_ratio', 0)
                rr_icon = "🟢" if rr >= 2 else "🟡" if rr >= 1 else "🔴"
                m2.metric("위험/보상", f"{rr_icon} {rr:.1f}:1")
                m3.metric("RSI", f"{entry_data.get('rsi', 0):.0f}")

                e1, e2, e3, e4 = st.columns(4)
                e1.metric("🎯 진입점", f"{entry_data['entry_point']:,.0f}원",
                          f"{(entry_data['entry_point'] - entry_data['price']) / entry_data['price'] * 100:+.1f}%")
                e2.metric("🛑 손절라인", f"{entry_data['stop_loss']:,.0f}원",
                          f"{entry_data['stop_loss_pct']:+.1f}%")
                for t in entry_data.get('targets', [])[:2]:
                    if t == entry_data['targets'][0]:
                        e3.metric(f"📈 {t['label']}", f"{t['price']:,.0f}원", f"+{t['pct']:.1f}%")
                    else:
                        e4.metric(f"📈 {t['label']}", f"{t['price']:,.0f}원", f"+{t['pct']:.1f}%")

                # MA 정보
                st.markdown(f"**MA20**: {entry_data.get('ma20', 0):,.0f}원 | "
                            f"**MA60**: {entry_data.get('ma60', 0):,.0f}원 | "
                            f"**MA120**: {entry_data.get('ma120', 0):,.0f}원")

                # 지지/저항
                st.markdown("---")
                sup_col, res_col = st.columns(2)
                with sup_col:
                    st.markdown("### 🟢 주요 지지선")
                    for lvl in entry_data.get('support_levels', [])[:5]:
                        pct = (lvl['price'] - entry_data['price']) / entry_data['price'] * 100
                        st.markdown(f"- **{lvl['price']:,.0f}원** ({pct:+.1f}%) — 강도: {'●' * min(lvl['strength'], 5)}")
                with res_col:
                    st.markdown("### 🔴 주요 저항선")
                    for lvl in entry_data.get('resistance_levels', [])[:5]:
                        pct = (lvl['price'] - entry_data['price']) / entry_data['price'] * 100
                        st.markdown(f"- **{lvl['price']:,.0f}원** ({pct:+.1f}%) — 강도: {'●' * min(lvl['strength'], 5)}")

                # 캔들차트
                if ohlcv_3y is not None and not ohlcv_3y.empty:
                    import plotly.graph_objects as go
                    st.markdown("---")
                    # 차트 기간 선택
                    chart_period = st.radio("차트 기간", ["3개월", "6개월", "1년", "3년"],
                                            index=1, horizontal=True, key="entry_chart_period")
                    period_map = {"3개월": 60, "6개월": 120, "1년": 250, "3년": len(ohlcv_3y)}
                    n_bars = period_map[chart_period]

                    chart_data = ohlcv_3y.tail(n_bars).reset_index()
                    if chart_data.columns[0] != 'date':
                        chart_data = chart_data.rename(columns={chart_data.columns[0]: 'date'})

                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=chart_data['date'],
                        open=chart_data['시가'], high=chart_data['고가'],
                        low=chart_data['저가'], close=chart_data['종가'],
                        name="가격"
                    ))
                    # MA
                    all_closes = ohlcv_3y['종가']
                    for ma_len, color, name in [(20, 'orange', 'MA20'), (60, 'blue', 'MA60'), (120, 'purple', 'MA120')]:
                        ma_s = all_closes.rolling(ma_len).mean().tail(n_bars)
                        fig.add_trace(go.Scatter(x=chart_data['date'], y=ma_s.values,
                                                name=name, line=dict(color=color, width=1)))

                    # 진입/손절/목표 수평선
                    fig.add_hline(y=entry_data['entry_point'], line_dash="dash",
                                  line_color="green", line_width=2,
                                  annotation_text=f"진입 {entry_data['entry_point']:,.0f}",
                                  annotation_position="bottom left")
                    fig.add_hline(y=entry_data['stop_loss'], line_dash="dot",
                                  line_color="red", line_width=2,
                                  annotation_text=f"손절 {entry_data['stop_loss']:,.0f}",
                                  annotation_position="bottom left")
                    for t in entry_data.get('targets', [])[:2]:
                        fig.add_hline(y=t['price'], line_dash="dash",
                                      line_color="gold", line_width=2,
                                      annotation_text=f"{t['label']} {t['price']:,.0f}",
                                      annotation_position="bottom left")

                    fig.update_layout(
                        title=f"{selected_name} ({selected_sym}) — {chart_period} 차트",
                        xaxis_rangeslider_visible=False,
                        height=550,
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("분석 데이터를 가져올 수 없습니다. 종목 코드를 확인해 주세요.")

    with analysis_tab2:
        st.subheader("🏆 추천 종목 진입/손절 분석")
        st.markdown("*AI 추천 종목들의 진입점/손절/목표가를 한눈에 비교합니다.*")

        with st.spinner("종합 추천 분석 중... (최대 2분)"):
            recs_entry = cached_recommendations(top_n=15)

        if not recs_entry.empty:
            # 폴백
            if 'entry_point' in recs_entry.columns:
                for idx in recs_entry.index:
                    if recs_entry.at[idx, 'entry_point'] == 0:
                        try:
                            sym = recs_entry.at[idx, 'symbol']
                            price_info = get_kr_scraper().get_stock_price(sym)
                            p = price_info.get('close', 0)
                            if p > 0:
                                recs_entry.at[idx, 'entry_point'] = int(p * 0.98)
                                recs_entry.at[idx, 'stop_loss'] = int(p * 0.93)
                                recs_entry.at[idx, 'stop_loss_pct'] = -7.0
                                recs_entry.at[idx, 'target_1'] = int(p * 1.05)
                                recs_entry.at[idx, 'target_1_pct'] = 5.0
                                recs_entry.at[idx, 'risk_reward'] = 1.0
                        except Exception:
                            pass

            # 카드 표시
            for _, row in recs_entry.iterrows():
                with st.expander(f"**{row['rank']}. {row['name']}** ({row['symbol']}) — 점수: {row['score']:.0f}"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("외국인", f"{row.get('foreign_억', '-')}억")
                    c2.metric("기관", f"{row.get('inst_억', '-')}억")
                    c3.metric("RSI", f"{row.get('rsi', 0):.0f}")
                    c4.metric("PER", f"{row.get('per', 0):.1f}")

                    if row.get('entry_point', 0) > 0:
                        st.markdown("---")
                        e1, e2, e3, e4 = st.columns(4)
                        e1.metric("🎯 진입점", f"{row['entry_point']:,.0f}원")
                        e2.metric("🛑 손절", f"{row['stop_loss']:,.0f}원", f"{row['stop_loss_pct']:+.1f}%")
                        if row.get('target_1', 0) > 0:
                            e3.metric("📈 1차 목표", f"{row['target_1']:,.0f}원", f"+{row['target_1_pct']:.1f}%")
                        _rr = row.get('risk_reward', 0)
                        _rr_icon = "🟢" if _rr >= 2 else "🟡" if _rr >= 1 else "🔴"
                        e4.metric("위험/보상", f"{_rr_icon} {_rr:.1f}:1")

                    st.markdown(f"**신호**: {row.get('signals', '')}")

            # 테이블
            st.markdown("---")
            st.subheader("📊 전체 비교 테이블")
            table_cols = ['rank', 'symbol', 'name', 'score']
            table_names = ['순위', '코드', '종목명', '점수']
            if 'entry_point' in recs_entry.columns:
                table_cols.extend(['entry_point', 'stop_loss', 'stop_loss_pct', 'target_1', 'risk_reward'])
                table_names.extend(['진입점', '손절', '손절(%)', '1차목표', 'R/R'])
            table_cols.extend(['rsi', 'foreign_억', 'inst_억'])
            table_names.extend(['RSI', '외국인(억)', '기관(억)'])
            avail = [c for c in table_cols if c in recs_entry.columns]
            avail_names = [table_names[table_cols.index(c)] for c in avail]
            df_disp = recs_entry[avail].copy()
            df_disp.columns = avail_names
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
        else:
            st.warning("추천 데이터를 가져올 수 없습니다.")

    st.markdown("---")
    st.caption("⚠️ **투자 유의사항**: 이 분석은 참고용이며 투자 권유가 아닙니다. 투자 결정은 본인의 판단과 책임하에 하시기 바랍니다.")
    st.stop()


# US Stock Recommendation page
elif page == "🌍 해외 종목 추천":
    st.title("🌍 해외(미국) AI 종목 추천")
    st.markdown("*SEC 13F 공시 기반 슈퍼투자자 82명의 보유·매매 활동 종합 분석*")

    st.info("""
    **점수 산정 기준 (최대 100점):**
    - 👥 **보유 투자자 수** (30점): 많은 투자자가 보유 = 시장의 합의
    - 🆕 **최근 매수 활동** (25점): 최근 새로 사거나 추가 매수한 종목 가점
    - 💪 **포트폴리오 비중** (20점): 투자자가 전체 자산의 몇 %를 투자했는지 (높을수록 확신)
    - 💰 **가격 분석** (15점): 현재가가 매수가보다 낮으면 저평가 가능성
    - ⭐ **유명 투자자** (10점): 버핏, 소로스 등 유명 투자자 보유 시 가점
    """)

    tab1, tab2, tab3, tab4 = st.tabs(["🏆 종합 추천", "🆕 신규 매수", "💪 고확신 종목", "🔍 종목 검색"])

    with tab1:
        st.subheader("종합 추천 TOP 20")

        with st.spinner("슈퍼투자자 데이터 분석 중... (최대 2분 소요)"):
            us_recs = cached_us_recommendations(top_n=20)

        if not us_recs.empty:
            # Score chart
            fig = px.bar(
                us_recs.head(15),
                x='name',
                y='score',
                title="슈퍼투자자 종합 점수 TOP 15",
                color='score',
                color_continuous_scale="Bluered",
                hover_data=['symbol', 'num_owners', 'signals'],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Top 5 cards
            st.subheader("📋 추천 상세")
            for _, row in us_recs.head(10).iterrows():
                with st.expander(f"{row['rank']}. {row['name']} ({row['symbol']}) - 점수: {row['score']}"):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("보유 투자자", f"{row['num_owners']}명")
                    col2.metric("신규 매수", f"{row['new_buys']}건")
                    col3.metric("추가 매수", f"{row['adds']}건")
                    col4.metric("평균 비중", f"{row['avg_conviction']}%")

                    if row['current_price'] > 0:
                        col5.metric("현재가", f"${row['current_price']:,.1f}")
                    else:
                        col5.metric("현재가", "-")

                    if row['famous_holders']:
                        st.success(f"⭐ 유명 투자자: {row['famous_holders']}")
                    st.markdown(f"**시그널**: {row['signals']}")

            # Full table
            st.subheader("📊 전체 추천 목록")
            display_cols = ['rank', 'symbol', 'name', 'score', 'num_owners', 'new_buys', 'adds', 'reduces', 'avg_conviction', 'famous_holders', 'signals']
            display_names = ['순위', '심볼', '종목명', '점수', '보유자수', '신규매수', '추가매수', '매도', '평균비중(%)', '유명투자자', '시그널']
            display_df = us_recs[display_cols].copy()
            display_df.columns = display_names
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("추천 데이터를 가져올 수 없습니다.")

    with tab2:
        st.subheader("🆕 최근 신규 매수 종목")
        st.markdown("*슈퍼투자자들이 최근 새로 사기 시작한 종목 — 기존에 없던 종목을 새로 매수한 것이므로 가장 강력한 관심 신호입니다*")

        with st.spinner("신규 매수 데이터 분석 중..."):
            new_buys = cached_us_new_buys(top_n=15)

        if not new_buys.empty:
            fig = px.bar(
                new_buys.head(10),
                x='name',
                y='buyer_count',
                title="신규 매수 종목 (투자자 수 기준)",
                color='avg_conviction',
                color_continuous_scale="Viridis",
                hover_data=['symbol', 'buyers'],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            for _, row in new_buys.iterrows():
                with st.expander(f"{row['rank']}. {row['name']} ({row['symbol']}) - {row['buyer_count']}명 매수"):
                    st.markdown(f"**매수 투자자**: {row['buyers']}")
                    st.markdown(f"**평균 포트폴리오 비중**: {row['avg_conviction']:.1f}%")
        else:
            st.info("현재 신규 매수 데이터가 없습니다.")

    with tab3:
        st.subheader("💪 고확신 종목")
        st.markdown("*투자자가 자산의 5% 이상을 투자한 종목 — 비중이 높을수록 그 종목에 대한 확신이 크다는 의미입니다*")

        with st.spinner("고확신 종목 분석 중..."):
            high_conv = cached_us_high_conviction(top_n=15)

        if not high_conv.empty:
            fig = px.scatter(
                high_conv,
                x='holder_count',
                y='max_conviction',
                size='avg_conviction',
                color='max_conviction',
                text='name',
                title="고확신 종목 (버블 크기 = 평균 투자 비중)",
                color_continuous_scale="YlOrRd",
            )
            fig.update_traces(textposition='top center')
            fig.update_layout(
                xaxis_title="5%↑ 투자한 투자자 수",
                yaxis_title="최대 투자 비중 (%)",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.caption("💡 **최대 비중**: 가장 많이 투자한 투자자가 자산의 몇 %를 이 종목에 투자했는지 | **평균 비중**: 5%↑ 투자자들의 평균")

            for _, row in high_conv.iterrows():
                with st.expander(f"{row['rank']}. {row['name']} ({row['symbol']}) - 최대 {row['max_conviction']}%"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("5%↑ 보유자", f"{row['holder_count']}명", help="이 종목에 포트폴리오의 5% 이상을 투자한 투자자 수")
                    col2.metric("평균 비중", f"{row['avg_conviction']}%", help="5%↑ 투자자들의 평균 투자 비중")
                    col3.metric("최대 비중", f"{row['max_conviction']}%", help="가장 많이 투자한 투자자의 비중")
                    st.markdown(f"**보유 투자자**: {row['holders']}")
        else:
            st.info("현재 고확신 종목 데이터가 없습니다.")

    with tab4:
        st.subheader("🔍 미국 주식 종목 검색 및 분석")
        st.markdown("*티커(심볼)를 입력하면 차트, 기술적 지표, 슈퍼투자자 보유 현황을 종합 분석합니다*")

        # 인기 종목 버튼 클릭 시 설정된 값 확인
        default_us_symbol = st.session_state.get("_selected_us_stock", "")
        if default_us_symbol:
            del st.session_state["_selected_us_stock"]

        us_symbol = st.text_input(
            "티커(심볼) 입력",
            value=default_us_symbol,
            placeholder="예: AAPL, MSFT, GOOGL, TSLA, NVDA...",
            key="us_stock_search"
        ).strip().upper()

        if us_symbol:
            with st.spinner(f"{us_symbol} 분석 중..."):
                analysis = cached_us_stock_analysis(us_symbol)

            if analysis.get('error'):
                st.error(f"오류: {analysis['error']}")
            else:
                # 기본 정보
                st.markdown(f"## {analysis['name']} ({analysis['symbol']})")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric(
                    "현재가",
                    f"${analysis['current_price']:,.2f}",
                    f"{analysis['change_pct']:+.2f}%"
                )
                col2.metric("시가총액", f"${analysis['market_cap']/1e9:,.1f}B" if analysis['market_cap'] > 0 else "-")
                col3.metric("PER", f"{analysis['pe_ratio']:.1f}" if analysis['pe_ratio'] > 0 else "-")
                col4.metric("배당률", f"{analysis['dividend_yield']:.2f}%" if analysis['dividend_yield'] > 0 else "-")

                # 매수 판단
                st.markdown("---")
                col1, col2 = st.columns([1, 2])
                with col1:
                    # 점수 게이지
                    score = analysis['buy_score']
                    if score >= 75:
                        score_color = "🟢"
                    elif score >= 60:
                        score_color = "🟡"
                    elif score >= 40:
                        score_color = "🟠"
                    else:
                        score_color = "🔴"
                    st.metric("매수 점수", f"{score_color} {score}점 / 100점")
                    st.markdown(f"### {analysis['recommendation']}")

                with col2:
                    st.markdown("**📊 분석 신호:**")
                    if analysis['signals']:
                        for sig in analysis['signals']:
                            st.markdown(f"- {sig}")
                    else:
                        st.markdown("- 특별한 신호 없음")

                # 기술적 지표
                st.markdown("---")
                st.subheader("📈 기술적 지표")

                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("MA5", f"${analysis['ma5']:,.2f}" if analysis['ma5'] > 0 else "-")
                col2.metric("MA20", f"${analysis['ma20']:,.2f}" if analysis['ma20'] > 0 else "-")
                col3.metric("MA60", f"${analysis['ma60']:,.2f}" if analysis['ma60'] > 0 else "-")

                rsi = analysis['rsi']
                rsi_status = "과매수" if rsi > 70 else "과매도" if rsi < 30 else "중립"
                col4.metric(f"RSI ({rsi_status})", f"{rsi:.1f}")

                macd_status = "+" if analysis['macd_hist'] > 0 else "-"
                col5.metric(f"MACD ({macd_status})", f"{analysis['macd']:.2f}")

                col1, col2, col3 = st.columns(3)
                col1.metric("52주 최고", f"${analysis['week_52_high']:,.2f}" if analysis['week_52_high'] > 0 else "-")
                col2.metric("52주 최저", f"${analysis['week_52_low']:,.2f}" if analysis['week_52_low'] > 0 else "-")
                if analysis['week_52_low'] > 0:
                    from_low = ((analysis['current_price'] - analysis['week_52_low']) / analysis['week_52_low']) * 100
                    col3.metric("52주 저점 대비", f"+{from_low:.1f}%")

                # 차트
                candles = analysis.get('candles', pd.DataFrame())
                if not candles.empty:
                    st.markdown("---")
                    st.subheader("📊 6개월 차트")

                    # 캔들 + MA 차트
                    fig = go.Figure()

                    fig.add_trace(go.Candlestick(
                        x=candles['date'],
                        open=candles['open'], high=candles['high'],
                        low=candles['low'], close=candles['close'],
                        name="가격"
                    ))

                    if 'ma5' in candles.columns:
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['ma5'],
                            name='MA5 (5일)', line=dict(color='orange', width=1)
                        ))
                    if 'ma20' in candles.columns:
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['ma20'],
                            name='MA20 (20일)', line=dict(color='blue', width=1)
                        ))
                    if 'ma60' in candles.columns:
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['ma60'],
                            name='MA60 (60일)', line=dict(color='purple', width=1)
                        ))

                    # 볼린저밴드
                    if 'bb_upper' in candles.columns:
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['bb_upper'],
                            name='볼린저 상단', line=dict(color='rgba(255,0,0,0.3)', width=1, dash='dot')
                        ))
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['bb_lower'],
                            name='볼린저 하단', line=dict(color='rgba(0,128,0,0.3)', width=1, dash='dot'),
                            fill='tonexty', fillcolor='rgba(173,216,230,0.1)'
                        ))

                    fig.update_layout(
                        title=f"{analysis['name']} 일봉 차트",
                        xaxis_rangeslider_visible=False,
                        height=500,
                        yaxis_title="가격 ($)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # 슈퍼투자자 보유 현황
                if analysis['super_investors']:
                    st.markdown("---")
                    st.subheader(f"👥 슈퍼투자자 보유 현황 ({analysis['num_super_investors']}명)")

                    for inv in analysis['super_investors'][:5]:
                        pct_str = f" — 포트폴리오의 {inv['percent']:.1f}%" if inv['percent'] > 0 else ""
                        st.markdown(f"- **{inv['name']}** (`{inv['investor_id']}`){pct_str}")

                    if analysis['num_super_investors'] > 5:
                        st.caption(f"외 {analysis['num_super_investors'] - 5}명 더 보유")
                else:
                    st.info("이 종목을 보유한 슈퍼투자자가 없습니다.")

        else:
            st.info("💡 미국 주식 티커(심볼)를 입력하세요. 예: AAPL(애플), MSFT(마이크로소프트), NVDA(엔비디아)")

            # 인기 종목 바로가기
            st.markdown("**🔥 인기 종목 바로가기:**")
            popular = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B"]
            cols = st.columns(4)
            for i, sym in enumerate(popular):
                if cols[i % 4].button(sym, key=f"pop_{sym}"):
                    st.session_state["_selected_us_stock"] = sym
                    st.rerun()

    # Disclaimer
    st.markdown("---")
    st.caption("⚠️ **투자 유의사항**: 이 추천은 참고용이며 투자 권유가 아닙니다. 과거 투자자 행동이 미래 수익을 보장하지 않습니다.")
    st.stop()


# Pension Savings page
elif page == "💰 연금저축":
    st.title("💰 연금저축 투자상품 추천")
    st.markdown("*시장 심리 분석 + 뉴스 기반 ETF/자산배분 추천*")

    # 이 페이지에서만 인스턴스 생성
    pension_recommender = get_pension_recommender()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 시장 분석", "📈 ETF 추천", "💎 매집 신호", "🎯 자산배분", "🔥 테마별 추천", "🏆 유망섹터 대장주"])

    with tab1:
        st.subheader("시장 심리 분석")

        with st.spinner("시장 분석 중..."):
            sentiment = pension_recommender.analyze_market_sentiment()
            allocation_result = pension_recommender.get_sentiment_based_allocation()

        # 심리 점수 표시
        col1, col2, col3 = st.columns(3)

        sentiment_emoji = {"bullish": "🟢 강세", "mild_bullish": "🟢 약강세", "neutral": "🟡 중립", "mild_bearish": "🔴 약약세", "bearish": "🔴 약세"}
        col1.metric("시장 심리", sentiment_emoji.get(sentiment.overall, "중립"))
        col2.metric("심리 점수", f"{sentiment.score:+d}")
        col3.metric("추천 성향", allocation_result['risk_level'].upper())

        st.info(f"💡 **분석 결과**: {allocation_result['advice']}")

        # 유망 테마 + 관련 종목
        st.markdown("---")
        st.subheader("🔥 현재 유망 테마 및 관련 종목")

        # 테마 데이터 가져오기 (theme_no 포함)
        trending_themes = pension_recommender.news_scraper.get_trending_themes()

        if trending_themes:
            for theme_data in trending_themes[:5]:
                theme_name = theme_data.get('name', '')
                theme_change = theme_data.get('change', '')
                theme_no = theme_data.get('theme_no', '')

                with st.expander(f"📌 **{theme_name}** ({theme_change})", expanded=False):
                    if theme_no:
                        # 관련 종목 가져오기
                        stocks = pension_recommender.news_scraper.get_theme_stocks(theme_no, 5)
                        if stocks:
                            st.markdown("**관련 종목:**")
                            for i, stock in enumerate(stocks, 1):
                                change_color = "🔴" if "-" in stock.get('change', '') else "🟢"
                                st.markdown(f"{i}. **{stock['name']}** (`{stock['code']}`) - {stock.get('price', '')}원 {change_color} {stock.get('change', '')}")
                        else:
                            st.info("관련 종목 정보를 가져올 수 없습니다.")
                    else:
                        st.info("테마 정보가 부족합니다.")
        else:
            st.info("유망 테마 정보를 가져올 수 없습니다.")

        # 뉴스 요약
        if sentiment.news_summary:
            st.markdown("---")
            st.subheader("📰 최신 뉴스")
            st.write(sentiment.news_summary)

        st.markdown("---")

    with tab2:
        st.subheader("📈 연금저축 ETF 추천")
        st.markdown("*연금저축 계좌에서 투자 가능한 국내 상장 ETF*")

        with st.spinner("ETF 데이터 로딩 중... (최대 1분 소요)"):
            quick_picks = cached_quick_picks(15)

        if not quick_picks.empty:
            # 수익률 차트
            fig = px.bar(
                quick_picks.head(10),
                x='name',
                y='return_1m',
                title="연금저축 ETF 1개월 수익률 TOP 10",
                color='return_1m',
                color_continuous_scale="RdYlGn",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # 테이블
            etf_cols = ['rank', 'symbol', 'name', 'price', 'return_1m', 'return_3m', 'asset_class']
            etf_names = ['순위', '코드', 'ETF명', '현재가', '1개월(%)', '3개월(%)', '자산군']

            if 'sharpe' in quick_picks.columns:
                etf_cols.append('sharpe')
                etf_names.append('샤프비율')
            if 'mdd' in quick_picks.columns:
                etf_cols.append('mdd')
                etf_names.append('MDD(%)')
            if 'rsi' in quick_picks.columns:
                etf_cols.append('rsi')
                etf_names.append('RSI')

            display_df = quick_picks[etf_cols].copy()
            display_df.columns = etf_names
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("ETF 데이터를 가져올 수 없습니다.")

    with tab3:
        st.subheader("💎 ETF 매집 신호")
        st.markdown("*거래량 급증 + 가격 추세 분석으로 매집 신호 포착*")

        st.info("""
        **매집 신호 분석 기준:**
        - 🔥거래량급증: 최근 5일 거래량이 이전 5일 대비 50% 이상 증가
        - 📈거래량증가: 최근 5일 거래량이 이전 5일 대비 20% 이상 증가
        - ⭐강한매집: 가격 상승 + 거래량 증가 동반
        - 🎯세력매집추정: 가격 하락 중 거래량 급증 (저점 매집 가능성)
        """)

        with st.spinner("매집 신호 분석 중..."):
            accumulation_data = cached_pension_accumulation(15)

        if not accumulation_data.empty:
            # 매집 점수 차트
            fig = px.bar(
                accumulation_data.head(10),
                x='name',
                y='accumulation_score',
                title="ETF 매집 점수 TOP 10",
                color='accumulation_score',
                color_continuous_scale="YlOrRd",
                hover_data=['price_change_5d', 'vol_change_pct', 'signals'],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # 상세 테이블
            st.subheader("📋 매집 신호 상세")

            for _, row in accumulation_data.head(10).iterrows():
                with st.expander(f"{row['rank']}. {row['name']} - 점수: {row['accumulation_score']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("현재가", f"{row['price']:,}원")
                    col2.metric("5일 가격변화", f"{row['price_change_5d']:+.1f}%")
                    col3.metric("거래량 변화", f"{row['vol_change_pct']:+.1f}%")

                    st.markdown(f"**신호**: {row['signals']}")
                    st.markdown(f"**자산군**: {row['asset_class']}")
                    st.caption(f"코드: {row['symbol']}")

            # 전체 데이터 테이블
            st.subheader("📊 전체 매집 신호 목록")
            display_df = accumulation_data[['rank', 'symbol', 'name', 'price', 'price_change_5d', 'vol_change_pct', 'accumulation_score', 'signals']].copy()
            display_df.columns = ['순위', '코드', 'ETF명', '현재가', '5일변화(%)', '거래량변화(%)', '매집점수', '신호']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("매집 신호 데이터를 가져올 수 없습니다.")

        # 종합 매수 추천
        st.markdown("---")
        st.subheader("🏆 종합 매수 추천")
        st.markdown("*수익률 + 매집 신호 모두 충족하는 ETF*")

        with st.spinner("종합 분석 중..."):
            buy_recs = pension_recommender.get_buy_recommendations(5)

        if buy_recs['strong_picks']:
            st.success(f"✅ 강력 추천 종목 {len(buy_recs['strong_picks'])}개 발견!")

            for i, pick in enumerate(buy_recs['strong_picks'], 1):
                st.markdown(f"""
                **{i}. {pick['name']}** (`{pick['symbol']}`)
                - 현재가: {pick['price']:,}원 | 1개월 수익률: {pick['return_1m']:+.1f}%
                - 매집점수: {pick['accumulation_score']} | 신호: {pick['signals']}
                """)
        else:
            st.info("현재 수익률과 매집 신호를 동시에 만족하는 종목이 없습니다.")

    with tab4:
        st.subheader("🎯 자산배분 추천")
        st.markdown("*시장 상황에 맞는 자산 배분 전략*")

        # 리스크 수준 선택
        risk_level = st.selectbox(
            "투자 성향 선택",
            ["aggressive", "moderate", "conservative"],
            format_func=lambda x: {"aggressive": "공격적 (주식 비중 높음)", "moderate": "중립적 (균형)", "conservative": "보수적 (채권 비중 높음)"}[x],
            index=1
        )

        allocation = pension_recommender.allocator.get_recommended_allocation(risk_level)

        # 파이 차트
        fig = px.pie(
            names=list(allocation.keys()),
            values=list(allocation.values()),
            title=f"추천 자산배분 ({risk_level})",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 자산군별 비중
        st.subheader("자산군별 추천 비중")
        for asset_class, weight in allocation.items():
            if weight > 0:
                st.progress(weight / 100, text=f"{asset_class}: {weight}%")

        # 자산군별 ETF 추천
        st.subheader("자산군별 추천 ETF")
        for asset_class, weight in allocation.items():
            if weight > 0:
                with st.expander(f"{asset_class} ({weight}%)"):
                    class_etfs = pension_recommender.etf_scraper.get_etfs_by_asset_class(asset_class, 5)
                    if not class_etfs.empty:
                        st.dataframe(
                            class_etfs[['name', 'return_1m', 'price']].head(5),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info(f"{asset_class} ETF 데이터 없음")

    with tab5:
        st.subheader("🔥 테마별 ETF 추천")
        st.markdown("*현재 인기 테마/섹터 관련 ETF*")

        # 테마 선택
        themes = ["반도체", "2차전지", "AI", "바이오", "미국", "배당", "채권", "금리"]
        selected_theme = st.selectbox("테마 선택", themes)

        with st.spinner(f"{selected_theme} 테마 ETF 검색 중..."):
            theme_etfs = pension_recommender.get_theme_etfs(selected_theme, 10)

        if not theme_etfs.empty:
            fig = px.bar(
                theme_etfs,
                x='name',
                y='return_1m',
                title=f"{selected_theme} 테마 ETF 수익률",
                color='return_1m',
                color_continuous_scale="Viridis",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            display_df = theme_etfs[['symbol', 'name', 'price', 'return_1m', 'return_3m']].copy()
            display_df.columns = ['코드', 'ETF명', '현재가', '1개월(%)', '3개월(%)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"{selected_theme} 테마 관련 ETF가 없습니다.")

    with tab6:
        st.subheader("🏆 유망 섹터 대장주")
        st.markdown("*현재 주목받는 섹터와 대표 종목 (1등/2등/3등)*")

        # 섹터 선택
        all_sectors = pension_recommender.get_all_sectors()
        selected_sector = st.selectbox("섹터 선택", all_sectors)

        with st.spinner(f"{selected_sector} 섹터 분석 중..."):
            sector_data = pension_recommender.get_sector_leaders(selected_sector)

        if sector_data['leaders']:
            st.markdown("### 📊 대장주 TOP 3")

            # 대장주 카드 형태로 표시
            cols = st.columns(3)
            medals = ["🥇", "🥈", "🥉"]

            for i, leader in enumerate(sector_data['leaders'][:3]):
                with cols[i]:
                    st.markdown(f"### {medals[i]} {leader['name']}")
                    st.markdown(f"**코드:** `{leader['symbol']}`")
                    st.markdown(f"*{leader['description']}*")

            # 관련 뉴스
            if sector_data['news']:
                st.markdown("### 📰 관련 최신 뉴스")
                for news in sector_data['news'][:5]:
                    st.markdown(f"- [{news['title'][:60]}...]({news['url']})")
        else:
            st.info(f"{selected_sector} 섹터 데이터가 없습니다.")

        # 전체 유망 섹터 요약
        st.markdown("---")
        st.subheader("🔥 현재 유망 섹터 TOP 5")

        with st.spinner("유망 섹터 분석 중..."):
            promising = pension_recommender.get_promising_sectors(5)

        if promising:
            for sector_info in promising:
                with st.expander(f"**{sector_info['sector']}** - 대장주: {sector_info['leaders'][0]['name'] if sector_info['leaders'] else 'N/A'}"):
                    # 대장주 목록
                    if sector_info['leaders']:
                        st.markdown("**대표 종목:**")
                        for leader in sector_info['leaders'][:3]:
                            st.markdown(f"- {leader['rank']}위: **{leader['name']}** (`{leader['symbol']}`) - {leader['description']}")

                    # 관련 뉴스
                    if sector_info['news']:
                        st.markdown("**최신 뉴스:**")
                        for news in sector_info['news'][:3]:
                            st.markdown(f"- [{news['title'][:50]}...]({news['url']})")
        else:
            st.info("유망 섹터 데이터를 가져올 수 없습니다.")

    # Disclaimer
    st.markdown("---")
    st.caption("⚠️ **투자 유의사항**: 이 추천은 참고용이며 투자 권유가 아닙니다. 연금저축 투자는 장기 관점에서 신중하게 결정하세요.")
    st.stop()


# Crypto page
elif page == "🪙 현물코인":
    st.title("🪙 현물코인 시세 및 분석")
    st.caption("📌 v3.1 - entry/stop inline calc")

    crypto_scraper = get_crypto_scraper()
    crypto_recommender = get_crypto_recommender()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 시세 현황", "🔥 급등/급락", "📈 거래량 급증", "🔧 기술적 분석", "🏆 종합 추천"
    ])

    with tab1:
        st.subheader("거래대금 상위 코인")

        # 공포탐욕지수 + 김치프리미엄 표시
        fg_col1, fg_col2, fg_col3 = st.columns(3)
        try:
            fg = crypto_scraper.get_fear_greed_index()
            fg_val = fg['value']
            fg_label = fg['classification']
            fg_color = "🟢" if fg_val < 25 else "🟡" if fg_val < 45 else "🟠" if fg_val < 55 else "🔴" if fg_val < 75 else "🔴"
            fg_col1.metric("공포/탐욕 지수", f"{fg_color} {fg_val} ({fg_label})")
        except Exception:
            fg_col1.metric("공포/탐욕 지수", "N/A")

        try:
            kp = crypto_scraper.get_kimchi_premium()
            avg_kp = kp.get('avg_premium', 0)
            kp_color = "🔴" if avg_kp > 5 else "🟡" if avg_kp > 2 else "🟢" if avg_kp > -1 else "🔵"
            fg_col2.metric("김치프리미엄(평균)", f"{kp_color} {avg_kp:+.2f}%")
            fg_col3.metric("추정 환율", f"₩{kp.get('exchange_rate', 0):,.0f}/USD")
        except Exception:
            fg_col2.metric("김치프리미엄", "N/A")
            fg_col3.metric("추정 환율", "N/A")

        st.markdown("---")

        col1, col2 = st.columns([1, 3])
        with col1:
            exchange = st.radio("거래소", ["업비트 (KRW)", "바이낸스 (USDT)"], key="t1_exchange")
            ex_key = "upbit" if "업비트" in exchange else "binance"
        with col2:
            top_n = st.slider("종목 수", 10, 50, 30, key="t1_topn")

        with st.spinner("시세 데이터 로딩..."):
            top_coins = cached_top_coins(ex_key, top_n)

        if not top_coins.empty:
            # 주요 지표
            col1, col2, col3, col4 = st.columns(4)
            first = top_coins.iloc[0]
            second = top_coins.iloc[1] if len(top_coins) > 1 else first

            if ex_key == "upbit":
                col1.metric(first['name'], f"{first['price']:,.0f}원", f"{first['change_rate']:+.2f}%")
                col2.metric(second['name'], f"{second['price']:,.0f}원", f"{second['change_rate']:+.2f}%")
                col3.metric("상위 코인 수", f"{len(top_coins)}개")
                avg_change = top_coins['change_rate'].mean()
                col4.metric("평균 변동률", f"{avg_change:+.2f}%")
            else:
                col1.metric(first['name'], f"${first['price']:,.2f}", f"{first['change_rate']:+.2f}%")
                col2.metric(second['name'], f"${second['price']:,.2f}", f"{second['change_rate']:+.2f}%")
                col3.metric("상위 코인 수", f"{len(top_coins)}개")
                avg_change = top_coins['change_rate'].mean()
                col4.metric("평균 변동률", f"{avg_change:+.2f}%")

            # 차트
            fig = px.bar(
                top_coins.head(20),
                x='name',
                y='change_rate',
                title=f"{'업비트' if ex_key == 'upbit' else '바이낸스'} 상위 코인 24시간 변동률",
                color='change_rate',
                color_continuous_scale="RdYlGn",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # 테이블
            if ex_key == "upbit":
                display_cols = ['rank', 'symbol', 'name', 'price', 'change_rate', 'trade_value_억']
                display_df = top_coins[display_cols].copy()
                display_df.columns = ['순위', '심볼', '코인명', '현재가(원)', '변동률(%)', '거래대금(억)']
            else:
                display_cols = ['rank', 'base', 'name', 'price', 'change_rate', 'quote_volume_만달러']
                display_df = top_coins[display_cols].copy()
                display_df.columns = ['순위', '심볼', '코인명', '현재가($)', '변동률(%)', '거래대금(만$)']

            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("시세 데이터를 가져올 수 없습니다.")

    with tab2:
        st.subheader("24시간 급등/급락 코인")

        exchange2 = st.radio("거래소", ["업비트 (KRW)", "바이낸스 (USDT)"], key="t2_exchange", horizontal=True)
        ex_key2 = "upbit" if "업비트" in exchange2 else "binance"

        with st.spinner("데이터 분석 중..."):
            movers = cached_movers(ex_key2, 10)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📈 급등 코인 TOP 10")
            gainers = movers.get('gainers', pd.DataFrame())
            if not gainers.empty:
                fig = px.bar(
                    gainers,
                    x='name',
                    y='change_rate',
                    title="급등 코인",
                    color='change_rate',
                    color_continuous_scale="Greens",
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

                for _, row in gainers.iterrows():
                    price_str = f"{row['price']:,.0f}원" if ex_key2 == "upbit" else f"${row['price']:,.4f}"
                    st.markdown(f"**{row['name']}** | {price_str} | {row['change_rate']:+.2f}%")
            else:
                st.info("데이터 없음")

        with col2:
            st.markdown("### 📉 급락 코인 TOP 10")
            losers = movers.get('losers', pd.DataFrame())
            if not losers.empty:
                fig = px.bar(
                    losers,
                    x='name',
                    y='change_rate',
                    title="급락 코인",
                    color='change_rate',
                    color_continuous_scale="Reds_r",
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

                for _, row in losers.iterrows():
                    price_str = f"{row['price']:,.0f}원" if ex_key2 == "upbit" else f"${row['price']:,.4f}"
                    st.markdown(f"**{row['name']}** | {price_str} | {row['change_rate']:+.2f}%")
            else:
                st.info("데이터 없음")

    with tab3:
        st.subheader("거래량 급증 코인")
        st.markdown("*최근 거래량이 7일 평균 대비 급증한 코인*")

        exchange3 = st.radio("거래소", ["업비트 (KRW)", "바이낸스 (USDT)"], key="t3_exchange", horizontal=True)
        ex_key3 = "upbit" if "업비트" in exchange3 else "binance"

        with st.spinner("거래량 분석 중... (최대 1분 소요)"):
            vol_surge = cached_volume_surge(ex_key3, 15)

        if not vol_surge.empty:
            fig = px.bar(
                vol_surge,
                x='name',
                y='vol_change_pct',
                title="거래량 급증 코인",
                color='vol_change_pct',
                color_continuous_scale="YlOrRd",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            for _, row in vol_surge.iterrows():
                with st.expander(f"{row['rank']}. {row['name']} ({row['symbol']}) - 거래량 {row['vol_change_pct']:+.0f}%"):
                    col1, col2, col3 = st.columns(3)
                    price_str = f"{row['price']:,.0f}원" if ex_key3 == "upbit" else f"${row['price']:,.4f}"
                    col1.metric("현재가", price_str)
                    col2.metric("24h 변동", f"{row['change_24h']:+.2f}%")
                    col3.metric("거래량 변화", f"{row['vol_change_pct']:+.0f}%")
                    st.markdown(f"**신호**: {row['signals']}")
        else:
            st.info("현재 거래량 급증 코인이 없습니다.")

    with tab4:
        st.subheader("개별 코인 기술적 분석")

        exchange4 = st.radio("거래소", ["업비트 (KRW)", "바이낸스 (USDT)"], key="t4_exchange", horizontal=True)
        ex_key4 = "upbit" if "업비트" in exchange4 else "binance"

        # 코인 선택
        with st.spinner("코인 목록 로딩..."):
            coins = cached_top_coins(ex_key4, 30)

        if not coins.empty:
            if ex_key4 == "upbit":
                coin_options = {f"{row['name']} ({row['symbol']})": row['market'] for _, row in coins.iterrows()}
            else:
                coin_options = {f"{row['name']} ({row['base']})": row['symbol'] for _, row in coins.iterrows()}

            selected_coin = st.selectbox("코인 선택", list(coin_options.keys()))
            market_id = coin_options[selected_coin]

            with st.spinner("기술적 분석 중..."):
                analysis = crypto_recommender.get_technical_analysis(market_id, ex_key4)

            if 'error' not in analysis:
                # 지표 표시
                col1, col2, col3, col4, col5 = st.columns(5)
                price_str = f"{analysis['price']:,.0f}원" if ex_key4 == "upbit" else f"${analysis['price']:,.4f}"
                col1.metric("현재가", price_str)
                col2.metric("MA5", f"{analysis['ma5']:,.0f}" if ex_key4 == "upbit" else f"${analysis['ma5']:,.4f}")
                col3.metric("MA20", f"{analysis['ma20']:,.0f}" if ex_key4 == "upbit" else f"${analysis['ma20']:,.4f}")

                rsi_val = analysis['rsi']
                rsi_label = "과매수" if rsi_val > 70 else "과매도" if rsi_val < 30 else "중립"
                col4.metric(f"RSI ({rsi_label})", f"{rsi_val:.1f}")

                macd_cross = analysis.get('macd_cross', 'none')
                macd_label = {'golden': '골든크로스', 'dead': '데드크로스', 'bullish': '강세', 'bearish': '약세'}.get(macd_cross, '-')
                col5.metric("MACD", macd_label)

                # 신호
                if analysis['signals']:
                    st.info("**분석 신호**: " + ", ".join(analysis['signals']))

                # ── 진입점 / 손절 / 목표가 ──
                if analysis.get('entry_point', 0) > 0:
                    st.markdown("### 🎯 진입점 / 손절라인 / 목표가")

                    def _fmt_crypto_price(p, ex):
                        if ex == "upbit":
                            return f"{p:,.0f}원"
                        return f"${p:,.4f}"

                    ec1, ec2, ec3, ec4 = st.columns(4)
                    ec1.metric("🎯 진입점", _fmt_crypto_price(analysis['entry_point'], ex_key4))
                    ec2.metric("🛑 손절라인", _fmt_crypto_price(analysis['stop_loss'], ex_key4),
                               f"{analysis['stop_loss_pct']:+.1f}%")

                    _targets = analysis.get('targets', [])
                    if len(_targets) >= 1:
                        ec3.metric(f"📈 {_targets[0]['label']}", _fmt_crypto_price(_targets[0]['price'], ex_key4),
                                   f"+{_targets[0]['pct']:.1f}%")
                    if len(_targets) >= 2:
                        ec4.metric(f"📈 {_targets[1]['label']}", _fmt_crypto_price(_targets[1]['price'], ex_key4),
                                   f"+{_targets[1]['pct']:.1f}%")

                    # 위험/보상 비율
                    _rr = analysis.get('risk_reward_ratio', 0)
                    _rr_emoji = "🟢 양호" if _rr >= 2 else "🟡 보통" if _rr >= 1 else "🔴 주의"
                    st.markdown(f"**위험/보상 비율**: {_rr_emoji} ({_rr:.2f}:1) — {'높을수록 유리' if _rr < 2 else '매수 유리'}")

                    # 지지선/저항선
                    sup_col, res_col = st.columns(2)
                    with sup_col:
                        st.markdown("**🟢 주요 지지선**")
                        for _lvl in analysis.get('support_levels', [])[:3]:
                            st.markdown(f"- {_fmt_crypto_price(_lvl['price'], ex_key4)} (강도: {'●' * min(_lvl['strength'], 5)})")
                    with res_col:
                        st.markdown("**🔴 주요 저항선**")
                        for _lvl in analysis.get('resistance_levels', [])[:3]:
                            st.markdown(f"- {_fmt_crypto_price(_lvl['price'], ex_key4)} (강도: {'●' * min(_lvl['strength'], 5)})")

                    st.markdown("---")

                # 캔들차트 + MA + 볼린저밴드
                candles = analysis.get('candles', pd.DataFrame())
                if not candles.empty:
                    fig = go.Figure()

                    fig.add_trace(go.Candlestick(
                        x=candles['date'],
                        open=candles['open'], high=candles['high'],
                        low=candles['low'], close=candles['close'],
                        name="가격"
                    ))

                    if 'ma5' in candles.columns:
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['ma5'],
                            name='MA5', line=dict(color='orange', width=1.5)
                        ))
                    if 'ma20' in candles.columns:
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['ma20'],
                            name='MA20', line=dict(color='blue', width=1.5)
                        ))

                    # 볼린저밴드
                    if 'bb_upper' in candles.columns:
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['bb_upper'],
                            name='BB Upper', line=dict(color='rgba(255,0,0,0.3)', width=1, dash='dot')
                        ))
                        fig.add_trace(go.Scatter(
                            x=candles['date'], y=candles['bb_lower'],
                            name='BB Lower', line=dict(color='rgba(0,128,0,0.3)', width=1, dash='dot'),
                            fill='tonexty', fillcolor='rgba(173,216,230,0.1)'
                        ))

                    # 지지/저항/진입/손절 수평선 오버레이
                    if analysis.get('entry_point', 0) > 0:
                        # 지지선 (초록 점선)
                        for _sl in analysis.get('support_levels', [])[:2]:
                            fig.add_hline(y=_sl['price'], line_dash="dash", line_color="green",
                                          annotation_text=f"지지", annotation_position="bottom right",
                                          line_width=1, opacity=0.6)
                        # 저항선 (빨강 점선)
                        for _rl in analysis.get('resistance_levels', [])[:2]:
                            fig.add_hline(y=_rl['price'], line_dash="dash", line_color="red",
                                          annotation_text=f"저항", annotation_position="top right",
                                          line_width=1, opacity=0.6)
                        # 진입점 (파랑 실선)
                        fig.add_hline(y=analysis['entry_point'], line_dash="solid", line_color="blue",
                                      line_width=2, opacity=0.8,
                                      annotation_text="진입점", annotation_position="bottom left")
                        # 손절라인 (마젠타 점선)
                        fig.add_hline(y=analysis['stop_loss'], line_dash="dot", line_color="magenta",
                                      line_width=2, opacity=0.8,
                                      annotation_text="손절", annotation_position="bottom left")
                        # 1차 목표 (골드 점선)
                        _tgts = analysis.get('targets', [])
                        if _tgts:
                            fig.add_hline(y=_tgts[0]['price'], line_dash="dashdot", line_color="gold",
                                          line_width=1.5, opacity=0.7,
                                          annotation_text="1차 목표", annotation_position="top left")

                    fig.update_layout(
                        title=f"{analysis['name']} 일봉 차트 (MA + 볼린저밴드 + 진입/손절)",
                        xaxis_rangeslider_visible=False,
                        height=500,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # MACD 차트
                    if 'macd' in candles.columns:
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(
                            x=candles['date'], y=candles['macd'],
                            name='MACD', line=dict(color='blue', width=1.5)
                        ))
                        fig_macd.add_trace(go.Scatter(
                            x=candles['date'], y=candles['macd_signal'],
                            name='Signal', line=dict(color='red', width=1.5)
                        ))
                        if 'macd_hist' in candles.columns:
                            colors = ['green' if v >= 0 else 'red' for v in candles['macd_hist']]
                            fig_macd.add_trace(go.Bar(
                                x=candles['date'], y=candles['macd_hist'],
                                name='Histogram', marker_color=colors, opacity=0.5
                            ))
                        fig_macd.update_layout(title='MACD (12, 26, 9)', height=300)
                        st.plotly_chart(fig_macd, use_container_width=True)

                    # RSI 차트
                    rsi_values = []
                    for i in range(14, len(candles)):
                        r = crypto_recommender._calculate_rsi(candles['close'].iloc[:i+1])
                        rsi_values.append({'date': candles['date'].iloc[i], 'RSI': r})

                    if rsi_values:
                        rsi_df = pd.DataFrame(rsi_values)
                        fig_rsi = px.line(rsi_df, x='date', y='RSI', title='RSI (14일)')
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="과매수")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="과매도")
                        fig_rsi.update_layout(height=300)
                        st.plotly_chart(fig_rsi, use_container_width=True)
            else:
                st.warning("분석 데이터를 가져올 수 없습니다.")
        else:
            st.warning("코인 목록을 가져올 수 없습니다.")

    with tab5:
        st.subheader("종합 추천 코인")
        st.markdown("*모멘텀 + 거래량 + 기술적 분석 종합 점수*")

        exchange5 = st.radio("거래소", ["업비트 (KRW)", "바이낸스 (USDT)"], key="t5_exchange", horizontal=True)
        ex_key5 = "upbit" if "업비트" in exchange5 else "binance"

        st.info("""
        **점수 산정 기준 (최대 ~130점):**
        - 모멘텀 (24h/5일 변화율): 최대 20점
        - 거래량 급증: 최대 15점
        - 기술적 분석 (MA/RSI): 최대 20점
        - 거래대금 순위: 최대 10점
        - 추세 지속성 (연속양봉): 최대 10점
        - **MACD (골든/데드크로스)**: 최대 15점
        - **볼린저밴드 (과매수/과매도)**: 최대 15점
        - **공포탐욕지수**: 최대 15점
        - **김치프리미엄 (업비트만)**: 최대 10점

        📌 **각 코인별 진입점/손절라인/목표가도 표시됩니다.**
        - 🎯 진입점: 지지선 기반 최적 매수가
        - 🛑 손절: 주요 지지선 하단 -3%
        - 📈 목표가: 저항선 기반
        - 위험/보상: 🟢 2:1 이상 = 매수 유리
        """)

        with st.spinner("종합 분석 중... (최대 2분 소요)"):
            recommendations = cached_crypto_recommendations(ex_key5, 20)

        if not recommendations.empty:
            # 진입점/손절/목표가 0인 경우 RSI+MA20 기반 개별 보정
            for idx in recommendations.index:
                if recommendations.at[idx, 'entry_point'] == 0 and recommendations.at[idx, 'price'] > 0:
                    p = float(recommendations.at[idx, 'price'])
                    rsi = float(recommendations.at[idx, 'rsi']) if 'rsi' in recommendations.columns else 50
                    ma20 = float(recommendations.at[idx, 'ma20']) if 'ma20' in recommendations.columns and recommendations.at[idx, 'ma20'] > 0 else p

                    # RSI 기반 진입점 (과매도일수록 현재가에 가깝게)
                    if rsi < 30:
                        entry = round(p, 2)           # 과매도: 현재가 매수
                    elif rsi < 40:
                        entry = round(p * 0.99, 2)    # 약세: -1%
                    elif ma20 < p:
                        entry = round(ma20, 2)        # MA20 지지선
                    else:
                        entry = round(p * 0.97, 2)    # 기본: -3%

                    # RSI 기반 손절 (과매도면 타이트, 과매수면 넓게)
                    if rsi < 30:
                        sl_pct = 0.95   # -5%
                    elif rsi < 50:
                        sl_pct = 0.93   # -7%
                    else:
                        sl_pct = 0.90   # -10%
                    stop = round(entry * sl_pct, 2)
                    stop_pct = round((stop - entry) / entry * 100, 1) if entry > 0 else -5.0

                    # RSI 기반 목표가 (과매도면 반등폭 크게)
                    if rsi < 30:
                        tgt_mult = 1.15  # +15%
                    elif rsi < 50:
                        tgt_mult = 1.08  # +8%
                    else:
                        tgt_mult = 1.05  # +5%
                    target = round(p * tgt_mult, 2)
                    target_pct = round((target - entry) / entry * 100, 1) if entry > 0 else 5.0

                    # 위험/보상 비율
                    risk = abs(entry - stop) if entry > 0 else 1
                    reward = abs(target - entry) if entry > 0 else 1
                    rr = round(reward / risk, 1) if risk > 0 else 1.0

                    recommendations.at[idx, 'entry_point'] = entry
                    recommendations.at[idx, 'stop_loss'] = stop
                    recommendations.at[idx, 'stop_loss_pct'] = stop_pct
                    recommendations.at[idx, 'target_1'] = target
                    recommendations.at[idx, 'target_1_pct'] = target_pct
                    recommendations.at[idx, 'risk_reward'] = rr

            # 점수 차트
            fig = px.bar(
                recommendations.head(15),
                x='name',
                y='score',
                title=f"{'업비트' if ex_key5 == 'upbit' else '바이낸스'} 종합 추천 TOP 15",
                color='score',
                color_continuous_scale="Bluered",
                hover_data=['symbol', 'change_24h', 'rsi'],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # 상세 카드
            st.subheader("📋 추천 상세")
            for _, row in recommendations.head(10).iterrows():
                with st.expander(f"{row['rank']}. {row['name']} ({row['symbol']}) - 점수: {row['score']}"):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    price_str = f"{row['price']:,.0f}원" if ex_key5 == "upbit" else f"${row['price']:,.4f}"
                    col1.metric("현재가", price_str)
                    col2.metric("24h 변동", f"{row['change_24h']:+.2f}%")
                    col3.metric("RSI", f"{row['rsi']:.0f}")
                    macd_kr = {'golden': '골든크로스', 'dead': '데드크로스', 'bullish': '강세', 'bearish': '약세'}.get(row.get('macd_cross', ''), '-')
                    col4.metric("MACD", macd_kr)
                    col5.metric("총점", f"{row['score']:.1f}")

                    macd_s = row.get('macd_score', 0)
                    bb_s = row.get('bb_score', 0)
                    st.markdown(f"**모멘텀**: {row['momentum_score']}점 | **거래량**: {row['volume_score']}점 | **기술적**: {row['technical_score']}점 | **MACD**: {macd_s}점 | **볼린저**: {bb_s}점")

                    # 진입점 / 손절 / 목표가
                    if row.get('entry_point', 0) > 0:
                        st.markdown("---")
                        e1, e2, e3, e4 = st.columns(4)
                        if ex_key5 == "upbit":
                            e1.metric("🎯 진입점", f"{row['entry_point']:,.0f}원")
                            e2.metric("🛑 손절", f"{row['stop_loss']:,.0f}원", f"{row['stop_loss_pct']:+.1f}%")
                            if row.get('target_1', 0) > 0:
                                e3.metric("📈 1차 목표", f"{row['target_1']:,.0f}원", f"+{row['target_1_pct']:.1f}%")
                        else:
                            e1.metric("🎯 진입점", f"${row['entry_point']:,.4f}")
                            e2.metric("🛑 손절", f"${row['stop_loss']:,.4f}", f"{row['stop_loss_pct']:+.1f}%")
                            if row.get('target_1', 0) > 0:
                                e3.metric("📈 1차 목표", f"${row['target_1']:,.4f}", f"+{row['target_1_pct']:.1f}%")
                        _rr = row.get('risk_reward', 0)
                        _rr_icon = "🟢" if _rr >= 2 else "🟡" if _rr >= 1 else "🔴"
                        e4.metric("위험/보상", f"{_rr_icon} {_rr:.1f}:1")

                    st.markdown(f"**신호**: {row['signals']}")

            # 전체 테이블
            st.subheader("📊 전체 추천 목록")
            rec_cols = ['rank', 'symbol', 'name', 'price', 'change_24h', 'score',
                         'entry_point', 'stop_loss', 'stop_loss_pct', 'target_1',
                         'rsi', 'risk_reward', 'signals']
            rec_names = ['순위', '심볼', '코인명', '현재가', '24h(%)', '점수',
                          '진입점', '손절', '손절(%)', '1차목표',
                          'RSI', '위험/보상', '신호']

            # 컬럼이 없는 경우 안전 처리
            available_cols = [c for c in rec_cols if c in recommendations.columns]
            available_names = [rec_names[rec_cols.index(c)] for c in available_cols]

            display_df = recommendations[available_cols].copy()
            display_df.columns = available_names
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("추천 데이터를 가져올 수 없습니다.")

    # Disclaimer
    st.markdown("---")
    st.caption("⚠️ **투자 유의사항**: 이 추천은 참고용이며 투자 권유가 아닙니다. 암호화폐는 높은 변동성을 가지므로 투자에 주의하세요.")
    st.stop()
