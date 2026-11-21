"""Step 6: Jev interprets the company file.

If Jev is not configured or fails (network, missing key), we use simple rules
so the demo still works. Either way, the numeric cap has the final say.

Setup:
    pip install typesafe-sdk
    export TYPESAFE_API_KEY=...        # or a gateway (OpenRouter / Vercel), see docs
"""
from __future__ import annotations

import os

from .analysis import apply_readiness_cap, detect_problems
from .models import Diagnosis, Metrics

ISSUE_CRITERIA = {
    "stability": "Income varies a lot from one month to another",
    "seasonality": "Has very weak months during the year",
    "concentration": "Depends on too few clients",
    "late_payments": "Pays suppliers or taxes late",
    "repayment": "Cash flow does not cover a loan payment",
    "financial_distress": "The balance sheet shows financial fragility (Altman distress zone)",
}


def diagnose_with_jev(dossier: str) -> Diagnosis:
    """Real call to Jev. TODO: check the response field names with a
    print(response) on the first call, the SDK is new."""
    from typesafe_sdk import Choice, Noul, TypeSafeClient  # local import: optional dependency

    client = TypeSafeClient()  # reads TYPESAFE_API_KEY
    response = client.system_one(
        state={"company_file": dossier},
        questions={
            "readiness": Choice(
                instructions="How ready is the company for a bank loan?",
                criteria={
                    "ready": "Stable income, on-time payments, can sustain a loan payment",
                    "almost": "Has 1-2 problems that can be fixed within 3 months",
                    "not_ready": "Serious cash flow, repayment or balance sheet problems",
                },
            ),
            "main_issue": Choice(
                instructions="What is the biggest obstacle to getting a loan?",
                criteria=ISSUE_CRITERIA,
            ),
            "product": Choice(
                instructions="Which type of financing fits best?",
                criteria={
                    "credit_line": "Needs short-term liquidity, variable income",
                    "investment_loan": "Stable company that wants to invest",
                    "factoring": "Has large invoices to collect from solid clients",
                    "leasing": "Wants to buy equipment or vehicles",
                },
            ),
            "can_pay": Noul(
                instructions="The company can pay a loan installment even in weak months.",
            ),
        },
    )
    a = response.answers
    return Diagnosis(
        readiness=a["readiness"].choice,
        confidence=a["readiness"].confidence,
        main_issue=a["main_issue"].choice,
        product=a["product"].choice,
        can_pay_weak_months=a["can_pay"].noul,
        source="jev",
    )


def diagnose_fallback(m: Metrics) -> Diagnosis:
    """Simple rules, used when Jev is unavailable."""
    found = detect_problems(m)
    readiness = "ready" if not found else ("almost" if len(found) <= 2 else "not_ready")
    if "repayment" in found:
        readiness = "not_ready"
    return Diagnosis(
        readiness=readiness,
        confidence=0.6,
        main_issue=found[0] if found else "stability",
        product="credit_line" if m.seasonality < 0.6 else "investment_loan",
        can_pay_weak_months=(0.9 if m.weak_months_net_cash_flow >= m.max_monthly_rate
                             else 0.6 if m.weak_months_net_cash_flow > 0 else 0.25),
        source="fallback",
    )


def diagnose(dossier: str, m: Metrics) -> Diagnosis:
    diagnosis = None
    if os.getenv("TYPESAFE_API_KEY"):
        try:
            diagnosis = diagnose_with_jev(dossier)
        except Exception as e:  # the demo must not crash
            print(f"[jev] error, switching to rules: {e}")
    if diagnosis is None:
        diagnosis = diagnose_fallback(m)
    return diagnosis.model_copy(
        update={"readiness": apply_readiness_cap(diagnosis.readiness, m)})
