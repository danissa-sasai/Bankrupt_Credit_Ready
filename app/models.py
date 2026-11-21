"""Data structures used across the application."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel


class Transaction(BaseModel):
    date: str                      # "2026-03-14"
    amount: float                  # RON, always positive
    type: Literal["in", "out"]
    counterparty: str
    category: Literal["client", "supplier", "payroll", "taxes", "rent", "loan_payment"]
    due_date: Optional[str] = None # due date, for suppliers and taxes


class CompanyPublic(BaseModel):
    """What we learn from the tax ID alone (public ANAF / ONRC data)."""
    cui: str
    name: str
    caen: str
    years_active: float
    anaf_debt: float
    insolvency: bool
    equity: float
    last_year_profit: float


class FinancialStatement(BaseModel):
    """Annual balance sheet and income statement figures, in RON."""
    year: int
    total_assets: float
    current_assets: float
    current_liabilities: float     # due within one year
    retained_earnings: float       # accumulated profit (accounts 106, 117, 121, 129)
    ebit: float                    # operating result
    equity: float
    total_liabilities: float
    revenue: float                 # net turnover


class Company(BaseModel):
    public: CompanyPublic
    transactions: list[Transaction]
    financials: Optional[FinancialStatement] = None
    story: str = ""


class AltmanResult(BaseModel):
    """Financial fragility signal. It is not a default probability or a bank rating."""
    score: float
    zone: Literal["safe", "grey", "distress"]
    model: Literal["Z'", "Z''"]    # Z' = manufacturing, Z'' = non-manufacturing


class Metrics(BaseModel):
    """Computed by code. The AI never calculates these."""
    avg_monthly_income: float
    income_variation: float        # standard deviation / mean
    seasonality: float             # weakest month / mean
    top_client_share: float
    top_client_name: str
    late_payment_share: float
    avg_net_cash_flow: float
    weak_months_net_cash_flow: float
    existing_debt_service: float
    max_monthly_rate: float
    max_loan: float
    dscr: Optional[float] = None   # at the recommended payment; None if there is no debt service
    altman: Optional[AltmanResult] = None  # None if the balance sheet is missing or unusable


class Blocker(BaseModel):
    """Knockout criterion (e.g. tax debt)."""
    code: str
    message: str
    action: str


class Diagnosis(BaseModel):
    """The verdict: from Jev, or from rules if Jev does not respond."""
    readiness: Literal["ready", "almost", "not_ready"]
    confidence: float
    main_issue: Literal["stability", "seasonality", "concentration", "late_payments",
                        "repayment", "financial_distress"]
    product: Literal["credit_line", "investment_loan", "factoring", "leasing"]
    can_pay_weak_months: float
    source: Literal["jev", "fallback"]


class ActionStep(BaseModel):
    title: str
    detail: str


class AnalysisResult(BaseModel):
    company: CompanyPublic
    blockers: list[Blocker]
    metrics: Metrics
    diagnosis: Optional[Diagnosis]  # None if the company is blocked
    plan: list[ActionStep]
