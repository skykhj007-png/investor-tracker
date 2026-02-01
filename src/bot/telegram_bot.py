"""Telegram bot for Investor Tracker."""

import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..scrapers.dataroma import DataromaScraper
from ..scrapers.korean_stocks import KoreanStocksScraper
from ..analyzers.overlap import OverlapAnalyzer
from ..analyzers.changes import ChangesAnalyzer
from ..analyzers.korean_recommender import KoreanStockRecommender
from ..analyzers.pension_recommender import PensionRecommender
from ..storage.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
scraper = DataromaScraper()
kr_scraper = KoreanStocksScraper()
kr_recommender = KoreanStockRecommender()
pension_recommender = PensionRecommender()
db = Database()


def format_portfolio(df, top: int = 10) -> str:
    """Format portfolio DataFrame as text."""
    if df.empty:
        return "포트폴리오를 찾을 수 없습니다."

    lines = [f"📊 *포트폴리오* (Top {min(top, len(df))})\n"]
    for idx, row in df.head(top).iterrows():
        lines.append(
            f"{idx+1}. *{row['symbol']}* ({row['percent_portfolio']:.1f}%)\n"
            f"   {row['stock'][:20]}\n"
        )
    return "\n".join(lines)


def format_overlap(df, investors: list) -> str:
    """Format overlap DataFrame as text."""
    if df.empty:
        return "공통 종목이 없습니다."

    lines = [f"🔍 *공통 종목* ({', '.join(investors)})\n"]
    for idx, row in df.head(10).iterrows():
        lines.append(
            f"{idx+1}. *{row['symbol']}* - {row['num_owners']}명 보유\n"
            f"   평균 비중: {row['avg_percent']:.1f}%\n"
        )
    return "\n".join(lines)


