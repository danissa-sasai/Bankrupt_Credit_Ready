# Credit Ready: backend skeleton (Python)

## Getting started
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- http://localhost:8000/docs → all endpoints, testable from the browser
- http://localhost:8000/companies → demo companies
- http://localhost:8000/analyze/RO11111111 → full analysis

## Demo companies
| Tax ID | Company | Altman | Result |
|---|---|---|---|
| RO11111111 | Cafeneaua Valul (seasonal) | safe | almost / seasonality |
| RO22222222 | Pixel Code (one client = 75%) | grey | almost / concentration |
| RO33333333 | Construct Distrib (stable) | safe | ready |

The balance sheets are fictional and exist only for the demo.

## Flow (`app/main.py`)
1. `demo_data.get_company`: tax ID + "connect bank" (simulated)
2. `analysis.check_blockers`: knockout criteria (ANAF, insolvency, company age)
3. `analysis.compute_metrics`: all numbers, including DSCR and Altman (code only, no AI)
4. `analysis.build_dossier`: the text file for Jev
5. `jev_client.diagnose`: Jev proposes a verdict; without a key or on failure, rules do
6. `analysis.apply_readiness_cap`: the numbers limit the verdict
7. `plan.build_plan`: the 30-90 day steps + the maximum amount

## Verdict limits
| DSCR | Altman safe | Altman grey or missing | Altman distress |
|---|---|---|---|
| **>= 1.2** | ready | almost | not_ready |
| **< 1.2** | not_ready | not_ready | not_ready |

The Altman score is a warning signal. Its coefficients were not calibrated on Romanian companies,
so it is not a default probability or a bank rating.

## Enabling Jev
```bash
pip install typesafe-sdk
export TYPESAFE_API_KEY=...
```
On the first call, add a `print(response)` in `diagnose_with_jev` and check the field names.
Without a key, the app runs on rules (`"source": "fallback"` in the response).

## To do (TODOs in the code)
- calibrate the `detect_problems` thresholds with the banker
- stress test: modified files (weak year, no main client) sent to Jev
- CSV bank statement upload
- frontend with the 3 screens
