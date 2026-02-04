"""Streamlit web dashboard for Investor Tracker."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys
import importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Force reload Korean stock modules to avoid stale class definitions
import src.scrapers.korean_stocks as korean_stocks_module
import src.analyzers.korean_recommender as korean_recommender_module
import src.scrapers.pension_etf as pension_etf_module
import src.analyzers.pension_recommender as pension_recommender_module
import src.scrapers.crypto as crypto_module
import src.analyzers.crypto_recommender as crypto_recommender_module
importlib.reload(korean_stocks_module)
importlib.reload(korean_recommender_module)
importlib.reload(pension_etf_module)
importlib.reload(pension_recommender_module)
importlib.reload(crypto_module)
importlib.reload(crypto_recommender_module)

from src.scrapers.dataroma import DataromaScraper
from src.scrapers.korean_stocks import KoreanStocksScraper
from src.scrapers.crypto import CryptoScraper
from src.analyzers.overlap import OverlapAnalyzer
from src.analyzers.changes import ChangesAnalyzer
from src.analyzers.korean_recommender import KoreanStockRecommender
from src.analyzers.pension_recommender import PensionRecommender
from src.analyzers.crypto_recommender import CryptoRecommender
from src.storage.database import Database

# Page config
st.set_page_config(
    page_title="Investor Tracker",
    page_icon="📊",
    layout="wide",
)

# Auto refresh every 5 minutes (300 seconds)
st.markdown(
    '<meta http-equiv="refresh" content="300">',
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
    [data-testid="collapsedControl"]::after {
        content: " 메뉴" !important;
        color: white !important;
        font-size: 14px !important;
        font-weight: bold !important;
        margin-left: 4px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Initialize
@st.cache_resource
def get_scraper():
    return DataromaScraper()

@st.cache_resource
def get_database():
    db = Database()
    db.init_db()
    return db

# Create fresh instances (no caching for Korean modules to avoid stale class issues)
scraper = get_scraper()
db = get_database()

# 각 페이지별로 필요한 인스턴스만 지연 생성하는 함수
def get_kr_scraper():
    return KoreanStocksScraper()

def get_recommender():
    return KoreanStockRecommender()

def get_pension_recommender():
    return PensionRecommender()

def get_crypto_scraper():
    return CryptoScraper()

def get_crypto_recommender():
    return CryptoRecommender()


# 메뉴 목록
MENU_ITEMS = ["🏠 홈", "💼 포트폴리오", "🔍 공통 종목", "📈 변화 분석", "🌐 Grand Portfolio", "🇰🇷 국내주식", "🎯 종목 추천", "💰 연금저축", "🪙 현물코인"]

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


# Home page
if page == "🏠 홈":
    st.title("🎯 Investor Tracker")
    st.markdown("슈퍼투자자들의 포트폴리오를 추적하고 분석합니다.")

    # Quick stats
    col1, col2, col3 = st.columns(3)

    with st.spinner("데이터 로딩 중..."):
        investors_df = scraper.get_investor_list()

    with col1:
        st.metric("추적 투자자 수", len(investors_df) if not investors_df.empty else 0)
    with col2:
        st.metric("대표 투자자", "Warren Buffett")
    with col3:
        st.metric("데이터 소스", "Dataroma / SEC")

    st.markdown("---")
    st.subheader("메뉴 바로가기")

    # 모바일용 메뉴 버튼 (2열 배치)
    menu_buttons = [
        ("💼", "포트폴리오", "개별 투자자 보유 종목 조회", "💼 포트폴리오"),
        ("🔍", "공통 종목", "투자자 공통 보유 종목", "🔍 공통 종목"),
        ("📈", "변화 분석", "분기별 매수/매도 추적", "📈 변화 분석"),
        ("🌐", "Grand Portfolio", "전체 통합 포트폴리오", "🌐 Grand Portfolio"),
        ("🇰🇷", "국내주식", "투자자 동향/공매도/매집", "🇰🇷 국내주식"),
        ("🎯", "종목 추천", "AI 종합 종목 추천", "🎯 종목 추천"),
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


# Portfolio page
elif page == "💼 포트폴리오":
    st.title("💼 투자자 포트폴리오")

    # Get investor list
    with st.spinner("투자자 목록 로딩..."):
        investors_df = scraper.get_investor_list()

    if investors_df.empty:
        st.error("투자자 목록을 가져올 수 없습니다.")
    else:
        # Investor selector
        investor_options = {
            f"{row['name']} ({row['investor_id']})": row['investor_id']
            for _, row in investors_df.iterrows()
        }

        col1, col2 = st.columns([3, 1])
        with col1:
            selected = st.selectbox("투자자 선택", list(investor_options.keys()))
        with col2:
            top_n = st.number_input("상위 종목 수", min_value=5, max_value=50, value=15)

        investor_id = investor_options[selected]

        # Load portfolio
        with st.spinner(f"{investor_id} 포트폴리오 로딩..."):
            portfolio = scraper.get_portfolio(investor_id)

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
            display_df = portfolio.head(top_n)[["symbol", "stock", "percent_portfolio", "shares", "value", "activity"]]
            display_df.columns = ["심볼", "종목명", "비중(%)", "주식수", "가치($)", "최근활동"]
            st.dataframe(display_df, use_container_width=True)


# Overlap page
elif page == "🔍 공통 종목":
    st.title("🔍 공통 종목 분석")

    # Get investor list
    with st.spinner("투자자 목록 로딩..."):
        investors_df = scraper.get_investor_list()

    if investors_df.empty:
        st.error("투자자 목록을 가져올 수 없습니다.")
    else:
        investor_options = {
            f"{row['name']} ({row['investor_id']})": row['investor_id']
            for _, row in investors_df.iterrows()
        }

        selected_investors = st.multiselect(
            "분석할 투자자 선택 (2명 이상)",
            list(investor_options.keys()),
            default=list(investor_options.keys())[:3] if len(investor_options) >= 3 else list(investor_options.keys())
        )

        col1, col2 = st.columns(2)
        with col1:
            min_owners = st.slider("최소 보유자 수", 2, len(selected_investors) if selected_investors else 2, 2)
        with col2:
            use_conviction = st.checkbox("확신도 점수 사용", value=False)

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
                    fig = px.bar(
                        result.head(20),
                        x="symbol",
                        y="num_owners" if not use_conviction else "conviction_score",
                        title="공통 보유 종목",
                        color="avg_percent",
                        color_continuous_scale="Greens",
                        hover_data=["stock", "avg_percent"],
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Table
                    st.dataframe(result.head(30), use_container_width=True)
                else:
                    st.info(f"{min_owners}명 이상이 공통 보유한 종목이 없습니다.")
            else:
                st.warning("분석 결과가 없습니다.")
        else:
            st.info("2명 이상의 투자자를 선택하세요.")


# Changes page
elif page == "📈 변화 분석":
    st.title("📈 분기별 변화 분석")

    col1, col2 = st.columns(2)

    with col1:
        investor_id = st.text_input("투자자 ID", value="BRK")
    with col2:
        # Check available quarters
        quarters = db.get_available_quarters(investor_id)
        st.write(f"저장된 분기: {quarters if quarters else '없음'}")

    col1, col2, col3 = st.columns(3)
    with col1:
        q1 = st.text_input("이전 분기", value="2024Q3")
    with col2:
        q2 = st.text_input("현재 분기", value="2024Q4")
    with col3:
        if st.button("현재 데이터 동기화"):
            with st.spinner("동기화 중..."):
                analyzer = ChangesAnalyzer(db=db, scraper=scraper)
                analyzer.sync_portfolio(investor_id, q2)
                st.success(f"{investor_id} 포트폴리오를 {q2}로 저장했습니다.")
                st.rerun()

    if st.button("변화 분석"):
        analyzer = ChangesAnalyzer(db=db, scraper=scraper)
        changes = analyzer.compare_quarters(investor_id, q1, q2)

        if changes.empty:
            st.info("변화가 없거나 데이터가 부족합니다.")
        else:
            # Summary
            summary = analyzer.get_activity_summary(investor_id, q1, q2)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("신규 매수", summary["new_positions"], delta_color="normal")
            col2.metric("완전 매도", summary["exits"], delta_color="inverse")
            col3.metric("비중 증가", summary["increases"])
            col4.metric("비중 감소", summary["decreases"])

            # Charts
            col1, col2 = st.columns(2)

            with col1:
                new_df = changes[changes["change_type"] == "NEW"]
                if not new_df.empty:
                    fig = px.bar(new_df, x="symbol", y="curr_percent", title="신규 매수 종목", color_discrete_sequence=["green"])
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                exit_df = changes[changes["change_type"] == "EXIT"]
                if not exit_df.empty:
                    fig = px.bar(exit_df, x="symbol", y="prev_percent", title="매도 종목", color_discrete_sequence=["red"])
                    st.plotly_chart(fig, use_container_width=True)

            # Full table
            st.subheader("전체 변화 내역")
            st.dataframe(changes, use_container_width=True)


# Grand Portfolio page
elif page == "🌐 Grand Portfolio":
    st.title("🌐 Grand Portfolio")
    st.markdown("*전체 슈퍼투자자들이 가장 많이 보유한 종목*")

    with st.spinner("Grand Portfolio 로딩..."):
        grand = scraper.get_grand_portfolio()

    if grand.empty:
        st.error("데이터를 가져올 수 없습니다.")
    else:
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
        fig.update_layout(xaxis_tickangle=-45, yaxis_title="보유 투자자 수")
        st.plotly_chart(fig, use_container_width=True)

        # Table
        display_cols = ["symbol", "stock", "num_owners", "percent_total"]
        col_names = ["종목코드", "종목명", "보유 투자자 수", "비중(%)"]

        if "current_price" in grand.columns:
            display_cols.append("current_price")
            col_names.append("현재가($)")
        if "hold_price" in grand.columns:
            display_cols.append("hold_price")
            col_names.append("매입가($)")

        display_df = grand.head(50)[display_cols].copy()
        display_df.columns = col_names
        st.dataframe(display_df, use_container_width=True, hide_index=True)


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
                foreign_df = kr_scraper.get_foreign_buying(20)

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
                inst_df = kr_scraper.get_institution_buying(20)

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
            cap_df = kr_scraper.get_market_cap_top(market, top_n)

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
            short_df = kr_scraper.get_short_volume(short_market, 30)

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
            acc_signals = kr_recommender.get_accumulation_signals(acc_market, 20)

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
            strong_candidates = kr_recommender.get_strong_buy_candidates(acc_market, 5)

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
        st.subheader("종목 검색")

        query = st.text_input("종목명 또는 코드 입력", placeholder="삼성전자, 005930")

        if query:
            with st.spinner("검색 중..."):
                results = kr_scraper.search_stock(query)

            if not results.empty:
                st.dataframe(results, use_container_width=True, hide_index=True)

                # Show selected stock details
                if len(results) > 0:
                    selected_symbol = st.selectbox(
                        "종목 선택",
                        results['symbol'].tolist(),
                        format_func=lambda x: f"{x} - {results[results['symbol']==x]['name'].values[0]}"
                    )

                    if selected_symbol:
                        with st.spinner("종목 정보 로딩..."):
                            stock_info = kr_scraper.get_stock_price(selected_symbol)

                        if stock_info:
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("종목명", stock_info.get('name', ''))
                            col2.metric("현재가", f"{stock_info.get('close', 0):,}원")
                            col3.metric("거래량", f"{stock_info.get('volume', 0):,}")
                            col4.metric("등락률", f"{stock_info.get('change', 0):.2f}%")
            else:
                st.info("검색 결과가 없습니다.")

    with tab6:
        st.subheader("📋 DART 전자공시")
        st.markdown("*최근 주요 공시 (대량보유, 주요사항, 공정공시 등)*")

        col_period, col_types = st.columns([1, 3])
        with col_period:
            dart_days = st.selectbox("조회 기간", [3, 7, 14, 30], index=1,
                                      format_func=lambda x: f"최근 {x}일",
                                      key="dart_days")

        type_options = {
            '대량보유': 'B001',
            '주요사항': 'C',
            '공정공시': 'D',
            '사업보고서': 'A001',
            '기타공시': 'E',
        }
        with col_types:
            selected_labels = st.multiselect(
                "공시 유형",
                options=list(type_options.keys()),
                default=['대량보유', '주요사항', '공정공시'],
                key="dart_types"
            )

        selected_types = [type_options[label] for label in selected_labels] if selected_labels else None

        with st.spinner("DART 공시 로딩..."):
            disclosures = kr_scraper.get_recent_disclosures(days=dart_days, report_types=selected_types)

        if not disclosures.empty:
            st.success(f"총 {len(disclosures)}건의 공시")

            for _, row in disclosures.iterrows():
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

        st.markdown("---")
        st.subheader("🔍 기업별 공시 검색")

        company_query = st.text_input("기업명 입력", placeholder="삼성전자", key="dart_company_search")

        if company_query:
            with st.spinner(f"'{company_query}' 공시 검색 중..."):
                company_disclosures = kr_scraper.search_company_disclosures(company_query, days=30)

            if not company_disclosures.empty:
                st.success(f"'{company_query}' 관련 공시 {len(company_disclosures)}건")

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

                with st.expander("공시 원문 링크"):
                    for _, row in company_disclosures.iterrows():
                        st.markdown(f"- [{row['company']} - {row['title']}]({row['url']})")
            else:
                st.info(f"'{company_query}' 관련 최근 30일 공시가 없습니다.")


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

    tab1, tab2, tab3 = st.tabs(["🏆 종합 추천", "⭐ 동반 매수", "🔥 역발상 매수"])

    with tab1:
        st.subheader("종합 추천 TOP 20")

        with st.spinner("데이터 분석 중..."):
            recs = recommender.get_recommendations(top_n=20)

        if not recs.empty:
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

            # Detailed table
            st.subheader("상세 정보")
            available_cols = ['rank', 'symbol', 'name', 'score', 'signals', 'foreign_억', 'inst_억', 'short_ratio']
            col_names = ['순위', '코드', '종목명', '점수', '시그널', '외국인(억)', '기관(억)', '공매도(%)']

            # 새 지표 컬럼이 있으면 추가
            if 'per' in recs.columns:
                available_cols.append('per')
                col_names.append('PER')
            if 'pbr' in recs.columns:
                available_cols.append('pbr')
                col_names.append('PBR')
            if 'rsi' in recs.columns:
                available_cols.append('rsi')
                col_names.append('RSI')

            display_df = recs[available_cols].copy()
            display_df.columns = col_names
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # 추천 종목 최근 공시
            st.markdown("---")
            st.subheader("📋 추천 종목 최근 공시")

            top_stock_names = recs.head(5)['name'].tolist()

            with st.spinner("추천 종목 공시 조회 중..."):
                rec_kr_scraper = get_kr_scraper()
                rec_disclosures = rec_kr_scraper.get_disclosures_for_stocks(top_stock_names, days=14)

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
            dual = recommender.get_dual_buying_stocks()

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
            contra = recommender.get_contrarian_picks()

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

    # Disclaimer
    st.markdown("---")
    st.caption("⚠️ **투자 유의사항**: 이 추천은 참고용이며 투자 권유가 아닙니다. 투자 결정은 본인의 판단과 책임하에 하시기 바랍니다.")


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
            quick_picks = pension_recommender.get_quick_picks(15)

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
            accumulation_data = pension_recommender.get_accumulation_signals(15)

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


# Crypto page
elif page == "🪙 현물코인":
    st.title("🪙 현물코인 시세 및 분석")

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
            top_coins = crypto_scraper.get_top_coins(ex_key, top_n)

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
            movers = crypto_scraper.get_movers(ex_key2, 10)

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
            vol_surge = crypto_recommender.get_volume_surge_coins(ex_key3, 15)

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
            coins = crypto_scraper.get_top_coins(ex_key4, 30)

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

                    fig.update_layout(
                        title=f"{analysis['name']} 일봉 차트 (MA + 볼린저밴드)",
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
        """)

        with st.spinner("종합 분석 중... (최대 2분 소요)"):
            recommendations = crypto_recommender.get_recommendations(ex_key5, 20)

        if not recommendations.empty:
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
                    st.markdown(f"**신호**: {row['signals']}")

            # 전체 테이블
            st.subheader("📊 전체 추천 목록")
            rec_cols = ['rank', 'symbol', 'name', 'price', 'change_24h', 'score', 'rsi', 'vol_change_pct', 'signals']
            rec_names = ['순위', '심볼', '코인명', '현재가', '24h(%)', '점수', 'RSI', '거래량변화(%)', '신호']

            if 'macd_cross' in recommendations.columns:
                rec_cols.insert(7, 'macd_cross')
                rec_names.insert(7, 'MACD')

            display_df = recommendations[rec_cols].copy()
            display_df.columns = rec_names
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("추천 데이터를 가져올 수 없습니다.")

    # Disclaimer
    st.markdown("---")
    st.caption("⚠️ **투자 유의사항**: 이 추천은 참고용이며 투자 권유가 아닙니다. 암호화폐는 높은 변동성을 가지므로 투자에 주의하세요.")


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Made with Streamlit")
st.sidebar.markdown("[GitHub](https://github.com)")
