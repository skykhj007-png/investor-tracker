"""Alert system for portfolio changes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
import time

import requests
import schedule
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..scrapers.dataroma import DataromaScraper
from ..analyzers.changes import ChangesAnalyzer
from ..storage.database import Database


@dataclass
class Alert:
    """Represents an alert notification."""
    alert_type: str  # "NEW_FILING", "NEW_POSITION", "EXIT", "SIGNIFICANT_CHANGE"
    investor_id: str
    investor_name: str
    message: str
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: str = "normal"  # "low", "normal", "high"


class SECEdgarClient:
    """Client for SEC EDGAR API to check 13F filings."""

    BASE_URL = "https://efts.sec.gov/LATEST/search-index"
    SEARCH_URL = "https://efts.sec.gov/LATEST"

    HEADERS = {
        "User-Agent": "InvestorTracker/1.0 (educational purposes)",
        "Accept": "application/json",
    }

    # Known CIK mappings for major investors
    INVESTOR_CIKS = {
        "BRK": "0001067983",      # Berkshire Hathaway
        "psc": "0001029160",       # Pershing Square
        "baupost": "0001061768",   # Baupost Group
        "third-point": "0001040273",  # Third Point
        "greenlight": "0001079114",   # Greenlight Capital
        "appaloosa": "0001656456",    # Appaloosa Management
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_recent_13f_filings(self, cik: str, limit: int = 5) -> list[dict]:
        """
        Get recent 13F-HR filings for a company.

        Args:
            cik: SEC CIK number
            limit: Number of recent filings to return

        Returns:
            List of filing info dicts
        """
        # SEC EDGAR company submissions API
        cik_padded = cik.lstrip("0").zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            filings = []
            recent = data.get("filings", {}).get("recent", {})

            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])

            for i, form in enumerate(forms):
                if "13F" in form and len(filings) < limit:
                    filings.append({
                        "form": form,
                        "filing_date": dates[i] if i < len(dates) else "",
                        "accession": accessions[i] if i < len(accessions) else "",
                        "cik": cik,
                    })

            return filings
        except Exception:
            return []

    def check_new_filing(self, cik: str, since_date: str) -> Optional[dict]:
        """
        Check if there's a new 13F filing since a given date.

        Args:
            cik: SEC CIK number
            since_date: Date string (YYYY-MM-DD)

        Returns:
            Filing info if new filing exists, None otherwise
        """
        filings = self.get_recent_13f_filings(cik, limit=1)
        if filings:
            latest = filings[0]
            if latest["filing_date"] > since_date:
                return latest
        return None


class AlertManager:
    """Manage and send alerts for portfolio events."""

    def __init__(
        self,
        db: Optional[Database] = None,
        scraper: Optional[DataromaScraper] = None,
    ):
        self.db = db or Database()
        self.scraper = scraper or DataromaScraper()
        self.edgar = SECEdgarClient()
        self.console = Console()
        self.alerts: list[Alert] = []
        self.last_check: dict[str, str] = {}  # investor_id -> last filing date
        self.callbacks: list[Callable[[Alert], None]] = []

    def add_callback(self, callback: Callable[[Alert], None]):
        """Add a callback to be called when an alert is triggered."""
        self.callbacks.append(callback)

    def check_new_filings(self, investor_ids: list[str]) -> list[Alert]:
        """
        Check SEC EDGAR for new 13F filings.

        Args:
            investor_ids: List of investor IDs to check

        Returns:
            List of alerts for new filings
        """
        alerts = []

        for investor_id in investor_ids:
            cik = SECEdgarClient.INVESTOR_CIKS.get(investor_id)
            if not cik:
                continue

            last_date = self.last_check.get(investor_id, "2000-01-01")
            new_filing = self.edgar.check_new_filing(cik, last_date)

            if new_filing:
                # Get investor name from scraper
                investors = self.scraper.get_investor_list()
                inv_row = investors[investors["investor_id"] == investor_id]
                inv_name = inv_row.iloc[0]["name"] if not inv_row.empty else investor_id

                alert = Alert(
                    alert_type="NEW_FILING",
                    investor_id=investor_id,
                    investor_name=inv_name,
                    message=f"New 13F filing detected: {new_filing['form']}",
                    details={
                        "filing_date": new_filing["filing_date"],
                        "accession": new_filing["accession"],
                        "form": new_filing["form"],
                    },
                    priority="high",
                )
                alerts.append(alert)
                self.last_check[investor_id] = new_filing["filing_date"]

        return alerts

    def watch_investors(
        self,
        investor_ids: list[str],
        check_interval_hours: int = 24
    ) -> list[Alert]:
        """
        Monitor investors for portfolio changes.

        Args:
            investor_ids: List of investor IDs to watch
            check_interval_hours: How often to check (for scheduling)

        Returns:
            List of triggered alerts
        """
        all_alerts = []

        for investor_id in investor_ids:
            # Check for new positions and exits via Dataroma
            alerts = self._check_investor_changes(investor_id)
            all_alerts.extend(alerts)

        # Store alerts
        self.alerts.extend(all_alerts)

        # Send notifications
        for alert in all_alerts:
            self.send_notification(alert)
            for callback in self.callbacks:
                callback(alert)

        return all_alerts

    def _check_investor_changes(self, investor_id: str) -> list[Alert]:
        """Check for changes in a single investor's portfolio."""
        alerts = []

        # Get available quarters from DB
        quarters = self.db.get_available_quarters(investor_id)
        if len(quarters) < 2:
            return alerts

        q_prev, q_curr = quarters[1], quarters[0]

        # Use ChangesAnalyzer
        analyzer = ChangesAnalyzer(db=self.db, scraper=self.scraper)
        changes = analyzer.compare_quarters(investor_id, q_prev, q_curr)

        if changes.empty:
            return alerts

        # Get investor name
        investors = self.scraper.get_investor_list()
        inv_row = investors[investors["investor_id"] == investor_id]
        inv_name = inv_row.iloc[0]["name"] if not inv_row.empty else investor_id

        # New positions
        new_positions = changes[changes["change_type"] == "NEW"]
        if not new_positions.empty:
            symbols = new_positions["symbol"].tolist()
            alert = Alert(
                alert_type="NEW_POSITION",
                investor_id=investor_id,
                investor_name=inv_name,
                message=f"New positions: {', '.join(symbols[:5])}",
                details={"symbols": symbols, "count": len(symbols)},
                priority="high",
            )
            alerts.append(alert)

        # Exits
        exits = changes[changes["change_type"] == "EXIT"]
        if not exits.empty:
            symbols = exits["symbol"].tolist()
            alert = Alert(
                alert_type="EXIT",
                investor_id=investor_id,
                investor_name=inv_name,
                message=f"Exited positions: {', '.join(symbols[:5])}",
                details={"symbols": symbols, "count": len(symbols)},
                priority="normal",
            )
            alerts.append(alert)

        # Significant changes (>25% weight change)
        significant = changes[abs(changes["percent_change"]) >= 25.0]
        if not significant.empty:
            for _, row in significant.iterrows():
                alert = Alert(
                    alert_type="SIGNIFICANT_CHANGE",
                    investor_id=investor_id,
                    investor_name=inv_name,
                    message=f"{row['symbol']}: {row['percent_change']:+.1f}% weight change",
                    details={
                        "symbol": row["symbol"],
                        "prev_percent": row["prev_percent"],
                        "curr_percent": row["curr_percent"],
                        "change": row["percent_change"],
                    },
                    priority="normal",
                )
                alerts.append(alert)

        return alerts

    def send_notification(self, alert: Alert):
        """
        Send alert notification to terminal using Rich.

        Args:
            alert: Alert to display
        """
        # Choose style based on priority and type
        style_map = {
            "NEW_FILING": ("bold white on blue", "blue"),
            "NEW_POSITION": ("bold white on green", "green"),
            "EXIT": ("bold white on red", "red"),
            "SIGNIFICANT_CHANGE": ("bold white on yellow", "yellow"),
        }

        title_style, border_style = style_map.get(
            alert.alert_type,
            ("bold white", "white")
        )

        # Build content
        content = Text()
        content.append(f"{alert.investor_name}\n", style="bold")
        content.append(f"{alert.message}\n", style="")

        if alert.details:
            content.append("\n")
            for key, value in alert.details.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value[:5])
                content.append(f"  {key}: ", style="dim")
                content.append(f"{value}\n", style="")

        content.append(f"\n{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", style="dim")

        # Create panel
        panel = Panel(
            content,
            title=f"[{title_style}] {alert.alert_type.replace('_', ' ')} ",
            border_style=border_style,
            padding=(1, 2),
        )

        self.console.print(panel)

    def show_alerts_table(self, limit: int = 20):
        """Display recent alerts in a table format."""
        table = Table(title="Recent Alerts", show_lines=True)
        table.add_column("Time", style="dim", width=12)
        table.add_column("Type", style="bold")
        table.add_column("Investor")
        table.add_column("Message")
        table.add_column("Priority")

        priority_colors = {"low": "dim", "normal": "white", "high": "bold red"}

        for alert in self.alerts[-limit:]:
            table.add_row(
                alert.timestamp.strftime("%H:%M:%S"),
                alert.alert_type,
                alert.investor_name,
                alert.message[:50],
                Text(alert.priority, style=priority_colors.get(alert.priority, "white")),
            )

        self.console.print(table)


