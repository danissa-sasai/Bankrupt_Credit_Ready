"""The API: connects all the steps.

Run:   uvicorn app.main:app --reload
Test:  http://localhost:8000/analyze/RO11111111
Docs:  http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .analysis import build_dossier, check_blockers, compute_metrics
from .demo_data import DEMO_COMPANIES, get_company
from .jev_client import diagnose
from .models import AnalysisResult
from .plan import build_plan

app = FastAPI(title="Credit Ready")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/companies")
def list_demo_companies():
    """For the demo screen: the list of fictional companies."""
    return [{"cui": c.public.cui, "name": c.public.name, "story": c.story}
            for c in DEMO_COMPANIES.values()]


@app.get("/analyze/{cui}", response_model=AnalysisResult)
def analyze(cui: str):
    company = get_company(cui)
    if not company:
        raise HTTPException(404, "Company not found")

    blockers = check_blockers(company)            # step 3: knockout criteria
    metrics = compute_metrics(company)            # step 4: calculations, DSCR, Altman
    diagnosis = None
    if not blockers:
        dossier = build_dossier(company, metrics) # step 5: text file
        diagnosis = diagnose(dossier, metrics)    # step 6: Jev (or rules) + numeric cap
    plan = build_plan(blockers, metrics, diagnosis)  # step 7: plan

    return AnalysisResult(company=company.public, blockers=blockers,
                          metrics=metrics, diagnosis=diagnosis, plan=plan)


# Next TODOs:
# - POST /analyze with an uploaded bank statement (CSV)
# - stress test: 3 modified files (weak year, no main client) -> Jev can_pay
# - frontend: the 3 screens
