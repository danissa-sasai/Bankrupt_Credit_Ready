"""Synthetic data: 3 fictional companies, 12 months of transactions.

TODO (team): adjust the profiles so the stories come through clearly in the demo.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from .models import Company, CompanyPublic, FinancialStatement, Transaction


def _build(seed: int, monthly_income: list[float], clients: list[tuple[str, float]],
           fixed_costs: list[tuple[str, str, float]], supplier_share: float,
           late_prob: float, noise: float) -> list[Transaction]:
    rnd = random.Random(seed)  # fixed seed -> identical demo every time
    tx: list[Transaction] = []
    for i in range(12):  # Dec 2025 - Nov 2026
        month = (11 + i) % 12 + 1
        year = 2025 if i == 0 else 2026
        income = monthly_income[month - 1] * (1 + rnd.uniform(-noise, noise))

        for name, share in clients:
            tx.append(Transaction(date=str(date(year, month, rnd.randint(5, 24))),
                                  amount=round(income * share), type="in",
                                  counterparty=name, category="client"))

        for k, supplier in enumerate(["Furnizor Principal SRL", "Distribuitor Materii SA"]):
            due = date(year, month, 10 + k * 10)
            paid = due + timedelta(days=rnd.randint(5, 25)) if rnd.random() < late_prob else due
            tx.append(Transaction(date=str(paid), due_date=str(due),
                                  amount=round(income * supplier_share / 2), type="out",
                                  counterparty=supplier, category="supplier"))

        for name, category, amount in fixed_costs:
            due = date(year, month, 25)
            tx.append(Transaction(date=str(due),
                                  due_date=str(due) if category == "taxes" else None,
                                  amount=amount, type="out",
                                  counterparty=name, category=category))
    return sorted(tx, key=lambda t: t.date)


DEMO_COMPANIES: dict[str, Company] = {
    # 🟡 seasonal
    "RO11111111": Company(
        story="Seaside cafe: earns double in summer and barely covers costs in winter.",
        public=CompanyPublic(cui="RO11111111", name="Cafeneaua Valul SRL", caen="5630",
                             years_active=4, anaf_debt=0, insolvency=False,
                             equity=85_000, last_year_profit=62_000),
        financials=FinancialStatement(year=2025, total_assets=150_000, current_assets=70_000,
                                      current_liabilities=45_000, retained_earnings=75_000,
                                      ebit=74_000, equity=85_000, total_liabilities=65_000,
                                      revenue=560_000),
        transactions=_build(
            1, [22e3, 20e3, 26e3, 34e3, 52e3, 78e3, 95e3, 98e3, 60e3, 36e3, 25e3, 30e3],
            [("POS receipts", 0.85), ("Evenimente Corporate SRL", 0.15)],
            [("Payroll", "payroll", 14_000), ("Rent", "rent", 6_000), ("ANAF", "taxes", 4_500)],
            supplier_share=0.35, late_prob=0.08, noise=0.08),
    ),
    # 🔴 one large client
    "RO22222222": Company(
        story="IT company: 75% of its money comes from a single client.",
        public=CompanyPublic(cui="RO22222222", name="Pixel Code Solutions SRL", caen="6201",
                             years_active=3, anaf_debt=0, insolvency=False,
                             equity=40_000, last_year_profit=38_000),
        financials=FinancialStatement(year=2025, total_assets=190_000, current_assets=120_000,
                                      current_liabilities=125_000, retained_earnings=30_000,
                                      ebit=46_000, equity=40_000, total_liabilities=150_000,
                                      revenue=830_000),
        transactions=_build(
            2, [70e3] * 12,
            [("MegaRetail SA", 0.75), ("Clinica Nova SRL", 0.15), ("StartUp Hub SRL", 0.10)],
            [("Payroll", "payroll", 42_000), ("Rent", "rent", 5_000),
             ("ANAF", "taxes", 9_000), ("Car lease payment", "loan_payment", 2_500)],
            supplier_share=0.08, late_prob=0.25, noise=0.12),
    ),
    # 🟢 stable
    "RO33333333": Company(
        story="Building materials distributor: many clients, on-time payments.",
        public=CompanyPublic(cui="RO33333333", name="Construct Distrib SRL", caen="4673",
                             years_active=9, anaf_debt=0, insolvency=False,
                             equity=420_000, last_year_profit=145_000),
        financials=FinancialStatement(year=2025, total_assets=760_000, current_assets=480_000,
                                      current_liabilities=260_000, retained_earnings=360_000,
                                      ebit=175_000, equity=420_000, total_liabilities=340_000,
                                      revenue=1_550_000),
        transactions=_build(
            3, [110e3, 105e3, 125e3, 140e3, 150e3, 155e3, 150e3, 148e3, 140e3, 135e3, 120e3, 115e3],
            [("BuildCo SRL", 0.18), ("Casa Ta Construct SRL", 0.15), ("Renovări Expert SRL", 0.14),
             ("Store receipts", 0.33), ("Other customers", 0.20)],
            [("Payroll", "payroll", 30_000), ("Rent", "rent", 9_000), ("ANAF", "taxes", 11_000)],
            supplier_share=0.45, late_prob=0.02, noise=0.05),
    ),
}


def get_company(cui: str) -> Company | None:
    """TODO (production): replace with ANAF/ONRC APIs + open banking."""
    return DEMO_COMPANIES.get(cui.upper().replace(" ", ""))