class AlertScheduler:
    """Schedule periodic alert checks."""

    def __init__(self, alert_manager: AlertManager):
        self.manager = alert_manager
        self.console = Console()
        self.running = False

    def schedule_filing_check(
        self,
        investor_ids: list[str],
        interval_hours: int = 24
    ):
        """Schedule periodic 13F filing checks."""
        def job():
            self.console.print(
                f"[dim]Checking for new 13F filings... "
                f"({datetime.now().strftime('%H:%M:%S')})[/dim]"
            )
            alerts = self.manager.check_new_filings(investor_ids)
            if not alerts:
                self.console.print("[dim]No new filings found.[/dim]")

        schedule.every(interval_hours).hours.do(job)
        job()  # Run immediately

    def schedule_portfolio_watch(
        self,
        investor_ids: list[str],
        interval_hours: int = 6
    ):
        """Schedule periodic portfolio monitoring."""
        def job():
            self.console.print(
                f"[dim]Monitoring portfolios... "
                f"({datetime.now().strftime('%H:%M:%S')})[/dim]"
            )
            self.manager.watch_investors(investor_ids)

        schedule.every(interval_hours).hours.do(job)
        job()  # Run immediately

    def run(self):
        """Start the scheduler loop."""
        self.running = True
        self.console.print("[bold green]Alert scheduler started.[/bold green]")
        self.console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.running = False
            self.console.print("\n[bold yellow]Scheduler stopped.[/bold yellow]")

    def stop(self):
        """Stop the scheduler."""
        self.running = False


