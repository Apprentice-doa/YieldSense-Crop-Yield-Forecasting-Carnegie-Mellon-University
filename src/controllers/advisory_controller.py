from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.request import ActualYieldUpdate
from models.response import AdvisoryOut, YieldRecordOut
from src.db.session import get_db
from src.repositories.yield_record_repository import YieldRecordRepository
from src.utils.security import AuthenticatedFarmer, get_current_farmer, require_farmer_access

router = APIRouter()


@router.get(
    "/farmers/{farmer_id}/records",
    response_model=List[YieldRecordOut],
    summary="List all yield records for a farmer",
)
@router.get(
    "/farmers/{farmer_id}/yield-records",
    response_model=List[YieldRecordOut],
    summary="List all yield records for a farmer",
)
def list_yield_records(
    farmer_id: int,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> List[YieldRecordOut]:
    require_farmer_access(farmer_id, current)
    return YieldRecordRepository(db).list_by_farmer(farmer_id)


@router.get(
    "/farmers/{farmer_id}/advisory/{record_id}",
    response_model=AdvisoryOut,
    summary="Retrieve the saved advisory summary for a yield record",
)
def get_advisory(
    farmer_id: int,
    record_id: int,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> AdvisoryOut:
    require_farmer_access(farmer_id, current)
    record = YieldRecordRepository(db).get_by_id(record_id)
    if not record or record.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Yield record not found")
    return record


@router.patch(
    "/farmers/{farmer_id}/advisory/{record_id}/actual-yield",
    response_model=AdvisoryOut,
    summary="Record the actual harvested yield for a yield record",
)
def submit_actual_yield(
    farmer_id: int,
    record_id: int,
    payload: ActualYieldUpdate,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> AdvisoryOut:
    require_farmer_access(farmer_id, current)
    repo = YieldRecordRepository(db)
    record = repo.get_by_id(record_id)
    if not record or record.farmer_id != farmer_id:
        raise HTTPException(status_code=404, detail="Yield record not found")
    record.actual_yield_kg_per_ha = payload.actual_yield_kg_per_ha
    repo.commit()
    return record
