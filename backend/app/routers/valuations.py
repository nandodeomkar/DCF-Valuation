from fastapi import APIRouter, HTTPException

from app import db
from app.dcf.engine import DcfError, run_dcf
from app.models import DcfInputs, DcfResult, SavedValuation

router = APIRouter(prefix="/api", tags=["valuations"])


@router.post("/dcf", response_model=DcfResult)
def run(inputs: DcfInputs) -> DcfResult:
    try:
        return run_dcf(inputs)
    except DcfError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/valuations", response_model=list[SavedValuation])
def list_all() -> list[SavedValuation]:
    return db.list_valuations()


@router.post("/valuations", response_model=SavedValuation)
def save(valuation: SavedValuation) -> SavedValuation:
    return db.save_valuation(valuation)


@router.get("/valuations/{valuation_id}", response_model=SavedValuation)
def get_one(valuation_id: int) -> SavedValuation:
    valuation = db.get_valuation(valuation_id)
    if valuation is None:
        raise HTTPException(status_code=404, detail=f"No saved valuation with id {valuation_id}")
    return valuation


@router.delete("/valuations/{valuation_id}")
def delete(valuation_id: int) -> dict:
    if not db.delete_valuation(valuation_id):
        raise HTTPException(status_code=404, detail=f"No saved valuation with id {valuation_id}")
    return {"deleted": valuation_id}
