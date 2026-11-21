"""Steps 3 + 4: knockout checks and metric calculations.

Every number is calculated HERE, in code. Jev only interprets.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Literal

from .models import AltmanResult, Blocker, Company, FinancialStatement, Metrics

DSCR_MIN = 1.2          # banks want cash flow >= 1.2 x debt payments
ANNUAL_RATE = 0.09      # indicative interest rate
LOAN_MONTHS = 60

# Altman zones: (safe above, distress below)
ALTMAN_MANUFACTURING_ZONES = (2.9, 1.23)      # Z'
ALTMAN_NON_MANUFACTURING_ZONES = (2.6, 1.1)   # Z''

# receipts from many small customers (excluded from concentration)
RETAIL_SOURCES = {"POS receipts", "Store receipts", "Other customers"}

Readiness = Literal["ready", "almost", "not_ready"]
READINESS_ORDER: list[Readiness] = ["not_ready", "almost", "ready"]


def check_blockers(company: Company) -> list[Blocker]:
    """Knockout criteria, from public data (tax ID)."""
    p = company.public
    blockers: list[Blocker] = []
    if p.insolvency:
        blockers.append(Blocker(code="insolvency", message="The company is insolvent.",
                                action="No bank finances a company in insolvency."))
    if p.anaf_debt > 0:
        blockers.append(Blocker(code="anaf_debt", message=f"You owe {p.anaf_debt:,.0f} RON to ANAF.",
                                action="Pay the arrears and request a tax clearance certificate."))
    if p.years_active < 1:
        blockers.append(Blocker(code="too_young", message="The company has been active for less than a year.",
                                action="Come back after the first annual balance sheet."))
    if p.equity < 0:
        blockers.append(Blocker(code="negative_equity", message="Equity is negative.",
                                action="Discuss a capital increase with your accountant."))
    # TODO: payment incidents (CIP), negative profit, etc.
    return blockers


def _max_loan(monthly_rate: float) -> float:
    """Annuity formula: the loan amount that matches a given monthly payment."""
    r = ANNUAL_RATE / 12
    return monthly_rate * (1 - (1 + r) ** -LOAN_MONTHS) / r


def _is_manufacturing(caen: str) -> bool:
    """CAEN divisions 10-33 are manufacturing."""
    division = caen[:2]
    return division.isdigit() and 10 <= int(division) <= 33


def altman_z(f: FinancialStatement, caen: str) -> AltmanResult | None:
    """Altman score for private companies.

    Z'  (manufacturing):     0.717A + 0.847B + 3.107C + 0.420D + 0.998E
    Z'' (non-manufacturing): 6.56A + 3.26B + 6.72C + 1.05D
    """
    if f.total_assets <= 0 or f.total_liabilities <= 0:
        return None  # never invent a score from incomplete data

    a = (f.current_assets - f.current_liabilities) / f.total_assets
    b = f.retained_earnings / f.total_assets
    c = f.ebit / f.total_assets
    d = f.equity / f.total_liabilities

    if _is_manufacturing(caen):
        e = f.revenue / f.total_assets
        score = 0.717 * a + 0.847 * b + 3.107 * c + 0.420 * d + 0.998 * e
        model = "Z'"
        safe, distress = ALTMAN_MANUFACTURING_ZONES
    else:
        score = 6.56 * a + 3.26 * b + 6.72 * c + 1.05 * d
        model = "Z''"
        safe, distress = ALTMAN_NON_MANUFACTURING_ZONES

    zone = "safe" if score > safe else "distress" if score < distress else "grey"
    return AltmanResult(score=round(score, 2), zone=zone, model=model)


def compute_metrics(company: Company) -> Metrics:
    tx = company.transactions

    income_by_month: dict[str, float] = defaultdict(float)
    net_by_month: dict[str, float] = defaultdict(float)
    by_client: dict[str, float] = defaultdict(float)
    debt_service = 0.0

    for t in tx:
        m = t.date[:7]
        if t.type == "in":
            income_by_month[m] += t.amount
            net_by_month[m] += t.amount
            if t.counterparty not in RETAIL_SOURCES:
                by_client[t.counterparty] += t.amount
        else:
            net_by_month[m] -= t.amount
            if t.category == "loan_payment":
                debt_service += t.amount

    incomes = list(income_by_month.values())
    avg_income = mean(incomes)
    nets = sorted(net_by_month.values())

    total_income = sum(incomes)
    top_name, top_amount = max(by_client.items(), key=lambda kv: kv[1], default=("-", 0.0))

    due = [t for t in tx if t.due_date]
    late = [t for t in due if t.date > t.due_date]

    weak_net = mean(nets[:3])                     # the 3 weakest months
    existing_monthly_debt = debt_service / len(net_by_month)
    # existing payments are already deducted from net, so the new payment comes on top.
    # Prudent: average of a typical month and the weak months, divided by DSCR.
    max_rate = max(0.0, (mean(nets) + max(weak_net, 0)) / 2 / DSCR_MIN)

    # DSCR = cash available for debt / all debt payments (existing + new)
    cash_for_debt = mean(nets) + existing_monthly_debt
    total_debt_service = existing_monthly_debt + max_rate
    dscr = round(cash_for_debt / total_debt_service, 2) if total_debt_service > 0 else None

    altman = altman_z(company.financials, company.public.caen) if company.financials else None

    return Metrics(
        avg_monthly_income=round(avg_income),
        income_variation=round(pstdev(incomes) / avg_income, 3),
        seasonality=round(min(incomes) / avg_income, 3),
        top_client_share=round(top_amount / total_income, 3),
        top_client_name=top_name,
        late_payment_share=round(len(late) / len(due), 3) if due else 0.0,
        avg_net_cash_flow=round(mean(nets)),
        weak_months_net_cash_flow=round(weak_net),
        existing_debt_service=round(existing_monthly_debt),
        max_monthly_rate=round(max_rate),
        max_loan=round(_max_loan(max_rate), -3),
        dscr=dscr,
        altman=altman,
    )


def readiness_cap(m: Metrics) -> Readiness:
    """The best verdict the numbers allow. Neither rules nor Jev can go above it.

    DSCR below the minimum -> not_ready
    Altman safe -> ready, grey or missing -> almost, distress -> not_ready
    """
    if m.dscr is None or m.dscr < DSCR_MIN:
        return "not_ready"
    if m.altman is None:
        return "almost"
    return {"safe": "ready", "grey": "almost", "distress": "not_ready"}[m.altman.zone]


def apply_readiness_cap(readiness: Readiness, m: Metrics) -> Readiness:
    """Return the stricter of the proposed verdict and the numeric cap."""
    cap = readiness_cap(m)
    return min(readiness, cap, key=READINESS_ORDER.index)


def detect_problems(m: Metrics) -> list[str]:
    """The company's real problems, ordered by severity.
    TODO (team): calibrate the thresholds with the banker."""
    rules = [
        ("repayment", m.avg_net_cash_flow <= 0),
        ("financial_distress", m.altman is not None and m.altman.zone == "distress"),
        ("concentration", m.top_client_share > 0.5),
        ("late_payments", m.late_payment_share > 0.10),
        ("seasonality", m.seasonality < 0.5 or m.weak_months_net_cash_flow < 0),
        ("stability", m.income_variation > 0.35),
    ]
    return [name for name, hit in rules if hit]


def build_dossier(company: Company, m: Metrics) -> str:
    """The plain-language file Jev reads (like a credit analyst)."""
    p = company.public
    dscr_text = f"{m.dscr:.2f}" if m.dscr is not None else "not available"
    altman_text = (f"{m.altman.model} {m.altman.score:.2f} ({m.altman.zone} zone)"
                   if m.altman else "not available")
    return (
        f"Company: {p.name}, CAEN {p.caen}, {p.years_active:g} years in business. "
        f"Equity {p.equity:,.0f} RON, last year's profit {p.last_year_profit:,.0f} RON. "
        f"Average monthly income {m.avg_monthly_income:,.0f} RON, variation {m.income_variation:.0%}. "
        f"The weakest month has {m.seasonality:.0%} of the monthly average. "
        f"The top client ({m.top_client_name}) brings {m.top_client_share:.0%} of income. "
        f"{m.late_payment_share:.0%} of payments with a due date were late. "
        f"Average net cash flow {m.avg_net_cash_flow:,.0f} RON/month; "
        f"in the 3 weakest months {m.weak_months_net_cash_flow:,.0f} RON/month. "
        f"Existing loan payments {m.existing_debt_service:,.0f} RON/month. "
        f"DSCR at the recommended payment: {dscr_text}. "
        f"Altman score: {altman_text}."
    )
