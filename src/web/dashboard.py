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
importlib.reload(korean_stocks_module)
importlib.reload(korean_recommender_module)
importlib.reload(pension_etf_module)
importlib.reload(pension_recommender_module)

from src.scrapers.dataroma import DataromaScraper
from src.scrapers.korean_stocks import KoreanStocksScraper
from src.analyzers.overlap import OverlapAnalyzer
from src.analyzers.changes import ChangesAnalyzer
from src.analyzers.korean_recommender import KoreanStockRecommender
from src.analyzers.pension_recommender import PensionRecommender
from src.storage.database import Database

# Page config
st.set_page_config(
    page_title="Investor Tracker",
    page_icon="📊",
    layout="wide",
)

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


# Sidebar
st.sidebar.title("📊 Investor Tracker")
page = st.sidebar.radio(
    "메뉴",
    ["🏠 홈", "💼 포트폴리오", "🔍 공통 종목", "📈 변화 분석", "🌐 Grand Portfolio", "🇰🇷 국내주식", "🎯 종목 추천", "💰 연금저축"]
)

# 페이지 전환 시 상태 초기화
if 'current_page' not in st.session_state:
    st.session_state.current_page = page

if st.session_state.current_page != page:
    # 페이지가 변경되면 캐시 클리어 및 상태 업데이트
    st.session_state.current_page = page
    st.cache_data.clear()


# Home page
if page == "🏠 홈":
    st.title("🎯 Investor Tracker")
    st.markdown("""
    슈퍼투자자들의 포트폴리오를 추적하고 분석합니다.

    - **포트폴리오**: 개별 투자자의 보유 종목 조회
    - **공통 종목**: 여러 투자자가 공통으로 보유한 종목 분석
    - **변화 분석**: 분기별 매수/매도 추적
    - **Grand Portfolio**: 전체 슈퍼투자자 통합 포트폴리오
    """)

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
            hover_data=["stock"],
        )
        st.plotly_chart(fig, use_container_width=True)

        # Table
        st.dataframe(grand.head(50), use_container_width=True)


# Korean Stocks page
elif page == "🇰🇷 국내주식":
    st.title("🇰🇷 국내주식 투자자 동향")

    # 이 페이지에서만 인스턴스 생성
    kr_scraper = get_kr_scraper()
    kr_recommender = get_recommender()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 외국인/기관 순매수", "📈 시총 상위", "📉 공매도", "💎 매집 신호", "🔍 종목 검색"])

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


# Recommendation page
elif page == "🎯 종목 추천":
    st.title("🎯 AI 종목 추천")
    st.markdown("*외국인/기관 수급과 공매도 데이터를 종합 분석한 매수 추천*")

    # 이 페이지에서만 인스턴스 생성
    recommender = get_recommender()

    st.info("""
    **점수 산정 기준:**
    - 외국인 순매수 상위 30위: +30점 (순위별 가중)
    - 기관 순매수 상위 30위: +30점 (순위별 가중)
    - 외국인+기관 동반 매수: +20점 (시너지 보너스)
    - 공매도 비중 5% 이하: +10점 / 20% 이상: -10점
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
            display_df = recs[['rank', 'symbol', 'name', 'score', 'signals', 'foreign_억', 'inst_억', 'short_ratio']]
            display_df.columns = ['순위', '코드', '종목명', '점수', '시그널', '외국인(억)', '기관(억)', '공매도(%)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
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

        sentiment_emoji = {"bullish": "🟢 강세", "neutral": "🟡 중립", "bearish": "🔴 약세"}
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
            display_df = quick_picks[['rank', 'symbol', 'name', 'price', 'return_1m', 'return_3m', 'asset_class']].copy()
            display_df.columns = ['순위', '코드', 'ETF명', '현재가', '1개월(%)', '3개월(%)', '자산군']
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


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Made with Streamlit")
st.sidebar.markdown("[GitHub](https://github.com)")
