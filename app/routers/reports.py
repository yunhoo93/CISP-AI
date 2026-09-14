# app/routers/reports.py

from fastapi import APIRouter, HTTPException
from app.models.report_schema import (
    ReportListResponse,
    ReportDetail,
    ReportListItem
)
from app.services.report_storage_service import ReportStorageService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=ReportListResponse)
async def get_all_reports():
    """
    모든 보고서 목록 조회
    
    **저장된 모든 보고서의 목록을 반환합니다.**
    """
    reports = ReportStorageService.get_all_reports()
    
    report_items = [
        ReportListItem(
            report_id=r["report_id"],
            case_id=r.get("case_id"),
            report_type=r["report_type"],
            title=r["title"],
            created_at=r["created_at"]
        )
        for r in reports
    ]
    
    return ReportListResponse(
        total=len(report_items),
        reports=report_items
    )


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(report_id: str):
    """
    특정 보고서 조회
    
    **report_id로 보고서의 전체 내용을 조회합니다.**
    """
    report = ReportStorageService.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다")
    
    return ReportDetail(
        report_id=report["report_id"],
        case_id=report.get("case_id"),
        report_type=report["report_type"],
        title=report["title"],
        content=report["content"],
        created_at=report["created_at"]
    )


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """
    보고서 삭제
    
    **report_id로 보고서를 삭제합니다.**
    """
    success = ReportStorageService.delete_report(report_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다")
    
    return {"message": "보고서가 삭제되었습니다", "report_id": report_id}