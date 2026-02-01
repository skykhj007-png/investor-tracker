"""Analyze portfolio changes over time."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from ..storage.database import Database
from ..scrapers.dataroma import DataromaScraper


@dataclass
class PositionChange:
    """Represents a change in a position."""
    symbol: str
    stock: str
    change_type: str  # "NEW", "EXIT", "INCREASE", "DECREASE"
    prev_shares: int
    curr_shares: int
    shares_change: int
    shares_change_pct: float
    prev_percent: float
    curr_percent: float
    percent_change: float


class ChangesAnalyzer:
    """Analyze changes in investor portfolios."""

    def __init__(
        self,
        db: Optional[Database] = None,
        scraper: Optional[DataromaScraper] = None
    ):
        self.db = db or Database()
        self.scraper = scraper or DataromaScraper()

    def compare_quarters(
        self,
        investor_id: str,
        q1: str,
        q2: str
    ) -> pd.DataFrame:
        """
        Compare portfolio between two quarters.

        Args:
            investor_id: Investor ID
            q1: Earlier quarter (e.g., "2024Q2")
            q2: Later quarter (e.g., "2024Q3")

        Returns:
            DataFrame with all position changes
        """
        prev_pf = self.db.get_portfolio(investor_id, q1)
        curr_pf = self.db.get_portfolio(investor_id, q2)

        return self._compare_portfolios(prev_pf, curr_pf)

    def compare_with_current(self, investor_id: str, quarter: str) -> pd.DataFrame:
        """
        Compare a historical quarter with current live portfolio.

        Args:
            investor_id: Investor ID
            quarter: Historical quarter to compare against

        Returns:
            DataFrame with all position changes
        """
        prev_pf = self.db.get_portfolio(investor_id, quarter)
        curr_pf = self.scraper.get_portfolio(investor_id)

        return self._compare_portfolios(prev_pf, curr_pf)

    def _compare_portfolios(
        self,
        prev_pf: pd.DataFrame,
        curr_pf: pd.DataFrame
    ) -> pd.DataFrame:
        """Compare two portfolio DataFrames and return changes."""
        if prev_pf.empty and curr_pf.empty:
            return pd.DataFrame()

        # Create symbol -> row mappings
        prev_map = {row["symbol"]: row for _, row in prev_pf.iterrows()} if not prev_pf.empty else {}
        curr_map = {row["symbol"]: row for _, row in curr_pf.iterrows()} if not curr_pf.empty else {}

        all_symbols = set(prev_map.keys()) | set(curr_map.keys())
        changes = []

        for symbol in all_symbols:
            prev_row = prev_map.get(symbol)
            curr_row = curr_map.get(symbol)

            change = self._calculate_change(symbol, prev_row, curr_row)
            if change:
                changes.append(change)

        if not changes:
            return pd.DataFrame()

        df = pd.DataFrame([vars(c) for c in changes])
        # Sort: NEW first, then EXIT, then by absolute percent change
        type_order = {"NEW": 0, "EXIT": 1, "INCREASE": 2, "DECREASE": 3}
        df["_sort"] = df["change_type"].map(type_order)
        df = df.sort_values(
            ["_sort", "percent_change"],
            ascending=[True, False]
        ).drop("_sort", axis=1)

        return df.reset_index(drop=True)

    def _calculate_change(
        self,
        symbol: str,
        prev_row: Optional[pd.Series],
        curr_row: Optional[pd.Series]
    ) -> Optional[PositionChange]:
        """Calculate change for a single position."""
        prev_shares = int(prev_row["shares"]) if prev_row is not None else 0
        curr_shares = int(curr_row["shares"]) if curr_row is not None else 0
        prev_percent = float(prev_row["percent_portfolio"]) if prev_row is not None else 0.0
        curr_percent = float(curr_row["percent_portfolio"]) if curr_row is not None else 0.0

        shares_change = curr_shares - prev_shares
        percent_change = curr_percent - prev_percent

        # Determine change type
        if prev_row is None and curr_row is not None:
            change_type = "NEW"
        elif prev_row is not None and curr_row is None:
            change_type = "EXIT"
        elif shares_change > 0:
            change_type = "INCREASE"
        elif shares_change < 0:
            change_type = "DECREASE"
        else:
            return None  # No change

        # Calculate percentage change in shares
        if prev_shares > 0:
            shares_change_pct = (shares_change / prev_shares) * 100
        elif curr_shares > 0:
            shares_change_pct = 100.0  # New position
        else:
            shares_change_pct = 0.0

        stock_name = ""
        if curr_row is not None:
            stock_name = curr_row.get("stock", "")
        elif prev_row is not None:
            stock_name = prev_row.get("stock", "")

        return PositionChange(
            symbol=symbol,
            stock=stock_name,
            change_type=change_type,
            prev_shares=prev_shares,
            curr_shares=curr_shares,
            shares_change=shares_change,
            shares_change_pct=round(shares_change_pct, 2),
            prev_percent=round(prev_percent, 2),
            curr_percent=round(curr_percent, 2),
            percent_change=round(percent_change, 2),
        )

    def detect_new_positions(
        self,
        investor_id: str,
        q1: str,
        q2: str
    ) -> pd.DataFrame:
        """
        Detect newly initiated positions between two quarters.

        Args:
            investor_id: Investor ID
            q1: Earlier quarter
            q2: Later quarter

        Returns:
            DataFrame with new positions only
        """
        changes = self.compare_quarters(investor_id, q1, q2)
        if changes.empty:
            return changes
        return changes[changes["change_type"] == "NEW"].reset_index(drop=True)

    def detect_exits(
        self,
        investor_id: str,
        q1: str,
        q2: str
    ) -> pd.DataFrame:
        """
        Detect completely exited positions between two quarters.

        Args:
            investor_id: Investor ID
            q1: Earlier quarter
            q2: Later quarter

        Returns:
            DataFrame with exited positions only
        """
        changes = self.compare_quarters(investor_id, q1, q2)
        if changes.empty:
            return changes
        return changes[changes["change_type"] == "EXIT"].reset_index(drop=True)

    def calculate_position_changes(
        self,
        investor_id: str,
        q1: str,
        q2: str,
        min_change_pct: float = 5.0
    ) -> pd.DataFrame:
        """
        Get significant position weight changes.

        Args:
            investor_id: Investor ID
            q1: Earlier quarter
            q2: Later quarter
            min_change_pct: Minimum absolute percent change to include

        Returns:
            DataFrame with significant weight changes
        """
        changes = self.compare_quarters(investor_id, q1, q2)
        if changes.empty:
            return changes

        # Filter by minimum change
        significant = changes[
            abs(changes["percent_change"]) >= min_change_pct
        ]
        return significant.reset_index(drop=True)

    def get_activity_summary(
        self,
        investor_id: str,
        q1: str,
        q2: str
    ) -> dict:
        """
        Get summary of portfolio activity.

        Returns:
            Dictionary with activity counts and key changes
        """
        changes = self.compare_quarters(investor_id, q1, q2)

        if changes.empty:
            return {
                "new_positions": 0,
                "exits": 0,
                "increases": 0,
                "decreases": 0,
                "total_changes": 0,
            }

        return {
            "new_positions": len(changes[changes["change_type"] == "NEW"]),
            "exits": len(changes[changes["change_type"] == "EXIT"]),
            "increases": len(changes[changes["change_type"] == "INCREASE"]),
            "decreases": len(changes[changes["change_type"] == "DECREASE"]),
            "total_changes": len(changes),
            "top_new": changes[changes["change_type"] == "NEW"]["symbol"].tolist()[:5],
            "top_exits": changes[changes["change_type"] == "EXIT"]["symbol"].tolist()[:5],
        }

    def sync_portfolio(self, investor_id: str, quarter: Optional[str] = None):
        """
        Fetch current portfolio from Dataroma and save to database.

        Args:
            investor_id: Investor ID
            quarter: Quarter string (auto-generated if None)
        """
        portfolio = self.scraper.get_portfolio(investor_id)
        if not portfolio.empty:
            self.db.save_portfolio(investor_id, portfolio, quarter)


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # Initialize
    db = Database()
    db.init_db()
    analyzer = ChangesAnalyzer(db=db)

    # Example: Sync a portfolio
    console.print("[bold]Syncing BRK portfolio...[/bold]")
    analyzer.sync_portfolio("BRK", "2024Q4")

    # Show available quarters
    quarters = db.get_available_quarters("BRK")
    console.print(f"Available quarters: {quarters}")

    if len(quarters) >= 2:
        q1, q2 = quarters[1], quarters[0]
        console.print(f"\n[bold cyan]=== Changes: {q1} -> {q2} ===[/bold cyan]")

        # All changes
        changes = analyzer.compare_quarters("BRK", q1, q2)
        console.print(changes)

        # Summary
        summary = analyzer.get_activity_summary("BRK", q1, q2)
        console.print(f"\n[bold]Summary:[/bold] {summary}")
