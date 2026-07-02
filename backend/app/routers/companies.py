from fastapi import APIRouter, HTTPException

from app.models import CompanyPayload
from app.services import edgar, normalize

router = APIRouter(prefix="/api", tags=["companies"])


@router.get("/company/{ticker}", response_model=CompanyPayload)
def get_company(ticker: str, refresh: bool = False) -> CompanyPayload:
    try:
        cik = edgar.resolve_cik(ticker, force_refresh=refresh)
        facts = edgar.get_company_facts(cik, force_refresh=refresh)
        submissions = edgar.get_submissions(cik, force_refresh=refresh)
    except edgar.EdgarError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return normalize.normalize(ticker, cik, facts, submissions)