if __name__ == "__main__":
    console = Console()

    # Initialize
    db = Database()
    db.init_db()

    manager = AlertManager(db=db)

    # Demo: Create sample alerts
    console.print("[bold]=== Alert System Demo ===[/bold]\n")

    demo_alerts = [
        Alert(
            alert_type="NEW_FILING",
            investor_id="BRK",
            investor_name="Berkshire Hathaway",
            message="New 13F-HR filing detected",
            details={"filing_date": "2024-11-14", "form": "13F-HR"},
            priority="high",
        ),
        Alert(
            alert_type="NEW_POSITION",
            investor_id="psc",
            investor_name="Pershing Square",
            message="New positions: GOOGL, MSFT",
            details={"symbols": ["GOOGL", "MSFT"], "count": 2},
            priority="high",
        ),
        Alert(
            alert_type="EXIT",
            investor_id="baupost",
            investor_name="Baupost Group",
            message="Exited positions: META",
            details={"symbols": ["META"], "count": 1},
            priority="normal",
        ),
    ]

    for alert in demo_alerts:
        manager.alerts.append(alert)
        manager.send_notification(alert)
        console.print()

    # Show table
    console.print("\n")
    manager.show_alerts_table()

    # Scheduler example (commented out for demo)
    # scheduler = AlertScheduler(manager)
    # scheduler.schedule_filing_check(["BRK", "psc"], interval_hours=24)
    # scheduler.run()