def format_grand(df) -> str:
    """Format grand portfolio as text."""
    if df.empty:
        return "데이터를 가져올 수 없습니다."

    lines = ["🌐 *Grand Portfolio* (슈퍼투자자 공통)\n"]
    for idx, row in df.head(15).iterrows():
        lines.append(
            f"{idx+1}. *{row['symbol']}* - {row['num_owners']}명\n"
        )
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    welcome = """
🎯 *Investor Tracker Bot*

슈퍼투자자 포트폴리오와 국내주식을 추적합니다.

*🇺🇸 미국주식:*
/portfolio BRK - 포트폴리오 조회
/investors - 투자자 목록
/overlap BRK,psc - 공통 종목 분석
/grand - Grand Portfolio

*🇰🇷 국내주식:*
/외국인 - 외국인 순매수 상위
/기관 - 기관 순매수 상위
/시총 - 시가총액 상위
/공매도 - 공매도 비중 상위
/추천 - 🎯 종목 추천
/kr [종목명] - 종목 검색

*💰 연금저축:*
/연금 - 연금저축 ETF 추천 (NEW!)
/시장분석 - 시장 심리 분석
/자산배분 - 자산배분 추천

/help - 도움말

*주요 투자자 ID:*
• BRK - Warren Buffett
• psc - Bill Ackman
• SAM - Michael Burry
"""
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    help_text = """
*사용법:*

/portfolio [ID] [개수]
  예: /portfolio BRK 10

/investors
  추적 가능한 투자자 목록

/overlap [ID1,ID2,...]
  예: /overlap BRK,psc,GLRE

/grand
  전체 슈퍼투자자 공통 종목

/search [종목]
  예: /search AAPL
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get investor portfolio."""
    args = context.args
    investor_id = args[0].upper() if args else "BRK"
    top = int(args[1]) if len(args) > 1 else 10

    await update.message.reply_text(f"🔄 {investor_id} 포트폴리오 조회 중...")

    try:
        df = scraper.get_portfolio(investor_id)
        response = format_portfolio(df, top)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def investors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all investors."""
    await update.message.reply_text("🔄 투자자 목록 조회 중...")

    try:
        df = scraper.get_investor_list()
        if df.empty:
            await update.message.reply_text("목록을 가져올 수 없습니다.")
            return

        lines = ["📋 *투자자 목록* (상위 20)\n"]
        for idx, row in df.head(20).iterrows():
            lines.append(f"• `{row['investor_id']}` - {row['name'][:25]}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def overlap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze portfolio overlaps."""
    args = context.args
    if not args:
        await update.message.reply_text("사용법: /overlap BRK,psc,GLRE")
        return

    investor_ids = [i.strip().upper() for i in args[0].split(",")]
    if len(investor_ids) < 2:
        await update.message.reply_text("최소 2명의 투자자가 필요합니다.")
        return

    await update.message.reply_text(f"🔄 {len(investor_ids)}명 분석 중...")

    try:
        analyzer = OverlapAnalyzer(scraper=scraper)
        df = analyzer.rank_by_ownership_count(investor_ids)
        df = df[df["num_owners"] >= 2]
        response = format_overlap(df, investor_ids)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def grand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get grand portfolio."""
    await update.message.reply_text("🔄 Grand Portfolio 조회 중...")

    try:
        df = scraper.get_grand_portfolio()
        response = format_grand(df)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for stock owners."""
    args = context.args
    if not args:
        await update.message.reply_text("사용법: /search AAPL")
        return

    symbol = args[0].upper()
    await update.message.reply_text(f"🔄 {symbol} 보유자 검색 중...")

    try:
        df = scraper.get_stock_owners(symbol)
        if df.empty:
            await update.message.reply_text(f"{symbol}을 보유한 투자자가 없습니다.")
            return

        lines = [f"🔎 *{symbol} 보유 투자자*\n"]
        for idx, row in df.head(10).iterrows():
            lines.append(
                f"• *{row['investor_name'][:20]}*\n"
                f"  비중: {row['percent_portfolio']:.1f}%\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


# Korean stocks commands
async def kr_foreign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get foreign investor net buying."""
    await update.message.reply_text("🔄 외국인 순매수 조회 중...")

    try:
        df = kr_scraper.get_foreign_buying(15)
        if df.empty:
            await update.message.reply_text("데이터를 가져올 수 없습니다.")
            return

        df['순매수_억'] = (df['net_amount'] / 100000000).round(0).astype(int)

        lines = ["🌍 *외국인 순매수 TOP 15*\n"]
        for _, row in df.iterrows():
            lines.append(f"{row['rank']}. *{row['name']}* `{row['symbol']}`\n   💰 {row['순매수_억']:,}억\n")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def kr_inst_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get institutional investor net buying."""
    await update.message.reply_text("🔄 기관 순매수 조회 중...")

    try:
        df = kr_scraper.get_institution_buying(15)
        if df.empty:
            await update.message.reply_text("데이터를 가져올 수 없습니다.")
            return

        df['순매수_억'] = (df['net_amount'] / 100000000).round(0).astype(int)

        lines = ["🏛️ *기관 순매수 TOP 15*\n"]
        for _, row in df.iterrows():
            lines.append(f"{row['rank']}. *{row['name']}* `{row['symbol']}`\n   💰 {row['순매수_억']:,}억\n")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def kr_marketcap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get market cap top stocks."""
    args = context.args
    market = args[0].upper() if args else "KOSPI"
    if market not in ["KOSPI", "KOSDAQ"]:
        market = "KOSPI"

    await update.message.reply_text(f"🔄 {market} 시총 상위 조회 중...")

    try:
        df = kr_scraper.get_market_cap_top(market, 15)
        if df.empty:
            await update.message.reply_text("데이터를 가져올 수 없습니다.")
            return

        df['시총_조'] = (df['market_cap'] / 1000000000000).round(1)

        lines = [f"📊 *{market} 시총 TOP 15*\n"]
        for _, row in df.iterrows():
            lines.append(f"{row['rank']}. *{row['name']}* `{row['symbol']}`\n   💎 {row['시총_조']}조 | {row['close']:,}원\n")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def kr_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search Korean stocks."""
    args = context.args
    if not args:
        await update.message.reply_text("사용법: /kr 삼성전자")
        return

    query = " ".join(args)
    await update.message.reply_text(f"🔄 '{query}' 검색 중...")

    try:
        df = kr_scraper.search_stock(query)
        if df.empty:
            await update.message.reply_text("검색 결과가 없습니다.")
            return

        lines = [f"🔎 *'{query}' 검색 결과*\n"]
        for _, row in df.head(10).iterrows():
            lines.append(f"• `{row['symbol']}` {row['name']} ({row['market']})")

        # Get price for first result
        if len(df) > 0:
            first_symbol = df.iloc[0]['symbol']
            price_info = kr_scraper.get_stock_price(first_symbol)
            if price_info:
                lines.append(f"\n*{price_info['name']}* 현재가: {price_info['close']:,}원")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def kr_short_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get short selling top stocks."""
    args = context.args
    market = args[0].upper() if args else "KOSPI"
    if market not in ["KOSPI", "KOSDAQ"]:
        market = "KOSPI"

    await update.message.reply_text(f"🔄 {market} 공매도 상위 조회 중...")

    try:
        df = kr_scraper.get_short_volume(market, 15)
        if df.empty:
            await update.message.reply_text("데이터를 가져올 수 없습니다.")
            return

        df['short_억'] = (df['short_amount'] / 100000000).round(0).astype(int)

        lines = [f"📉 *{market} 공매도 비중 TOP 15*\n"]
        for _, row in df.iterrows():
            lines.append(
                f"{int(row['rank'])}. *{row['name']}* `{row['symbol']}`\n"
                f"   📊 비중: {row['short_ratio']:.1f}% | {int(row['short_억']):,}억\n"
            )

        lines.append("\n💡 _비중이 높을수록 숏 포지션 많음_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def kr_recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get stock recommendations."""
    await update.message.reply_text("🔄 종목 추천 분석 중... (10-20초 소요)")

    try:
        recs = kr_recommender.get_recommendations(top_n=10)
        dual = kr_recommender.get_dual_buying_stocks()

        if recs.empty:
            await update.message.reply_text("추천 데이터를 가져올 수 없습니다.")
            return

        lines = ["🎯 *종합 추천 TOP 10*\n"]
        lines.append("_외국인+기관 수급 종합 분석_\n")

        for _, row in recs.iterrows():
            signals = row['signals']
            # Clean up emojis for telegram
            signals = signals.replace('🌍', '외').replace('🏛️', '기').replace('⭐', '★').replace('📈', '+').replace('⚠️', '!')

            lines.append(
                f"{int(row['rank'])}. *{row['name']}* `{row['symbol']}`\n"
                f"   점수: {int(row['score'])} | {signals}\n"
            )

        # Add dual buying highlight
        if not dual.empty and len(dual) > 0:
            lines.append("\n⭐ *동반 매수 TOP 3*")
            for _, row in dual.head(3).iterrows():
                lines.append(f"  • {row['name']}: 외국인 {row['foreign_억']:,}억 + 기관 {row['inst_억']:,}억")

        lines.append("\n_⚠️ 참고용이며 투자권유 아님_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


# Pension commands
async def pension_etf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get pension ETF recommendations."""
    await update.message.reply_text("🔄 연금저축 ETF 분석 중... (최대 1분 소요)")

    try:
        quick_picks = pension_recommender.get_quick_picks(10)

        if quick_picks.empty:
            await update.message.reply_text("ETF 데이터를 가져올 수 없습니다.")
            return

        lines = ["💰 *연금저축 ETF 추천 TOP 10*\n"]
        lines.append("_수익률 + 연금적합성 기준_\n")

        for _, row in quick_picks.iterrows():
            lines.append(
                f"{int(row['rank'])}. *{row['name'][:20]}*\n"
                f"   1M: {row['return_1m']:+.1f}% | {row['asset_class']}\n"
            )

        lines.append("\n_⚠️ 투자 결정은 신중하게_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def market_sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get market sentiment analysis."""
    await update.message.reply_text("🔄 시장 심리 분석 중...")

    try:
        sentiment = pension_recommender.analyze_market_sentiment()
        allocation = pension_recommender.get_sentiment_based_allocation()

        sentiment_emoji = {"bullish": "🟢 강세", "neutral": "🟡 중립", "bearish": "🔴 약세"}

        lines = ["📊 *시장 심리 분석*\n"]
        lines.append(f"전체 심리: {sentiment_emoji.get(sentiment.overall, '중립')}")
        lines.append(f"심리 점수: {sentiment.score:+d}")
        lines.append(f"추천 성향: {allocation['risk_level'].upper()}\n")
        lines.append(f"💡 {allocation['advice']}")

        if sentiment.themes:
            lines.append("\n🔥 *유망 테마:*")
            for theme in sentiment.themes[:5]:
                lines.append(f"  • {theme}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


async def asset_allocation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get asset allocation recommendation."""
    await update.message.reply_text("🔄 자산배분 분석 중...")

    try:
        allocation_result = pension_recommender.get_sentiment_based_allocation()

        lines = ["🎯 *자산배분 추천*\n"]
        lines.append(f"추천 성향: {allocation_result['risk_level'].upper()}")
        lines.append(f"💡 {allocation_result['advice']}\n")

        lines.append("*추천 비중:*")
        for asset_class, weight in allocation_result['allocation'].items():
            if weight > 0:
                bar = "█" * (weight // 5) + "░" * (20 - weight // 5)
                lines.append(f"{asset_class}: {bar} {weight}%")

        lines.append("\n_⚠️ 시장 상황에 따라 조정 필요_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ 오류: {str(e)}")


def run_bot(token: str):
    """Run the Telegram bot."""
    db.init_db()

    app = Application.builder().token(token).build()

    # Add handlers - US stocks
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("portfolio", portfolio_command))
    app.add_handler(CommandHandler("p", portfolio_command))  # shortcut
    app.add_handler(CommandHandler("investors", investors_command))
    app.add_handler(CommandHandler("overlap", overlap_command))
    app.add_handler(CommandHandler("grand", grand_command))
    app.add_handler(CommandHandler("search", search_command))

    # Add handlers - Korean stocks
    app.add_handler(CommandHandler("외국인", kr_foreign_command))
    app.add_handler(CommandHandler("foreign", kr_foreign_command))
    app.add_handler(CommandHandler("기관", kr_inst_command))
    app.add_handler(CommandHandler("inst", kr_inst_command))
    app.add_handler(CommandHandler("시총", kr_marketcap_command))
    app.add_handler(CommandHandler("cap", kr_marketcap_command))
    app.add_handler(CommandHandler("공매도", kr_short_command))
    app.add_handler(CommandHandler("short", kr_short_command))
    app.add_handler(CommandHandler("추천", kr_recommend_command))
    app.add_handler(CommandHandler("pick", kr_recommend_command))
    app.add_handler(CommandHandler("kr", kr_search_command))

    # Add handlers - Pension
    app.add_handler(CommandHandler("연금", pension_etf_command))
    app.add_handler(CommandHandler("pension", pension_etf_command))
    app.add_handler(CommandHandler("시장분석", market_sentiment_command))
    app.add_handler(CommandHandler("sentiment", market_sentiment_command))
    app.add_handler(CommandHandler("자산배분", asset_allocation_command))
    app.add_handler(CommandHandler("allocation", asset_allocation_command))

    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import sys

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        if len(sys.argv) > 1:
            token = sys.argv[1]
        else:
            print("Usage: python -m src.bot.telegram_bot <BOT_TOKEN>")
            print("Or set TELEGRAM_BOT_TOKEN environment variable")
            sys.exit(1)

    run_bot(token)
