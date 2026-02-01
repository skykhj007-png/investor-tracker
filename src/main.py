"""Main entry point for investor-tracker."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .scrapers.dataroma import DataromaScraper
from .analyzers.overlap import OverlapAnalyzer
from .analyzers.changes import ChangesAnalyzer
from .notifications.alerts import AlertManager, AlertScheduler
from .storage.database import Database

console = Console()


def create_table(title: str, columns: list[tuple[str, str]]) -> Table:
    """Create a styled Rich table."""
    table = Table(
        title=title,
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        title_style="bold white",
    )
    for name, style in columns:
        table.add_column(name, style=style)
    return table


@click.group()
@click.version_option(version="1.0.0", prog_name="investor-tracker")
def cli():
    """
    Investor Tracker - Track super investor portfolios.

    Monitor portfolio holdings, analyze overlaps, and detect changes
    from SEC 13F filings via Dataroma.
    """
    pass


@cli.command()
@click.option(
    "--investor", "-i",
    required=True,
    help="Investor ID (e.g., BRK, psc, baupost)"
)
@click.option(
    "--top", "-n",
    default=10,
    type=int,
    help="Number of top holdings to show"
)
@click.option(
    "--save/--no-save",
    default=False,
    help="Save portfolio to database"
)
def portfolio(investor: str, top: int, save: bool):
    """Show portfolio holdings for an investor."""
    scraper = DataromaScraper()

    with console.status(f"[bold green]Fetching portfolio for {investor}..."):
        df = scraper.get_portfolio(investor)

    if df.empty:
        console.print(f"[red]No portfolio found for investor: {investor}[/red]")
        return

    # Create table
    table = create_table(
        f"Portfolio: {investor.upper()}",
        [
            ("Rank", "dim"),
            ("Symbol", "bold cyan"),
            ("Stock", "white"),
            ("Weight %", "green"),
            ("Shares", "yellow"),
            ("Value", "magenta"),
            ("Activity", "blue"),
        ]
    )

    for idx, row in df.head(top).iterrows():
        table.add_row(
            str(idx + 1),
            row["symbol"],
            row["stock"][:30],
            f"{row['percent_portfolio']:.2f}%",
            f"{row['shares']:,}",
            f"${row['value']:,.0f}",
            row.get("activity", ""),
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]Showing top {min(top, len(df))} of {len(df)} holdings[/dim]")

    # Save to database if requested
    if save:
        db = Database()
        db.init_db()
        db.save_portfolio(investor, df)
        console.print(f"[green]Portfolio saved to database.[/green]")


@cli.command()
@click.option(
    "--investors", "-i",
    required=True,
    help="Comma-separated investor IDs (e.g., BRK,psc,baupost)"
)
@click.option(
    "--min-count", "-m",
    default=2,
    type=int,
    help="Minimum number of investors holding a stock"
)
@click.option(
    "--top", "-n",
    default=20,
    type=int,
    help="Number of results to show"
)
@click.option(
    "--conviction/--no-conviction",
    default=False,
    help="Sort by conviction score instead of ownership count"
)
def overlap(investors: str, min_count: int, top: int, conviction: bool):
    """Analyze portfolio overlaps between investors."""
    investor_list = [i.strip() for i in investors.split(",")]

    if len(investor_list) < 2:
        console.print("[red]Please provide at least 2 investors.[/red]")
        return

    analyzer = OverlapAnalyzer()

    with console.status(f"[bold green]Analyzing overlaps for {len(investor_list)} investors..."):
        if conviction:
            df = analyzer.calculate_conviction_score(investor_list)
            title = "Conviction Score Analysis"
            sort_col = "conviction_score"
        else:
            df = analyzer.rank_by_ownership_count(investor_list)
            title = "Portfolio Overlap Analysis"
            sort_col = "num_owners"

    if df.empty:
        console.print("[red]No overlapping holdings found.[/red]")
        return

    # Filter by minimum count
    df = df[df["num_owners"] >= min_count]

    if df.empty:
        console.print(f"[yellow]No stocks held by {min_count}+ investors.[/yellow]")
        return

    # Create table
    if conviction:
        table = create_table(
            title,
            [
                ("Rank", "dim"),
                ("Symbol", "bold cyan"),
                ("Stock", "white"),
                ("Score", "bold green"),
                ("Owners", "yellow"),
                ("Avg Weight", "magenta"),
            ]
        )
        for idx, row in df.head(top).iterrows():
            table.add_row(
                str(idx + 1),
                row["symbol"],
                str(row["stock"])[:25],
                f"{row['conviction_score']:.1f}",
                str(row["num_owners"]),
                f"{row['avg_percent']:.2f}%",
            )
    else:
        table = create_table(
            title,
            [
                ("Rank", "dim"),
                ("Symbol", "bold cyan"),
                ("Stock", "white"),
                ("Owners", "bold yellow"),
                ("Avg Weight", "green"),
                ("Held By", "dim"),
            ]
        )
        for idx, row in df.head(top).iterrows():
            table.add_row(
                str(idx + 1),
                row["symbol"],
                str(row["stock"])[:25],
                str(row["num_owners"]),
                f"{row['avg_percent']:.2f}%",
                str(row.get("owners", ""))[:30],
            )

    console.print()
    console.print(f"[bold]Investors:[/bold] {', '.join(investor_list)}")
    console.print(table)
    console.print(f"\n[dim]Showing {min(top, len(df))} stocks held by {min_count}+ investors[/dim]")


@cli.command()
@click.option(
    "--investor", "-i",
    required=True,
    help="Investor ID"
)
@click.option(
    "--period", "-p",
    required=True,
    help="Period to compare (e.g., 2024Q3-2024Q4 or Q3-Q4)"
)
@click.option(
    "--type", "-t",
    "change_type",
    type=click.Choice(["all", "new", "exit", "increase", "decrease"]),
    default="all",
    help="Filter by change type"
)
@click.option(
    "--sync/--no-sync",
    default=False,
    help="Sync current portfolio before comparing"
)
def changes(investor: str, period: str, change_type: str, sync: bool):
    """Analyze portfolio changes between quarters."""
    # Parse period
    parts = period.upper().replace(" ", "").split("-")
    if len(parts) != 2:
        console.print("[red]Invalid period format. Use: Q3-Q4 or 2024Q3-2024Q4[/red]")
        return

    q1, q2 = parts
    # Add year if not present
    if not q1[0].isdigit():
        from datetime import datetime
        year = datetime.now().year
        q1 = f"{year}{q1}"
        q2 = f"{year}{q2}"

    db = Database()
    db.init_db()
    analyzer = ChangesAnalyzer(db=db)

    # Sync if requested
    if sync:
        with console.status(f"[bold green]Syncing portfolio for {investor}..."):
            analyzer.sync_portfolio(investor, q2)
        console.print(f"[green]Synced {investor} portfolio as {q2}[/green]")

    # Check available quarters
    available = db.get_available_quarters(investor)
    if q1 not in available or q2 not in available:
        console.print(f"[yellow]Available quarters for {investor}: {available or 'None'}[/yellow]")
        console.print("[dim]Use --sync to save current portfolio first.[/dim]")
        return

    with console.status(f"[bold green]Comparing {q1} vs {q2}..."):
        df = analyzer.compare_quarters(investor, q1, q2)

    if df.empty:
        console.print(f"[yellow]No changes detected between {q1} and {q2}.[/yellow]")
        return

    # Filter by type
    type_map = {
        "new": "NEW",
        "exit": "EXIT",
        "increase": "INCREASE",
        "decrease": "DECREASE",
    }
    if change_type != "all":
        df = df[df["change_type"] == type_map[change_type]]

    if df.empty:
        console.print(f"[yellow]No {change_type} changes found.[/yellow]")
        return

    # Create table
    table = create_table(
        f"Changes: {investor.upper()} ({q1} → {q2})",
        [
            ("Type", "bold"),
            ("Symbol", "cyan"),
            ("Stock", "white"),
            ("Shares", "yellow"),
            ("Change", ""),
            ("Weight", "magenta"),
            ("Δ Weight", ""),
        ]
    )

    type_styles = {
        "NEW": "bold green",
        "EXIT": "bold red",
        "INCREASE": "green",
        "DECREASE": "red",
    }

    for _, row in df.iterrows():
        change_style = type_styles.get(row["change_type"], "white")

        # Format shares change
        if row["change_type"] == "NEW":
            shares_str = f"+{row['curr_shares']:,}"
        elif row["change_type"] == "EXIT":
            shares_str = f"-{row['prev_shares']:,}"
        else:
            shares_str = f"{row['curr_shares']:,}"

        # Format change
        if row["shares_change"] > 0:
            change_str = f"+{row['shares_change']:,} ({row['shares_change_pct']:+.1f}%)"
        else:
            change_str = f"{row['shares_change']:,} ({row['shares_change_pct']:+.1f}%)"

        table.add_row(
            Text(row["change_type"], style=change_style),
            row["symbol"],
            str(row["stock"])[:20],
            shares_str,
            change_str,
            f"{row['curr_percent']:.2f}%",
            Text(f"{row['percent_change']:+.2f}%", style=change_style),
        )

    # Summary panel
    summary = analyzer.get_activity_summary(investor, q1, q2)
    summary_text = (
        f"[green]New: {summary['new_positions']}[/green] | "
        f"[red]Exit: {summary['exits']}[/red] | "
        f"[blue]Increased: {summary['increases']}[/blue] | "
        f"[yellow]Decreased: {summary['decreases']}[/yellow]"
    )

    console.print()
    console.print(Panel(summary_text, title="Summary", border_style="blue"))
    console.print(table)


@cli.command()
@click.option(
    "--investors", "-i",
    default="BRK,psc,baupost",
    help="Comma-separated investor IDs to watch"
)
@click.option(
    "--interval", "-n",
    default=3600,
    type=int,
    help="Check interval in seconds"
)
@click.option(
    "--filings/--no-filings",
    default=True,
    help="Check for new SEC 13F filings"
)
def watch(investors: str, interval: int, filings: bool):
    """Watch investors for portfolio changes and new filings."""
    investor_list = [i.strip() for i in investors.split(",")]

    db = Database()
    db.init_db()
    manager = AlertManager(db=db)
    scheduler = AlertScheduler(manager)

    console.print(Panel(
        f"[bold]Watching {len(investor_list)} investors[/bold]\n\n"
        f"Investors: {', '.join(investor_list)}\n"
        f"Interval: {interval} seconds ({interval/3600:.1f} hours)\n"
        f"13F Filing Check: {'Enabled' if filings else 'Disabled'}",
        title="Investor Watch",
        border_style="green",
    ))

    interval_hours = interval / 3600

    if filings:
        scheduler.schedule_filing_check(investor_list, interval_hours=max(1, int(interval_hours)))

    scheduler.schedule_portfolio_watch(investor_list, interval_hours=max(1, int(interval_hours)))
    scheduler.run()


@cli.command()
def investors():
    """List all available investors on Dataroma."""
    scraper = DataromaScraper()

    with console.status("[bold green]Fetching investor list..."):
        df = scraper.get_investor_list()

    if df.empty:
        console.print("[red]Failed to fetch investor list.[/red]")
        return

    table = create_table(
        "Available Investors",
        [
            ("#", "dim"),
            ("ID", "bold cyan"),
            ("Name", "white"),
            ("Last Filing", "yellow"),
            ("Market Value", "green"),
        ]
    )

    for idx, row in df.iterrows():
        table.add_row(
            str(idx + 1),
            row["investor_id"],
            row["name"],
            row["portfolio_date"],
            row["market_value"],
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]Total: {len(df)} investors[/dim]")


@cli.command()
@click.option("--investor", "-i", required=True, help="Investor ID")
@click.option("--quarter", "-q", default=None, help="Quarter (e.g., 2024Q4)")
def sync(investor: str, quarter: str):
    """Sync portfolio from Dataroma to local database."""
    db = Database()
    db.init_db()
    analyzer = ChangesAnalyzer(db=db)

    with console.status(f"[bold green]Syncing {investor}..."):
        analyzer.sync_portfolio(investor, quarter)

    quarters = db.get_available_quarters(investor)
    console.print(f"[green]Synced {investor} portfolio.[/green]")
    console.print(f"[dim]Available quarters: {quarters}[/dim]")


@cli.command()
def grand():
    """Show grand portfolio (stocks held by most super investors)."""
    scraper = DataromaScraper()

    with console.status("[bold green]Fetching grand portfolio..."):
        df = scraper.get_grand_portfolio()

    if df.empty:
        console.print("[red]Failed to fetch grand portfolio.[/red]")
        return

    table = create_table(
        "Grand Portfolio - Most Widely Held Stocks",
        [
            ("Rank", "dim"),
            ("Symbol", "bold cyan"),
            ("Stock", "white"),
            ("# Owners", "bold yellow"),
            ("Total Value", "green"),
            ("% of Total", "magenta"),
        ]
    )

    for idx, row in df.head(30).iterrows():
        table.add_row(
            str(idx + 1),
            row["symbol"],
            str(row["stock"])[:30],
            str(row["num_owners"]),
            f"${row['total_value']:,.0f}" if row['total_value'] else "-",
            f"{row['percent_total']:.2f}%" if row['percent_total'] else "-",
        )

    console.print()
    console.print(table)


@cli.command()
def menu():
    """Interactive menu mode."""
    from rich.prompt import Prompt, IntPrompt

    while True:
        console.print()
        console.print(Panel(
            "[1] 투자자 목록 보기\n"
            "[2] 포트폴리오 조회\n"
            "[3] 공통 종목 분석\n"
            "[4] 분기 변화 확인\n"
            "[5] Grand Portfolio\n"
            "[6] 포트폴리오 동기화\n"
            "[7] 실시간 모니터링\n"
            "[0] 종료",
            title="[bold cyan]Investor Tracker[/bold cyan]",
            border_style="cyan",
        ))

        choice = Prompt.ask("선택", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="0")

        if choice == "0":
            console.print("[yellow]종료합니다.[/yellow]")
            break

        elif choice == "1":
            ctx = click.Context(investors)
            ctx.invoke(investors)

        elif choice == "2":
            inv = Prompt.ask("투자자 ID", default="BRK")
            top = IntPrompt.ask("상위 몇 개", default=10)
            ctx = click.Context(portfolio)
            ctx.invoke(portfolio, investor=inv, top=top, save=False)

        elif choice == "3":
            inv_list = Prompt.ask("투자자 ID (쉼표 구분)", default="BRK,psc,GLRE")
            min_cnt = IntPrompt.ask("최소 보유 투자자 수", default=2)
            ctx = click.Context(overlap)
            ctx.invoke(overlap, investors=inv_list, min_count=min_cnt, top=20, conviction=False)

        elif choice == "4":
            inv = Prompt.ask("투자자 ID", default="BRK")
            period = Prompt.ask("기간 (예: 2024Q3-2024Q4)", default="2024Q3-2024Q4")
            ctx = click.Context(changes)
            ctx.invoke(changes, investor=inv, period=period, change_type="all", sync=False)

        elif choice == "5":
            ctx = click.Context(grand)
            ctx.invoke(grand)

        elif choice == "6":
            inv = Prompt.ask("투자자 ID", default="BRK")
            qtr = Prompt.ask("분기 (예: 2024Q4)", default=None) or None
            ctx = click.Context(sync)
            ctx.invoke(sync, investor=inv, quarter=qtr)

        elif choice == "7":
            inv_list = Prompt.ask("투자자 ID (쉼표 구분)", default="BRK,psc,GLRE")
            interval = IntPrompt.ask("체크 주기 (초)", default=3600)
            ctx = click.Context(watch)
            ctx.invoke(watch, investors=inv_list, interval=interval, filings=True)


if __name__ == "__main__":
    cli()
