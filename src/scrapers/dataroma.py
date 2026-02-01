"""Dataroma scraper for super investor portfolios."""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Optional


class DataromaScraper:
    """Scraper for Dataroma website."""

    BASE_URL = "https://www.dataroma.com/m"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get_soup(self, url: str) -> BeautifulSoup:
        """Fetch URL and return BeautifulSoup object."""
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def get_investor_list(self) -> pd.DataFrame:
        """
        Get list of tracked super investors from Dataroma.

        Returns:
            DataFrame with columns: investor_id, name, portfolio_date, market_value
        """
        url = f"{self.BASE_URL}/managers.php"
        soup = self._get_soup(url)

        investors = []
        table = soup.find("table", {"id": "grid"})

        if not table:
            return pd.DataFrame(columns=["investor_id", "name", "portfolio_date", "market_value"])

        rows = table.find_all("tr")[1:]  # Skip header row

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                # Extract investor link and ID
                link = cols[0].find("a")
                if link:
                    href = link.get("href", "")
                    # Extract investor_id from URL like "holdings.php?m=BRK"
                    investor_id = href.split("m=")[-1] if "m=" in href else ""
                    name = link.get_text(strip=True)

                    # Portfolio date
                    portfolio_date = cols[1].get_text(strip=True) if len(cols) > 1 else ""

                    # Market value
                    market_value = cols[2].get_text(strip=True) if len(cols) > 2 else ""

                    investors.append({
                        "investor_id": investor_id,
                        "name": name,
                        "portfolio_date": portfolio_date,
                        "market_value": market_value,
                    })

        return pd.DataFrame(investors)

    def get_portfolio(self, investor_id: str) -> pd.DataFrame:
        """
        Get current portfolio holdings for a specific investor.

        Args:
            investor_id: Investor ID (e.g., 'BRK' for Berkshire Hathaway)

        Returns:
            DataFrame with columns: stock, symbol, percent_portfolio, shares,
                                   reported_price, value, activity
        """
        url = f"{self.BASE_URL}/holdings.php?m={investor_id}"
        soup = self._get_soup(url)

        holdings = []
        table = soup.find("table", {"id": "grid"})

        if not table:
            return pd.DataFrame(columns=[
                "stock", "symbol", "percent_portfolio", "shares",
                "reported_price", "value", "activity"
            ])

        rows = table.find_all("tr")[1:]  # Skip header row

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 7:
                # Column structure:
                # 0: History, 1: Stock (symbol + name), 2: % Portfolio
                # 3: Activity, 4: Shares, 5: Reported Price, 6: Value

                # Stock name and symbol from column 1
                stock_cell = cols[1]
                stock_link = stock_cell.find("a")

                if not stock_link:
                    continue

                # Extract symbol from href (most reliable)
                href = stock_link.get("href", "")
                if "sym=" in href:
                    symbol = href.split("sym=")[-1].split("&")[0]
                else:
                    # Fallback: symbol is direct text before span
                    symbol = ""
                    for child in stock_link.children:
                        if isinstance(child, str):
                            symbol = child.strip()
                            break

                # Stock name is in <span>
                span = stock_link.find("span")
                stock_name = span.get_text(strip=True).lstrip("- ").strip() if span else ""

                # Percent of portfolio (column 2)
                percent = cols[2].get_text(strip=True).replace("%", "")

                # Recent activity (column 3)
                activity = cols[3].get_text(strip=True)

                # Shares (column 4)
                shares = cols[4].get_text(strip=True).replace(",", "")

                # Reported price (column 5)
                reported_price = cols[5].get_text(strip=True).replace("$", "").replace(",", "")

                # Value (column 6)
                value = cols[6].get_text(strip=True).replace("$", "").replace(",", "")

                holdings.append({
                    "stock": stock_name,
                    "symbol": symbol,
                    "percent_portfolio": self._parse_float(percent),
                    "shares": self._parse_int(shares),
                    "reported_price": self._parse_float(reported_price),
                    "value": self._parse_float(value),
                    "activity": activity,
                })

        df = pd.DataFrame(holdings)
        df["investor_id"] = investor_id
        return df

    def get_grand_portfolio(self) -> pd.DataFrame:
        """
        Get the grand portfolio showing stocks held by multiple super investors.

        Returns:
            DataFrame with columns: stock, symbol, num_owners, total_value,
                                   percent_total, owners
        """
        url = f"{self.BASE_URL}/g/portfolio.php"
        soup = self._get_soup(url)

        stocks = []
        table = soup.find("table", {"id": "grid"})

        if not table:
            return pd.DataFrame(columns=[
                "stock", "symbol", "num_owners", "total_value", "percent_total", "owners"
            ])

        rows = table.find_all("tr")[1:]  # Skip header row

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                # Stock name and symbol
                stock_cell = cols[0]
                stock_link = stock_cell.find("a")
                stock_name = stock_link.get_text(strip=True) if stock_link else ""

                # Symbol
                symbol_span = stock_cell.find("span", {"class": "sym"})
                if symbol_span:
                    symbol = symbol_span.get_text(strip=True)
                else:
                    href = stock_link.get("href", "") if stock_link else ""
                    symbol = href.split("s=")[-1].split("&")[0] if "s=" in href else ""

                # Number of owners
                num_owners = cols[1].get_text(strip=True) if len(cols) > 1 else "0"

                # Total value
                total_value = cols[2].get_text(strip=True).replace("$", "").replace(",", "") if len(cols) > 2 else "0"

                # Percent of total
                percent_total = cols[3].get_text(strip=True).replace("%", "") if len(cols) > 3 else "0"

                # List of owners (if available in additional column or tooltip)
                owners_cell = cols[4] if len(cols) > 4 else None
                owners = owners_cell.get_text(strip=True) if owners_cell else ""

                stocks.append({
                    "stock": stock_name,
                    "symbol": symbol,
                    "num_owners": self._parse_int(num_owners),
                    "total_value": self._parse_float(total_value),
                    "percent_total": self._parse_float(percent_total),
                    "owners": owners,
                })

        return pd.DataFrame(stocks)

    def get_stock_owners(self, symbol: str) -> pd.DataFrame:
        """
        Get list of super investors who own a specific stock.

        Args:
            symbol: Stock ticker symbol

        Returns:
            DataFrame with columns: investor_id, investor_name, shares,
                                   percent_portfolio, value
        """
        url = f"{self.BASE_URL}/stock.php?s={symbol}"
        soup = self._get_soup(url)

        owners = []
        table = soup.find("table", {"id": "grid"})

        if not table:
            return pd.DataFrame(columns=[
                "investor_id", "investor_name", "shares", "percent_portfolio", "value"
            ])

        rows = table.find_all("tr")[1:]

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                investor_link = cols[0].find("a")
                if investor_link:
                    href = investor_link.get("href", "")
                    investor_id = href.split("m=")[-1] if "m=" in href else ""
                    investor_name = investor_link.get_text(strip=True)

                    shares = cols[1].get_text(strip=True).replace(",", "") if len(cols) > 1 else "0"
                    percent = cols[2].get_text(strip=True).replace("%", "") if len(cols) > 2 else "0"
                    value = cols[3].get_text(strip=True).replace("$", "").replace(",", "") if len(cols) > 3 else "0"

                    owners.append({
                        "investor_id": investor_id,
                        "investor_name": investor_name,
                        "shares": self._parse_int(shares),
                        "percent_portfolio": self._parse_float(percent),
                        "value": self._parse_float(value),
                        "symbol": symbol,
                    })

        return pd.DataFrame(owners)

    @staticmethod
    def _parse_float(value: str) -> float:
        """Parse string to float, handling empty or invalid values."""
        try:
            return float(value.replace(",", "").replace("$", "").replace("%", "").strip())
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _parse_int(value: str) -> int:
        """Parse string to int, handling empty or invalid values."""
        try:
            return int(value.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0


if __name__ == "__main__":
    # Quick test
    scraper = DataromaScraper()

    print("=== Investor List ===")
    investors = scraper.get_investor_list()
    print(investors.head(10))

    if not investors.empty:
        first_investor = investors.iloc[0]["investor_id"]
        print(f"\n=== Portfolio: {first_investor} ===")
        portfolio = scraper.get_portfolio(first_investor)
        print(portfolio.head(10))

    print("\n=== Grand Portfolio ===")
    grand = scraper.get_grand_portfolio()
    print(grand.head(10))
