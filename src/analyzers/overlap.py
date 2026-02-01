"""Analyze portfolio overlaps between investors."""

import pandas as pd
from typing import Optional

from ..scrapers.dataroma import DataromaScraper


class OverlapAnalyzer:
    """Analyze stock overlaps across investor portfolios."""

    def __init__(self, scraper: Optional[DataromaScraper] = None):
        self.scraper = scraper or DataromaScraper()
        self._portfolio_cache: dict[str, pd.DataFrame] = {}

    def _get_portfolio(self, investor_id: str) -> pd.DataFrame:
        """Get portfolio with caching."""
        if investor_id not in self._portfolio_cache:
            self._portfolio_cache[investor_id] = self.scraper.get_portfolio(investor_id)
        return self._portfolio_cache[investor_id]

    def load_portfolios(self, investor_ids: list[str]) -> dict[str, pd.DataFrame]:
        """Load multiple portfolios."""
        for investor_id in investor_ids:
            self._get_portfolio(investor_id)
        return self._portfolio_cache

    def find_common_holdings(self, investor_ids: list[str]) -> pd.DataFrame:
        """
        Find stocks held by all selected investors.

        Args:
            investor_ids: List of investor IDs to analyze

        Returns:
            DataFrame with common stocks and their details per investor
        """
        if not investor_ids:
            return pd.DataFrame()

        # Load all portfolios
        portfolios = [self._get_portfolio(inv_id) for inv_id in investor_ids]

        # Get symbols from each portfolio
        symbol_sets = [set(pf["symbol"].tolist()) for pf in portfolios if not pf.empty]

        if not symbol_sets:
            return pd.DataFrame()

        # Find intersection
        common_symbols = set.intersection(*symbol_sets)

        if not common_symbols:
            return pd.DataFrame(columns=["symbol", "stock", "investors", "avg_percent", "total_value"])

        # Build result with details
        results = []
        for symbol in common_symbols:
            stock_name = ""
            investor_details = []
            total_percent = 0.0
            total_value = 0.0

            for inv_id, pf in zip(investor_ids, portfolios):
                row = pf[pf["symbol"] == symbol]
                if not row.empty:
                    stock_name = row.iloc[0]["stock"]
                    pct = row.iloc[0]["percent_portfolio"]
                    val = row.iloc[0]["value"]
                    total_percent += pct
                    total_value += val
                    investor_details.append(f"{inv_id}({pct:.1f}%)")

            results.append({
                "symbol": symbol,
                "stock": stock_name,
                "num_investors": len(investor_ids),
                "investors": ", ".join(investor_details),
                "avg_percent": total_percent / len(investor_ids),
                "total_value": total_value,
            })

        df = pd.DataFrame(results)
        return df.sort_values("avg_percent", ascending=False).reset_index(drop=True)

    def rank_by_ownership_count(self, investor_ids: Optional[list[str]] = None) -> pd.DataFrame:
        """
        Rank stocks by number of investors holding them.

        Args:
            investor_ids: List of investor IDs (if None, uses grand portfolio)

        Returns:
            DataFrame sorted by ownership count descending
        """
        if investor_ids is None:
            # Use grand portfolio from Dataroma
            grand = self.scraper.get_grand_portfolio()
            if grand.empty:
                return pd.DataFrame()
            return grand.sort_values("num_owners", ascending=False).reset_index(drop=True)

        # Manual calculation from individual portfolios
        portfolios = [self._get_portfolio(inv_id) for inv_id in investor_ids]

        # Aggregate all holdings
        stock_counts: dict[str, dict] = {}

        for inv_id, pf in zip(investor_ids, portfolios):
            if pf.empty:
                continue
            for _, row in pf.iterrows():
                symbol = row["symbol"]
                if symbol not in stock_counts:
                    stock_counts[symbol] = {
                        "symbol": symbol,
                        "stock": row["stock"],
                        "num_owners": 0,
                        "owners": [],
                        "total_value": 0.0,
                        "total_percent": 0.0,
                    }
                stock_counts[symbol]["num_owners"] += 1
                stock_counts[symbol]["owners"].append(inv_id)
                stock_counts[symbol]["total_value"] += row["value"]
                stock_counts[symbol]["total_percent"] += row["percent_portfolio"]

        if not stock_counts:
            return pd.DataFrame()

        # Convert to DataFrame
        results = []
        for data in stock_counts.values():
            results.append({
                "symbol": data["symbol"],
                "stock": data["stock"],
                "num_owners": data["num_owners"],
                "owners": ", ".join(data["owners"]),
                "avg_percent": data["total_percent"] / data["num_owners"],
                "total_value": data["total_value"],
            })

        df = pd.DataFrame(results)
        return df.sort_values("num_owners", ascending=False).reset_index(drop=True)

    def calculate_conviction_score(self, investor_ids: list[str]) -> pd.DataFrame:
        """
        Calculate conviction score for each stock.
        Score = average portfolio weight * number of investors holding it

        Higher score means more investors hold it with higher conviction.

        Args:
            investor_ids: List of investor IDs to analyze

        Returns:
            DataFrame with conviction scores, sorted descending
        """
        ranked = self.rank_by_ownership_count(investor_ids)

        if ranked.empty:
            return pd.DataFrame(columns=["symbol", "stock", "conviction_score", "num_owners", "avg_percent"])

        # conviction_score = avg_percent * num_owners
        ranked["conviction_score"] = ranked["avg_percent"] * ranked["num_owners"]

        result = ranked[["symbol", "stock", "conviction_score", "num_owners", "avg_percent", "total_value"]]
        return result.sort_values("conviction_score", ascending=False).reset_index(drop=True)

    def get_top_picks(
        self,
        investor_ids: list[str],
        min_owners: int = 2,
        min_avg_percent: float = 1.0,
        top_n: int = 20
    ) -> pd.DataFrame:
        """
        Get top stock picks based on conviction score with filters.

        Args:
            investor_ids: List of investor IDs
            min_owners: Minimum number of investors holding the stock
            min_avg_percent: Minimum average portfolio percentage
            top_n: Number of top picks to return

        Returns:
            DataFrame of top conviction picks
        """
        scores = self.calculate_conviction_score(investor_ids)

        if scores.empty:
            return scores

        # Apply filters
        filtered = scores[
            (scores["num_owners"] >= min_owners) &
            (scores["avg_percent"] >= min_avg_percent)
        ]

        return filtered.head(top_n).reset_index(drop=True)


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    analyzer = OverlapAnalyzer()

    # Get investor list first
    investors = analyzer.scraper.get_investor_list()
    console.print("\n[bold]Available Investors:[/bold]")
    console.print(investors[["investor_id", "name"]].head(10))

    if not investors.empty:
        # Pick top 5 investors
        top_investors = investors["investor_id"].head(5).tolist()
        console.print(f"\n[bold]Analyzing: {top_investors}[/bold]")

        # Common holdings
        console.print("\n[bold cyan]=== Common Holdings ===[/bold cyan]")
        common = analyzer.find_common_holdings(top_investors)
        console.print(common.head(10))

        # Rank by ownership
        console.print("\n[bold cyan]=== Ranked by Ownership ===[/bold cyan]")
        ranked = analyzer.rank_by_ownership_count(top_investors)
        console.print(ranked.head(10))

        # Conviction scores
        console.print("\n[bold cyan]=== Conviction Scores ===[/bold cyan]")
        conviction = analyzer.calculate_conviction_score(top_investors)
        console.print(conviction.head(10))
