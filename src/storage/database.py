"""Database storage for portfolio data."""

from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


class PortfolioSnapshot(Base):
    """Portfolio snapshot model."""

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True)
    investor_id = Column(String(50), index=True, nullable=False)
    quarter = Column(String(10), index=True, nullable=False)  # e.g., "2024Q3"
    snapshot_date = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20), nullable=False)
    stock = Column(String(200))
    shares = Column(Integer, default=0)
    value = Column(Float, default=0.0)
    percent_portfolio = Column(Float, default=0.0)
    reported_price = Column(Float, default=0.0)
    activity = Column(String(100))


class Database:
    """Database handler for storing portfolio data."""

    def __init__(self, db_path: str = "data/investor_tracker.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """Initialize database tables."""
        Base.metadata.create_all(self.engine)

    def save_portfolio(
        self,
        investor_id: str,
        portfolio_df: pd.DataFrame,
        quarter: Optional[str] = None
    ):
        """
        Save portfolio snapshot to database.

        Args:
            investor_id: Investor ID
            portfolio_df: DataFrame with portfolio holdings
            quarter: Quarter string (e.g., "2024Q3"). Auto-generated if None.
        """
        if quarter is None:
            now = datetime.now()
            quarter = f"{now.year}Q{(now.month - 1) // 3 + 1}"

        session = self.Session()
        try:
            # Delete existing snapshot for this investor/quarter
            session.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.investor_id == investor_id,
                PortfolioSnapshot.quarter == quarter
            ).delete()

            # Insert new records
            for _, row in portfolio_df.iterrows():
                snapshot = PortfolioSnapshot(
                    investor_id=investor_id,
                    quarter=quarter,
                    symbol=row.get("symbol", ""),
                    stock=row.get("stock", ""),
                    shares=int(row.get("shares", 0)),
                    value=float(row.get("value", 0.0)),
                    percent_portfolio=float(row.get("percent_portfolio", 0.0)),
                    reported_price=float(row.get("reported_price", 0.0)),
                    activity=row.get("activity", ""),
                )
                session.add(snapshot)

            session.commit()
        finally:
            session.close()

    def get_portfolio(self, investor_id: str, quarter: str) -> pd.DataFrame:
        """
        Get portfolio for a specific quarter.

        Args:
            investor_id: Investor ID
            quarter: Quarter string (e.g., "2024Q3")

        Returns:
            DataFrame with portfolio holdings
        """
        session = self.Session()
        try:
            records = session.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.investor_id == investor_id,
                PortfolioSnapshot.quarter == quarter
            ).all()

            if not records:
                return pd.DataFrame()

            data = [{
                "symbol": r.symbol,
                "stock": r.stock,
                "shares": r.shares,
                "value": r.value,
                "percent_portfolio": r.percent_portfolio,
                "reported_price": r.reported_price,
                "activity": r.activity,
            } for r in records]

            return pd.DataFrame(data)
        finally:
            session.close()

    def get_latest_portfolio(self, investor_id: str) -> pd.DataFrame:
        """Get most recent portfolio for an investor."""
        quarters = self.get_available_quarters(investor_id)
        if not quarters:
            return pd.DataFrame()
        return self.get_portfolio(investor_id, quarters[0])

    def get_available_quarters(self, investor_id: str) -> list[str]:
        """Get list of available quarters for an investor, sorted descending."""
        session = self.Session()
        try:
            results = session.query(PortfolioSnapshot.quarter).filter(
                PortfolioSnapshot.investor_id == investor_id
            ).distinct().all()

            quarters = [r[0] for r in results]
            return sorted(quarters, reverse=True)
        finally:
            session.close()

    def get_all_investors(self) -> list[str]:
        """Get list of all investors in database."""
        session = self.Session()
        try:
            results = session.query(PortfolioSnapshot.investor_id).distinct().all()
            return [r[0] for r in results]
        finally:
            session.close()
