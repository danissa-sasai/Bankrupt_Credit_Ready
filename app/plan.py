"""Step 7: the 30-90 day action plan.

The texts are written by the team (not by AI), using the company's real numbers.
TODO (team): rewrite the texts in the owner's language and test them with the client.
"""
from __future__ import annotations

from .analysis import detect_problems
from .models import ActionStep, Blocker, Diagnosis, Metrics


def build_plan(blockers: list[Blocker], m: Metrics, d: Diagnosis | None) -> list[ActionStep]:
    if blockers:
        return [ActionStep(title=b.message, detail=b.action) for b in blockers][:3]

    altman_score = f"{m.altman.score:.2f}" if m.altman else "n/a"
    steps: dict[str, ActionStep] = {
        "concentration": ActionStep(
            title=f"You depend too much on {m.top_client_name} ({m.top_client_share:.0%})",
            detail="Bring in at least one more client that generates 20% of income.",
        ),
        "late_payments": ActionStep(
            title=f"{m.late_payment_share:.0%} of payments were late",
            detail="Pay suppliers and taxes on time for 2-3 months in a row. Banks check this.",
        ),
        "seasonality": ActionStep(
            title=f"Your weakest month has only {m.seasonality:.0%} of the average",
            detail="Set aside a reserve in strong months to cover payments in weak months.",
        ),
        "stability": ActionStep(
            title=f"Your monthly income varies by {m.income_variation:.0%} around the average",
            detail="Look for recurring contracts (subscriptions, monthly clients).",
        ),
        "repayment": ActionStep(
            title="Your cash flow does not leave room for a loan payment",
            detail="Cut fixed costs or request a smaller amount over a longer period.",
        ),
        "financial_distress": ActionStep(
            title=f"Your balance sheet looks fragile (Altman score {altman_score})",
            detail="Review debt, working capital and retained profit with your accountant.",
        ),
    }

    problems = detect_problems(m)
    if d and d.main_issue in problems:      # the issue chosen by Jev comes first
        problems.remove(d.main_issue)
        problems.insert(0, d.main_issue)
    plan = [steps[k] for k in problems][:3]

    if not problems:
        if d and d.readiness == "ready":
            plan.append(ActionStep(title="You are ready for a loan 🎉",
                                   detail="Your indicators look good. You can go to the bank."))
        elif m.altman is None:
            plan.append(ActionStep(title="We need your latest balance sheet",
                                   detail="Without it we cannot check the company's financial strength."))
        else:
            plan.append(ActionStep(title=f"Your balance sheet needs attention (Altman score {altman_score})",
                                   detail="Review debt and working capital with your accountant before applying."))

    if m.max_loan > 0 and (d is None or d.readiness != "not_ready"):
        plan.append(ActionStep(
            title=f"You can request up to {m.max_loan:,.0f} RON now",
            detail=f"Maximum recommended payment: {m.max_monthly_rate:,.0f} RON/month, over 5 years.",
        ))
    return plan
