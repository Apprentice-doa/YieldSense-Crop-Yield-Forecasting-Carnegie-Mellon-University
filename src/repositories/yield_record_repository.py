from __future__ import annotations
from typing import List, Optional
from sqlalchemy.orm import Session
from src.db.models.yield_record import YieldRecord


class YieldRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, record: YieldRecord) -> YieldRecord:
        self.db.add(record)
        self.db.flush()
        return record

    def get_by_id(self, record_id: int) -> Optional[YieldRecord]:
        return self.db.query(YieldRecord).filter(YieldRecord.id == record_id).first()

    def list_by_farmer(self, farmer_id: int) -> List[YieldRecord]:
        return (
            self.db.query(YieldRecord)
            .filter(YieldRecord.farmer_id == farmer_id)
            .order_by(YieldRecord.created_at.desc())
            .all()
        )
    def save_summary(self, record: YieldRecord, summary: str) -> YieldRecord:
        record.advisory_summary = summary
        self.db.flush()
        return record

    def commit(self) -> None:
        self.db.commit()
