# app/services/investigation_file_service.py

from app.models.investigation_file_schema import (
    InvestigationFilesRequest,
    InvestigationFilesResponse,
    AnalysisTarget
)


class InvestigationFileService:
    
    @staticmethod
    def schedule_analysis(request: InvestigationFilesRequest) -> InvestigationFilesResponse:
        """
        조사 파일 분석 작업 스케줄링
        이미 업로드된 파일들에 대한 분석 작업 등록
        """
        print("\n" + "=" * 70)
        print("📂 조사 파일 분석 작업 등록")
        print("=" * 70)
        print(f"사건: {request.case_detail.title} ({request.case_detail.case_id})")
        print(f"파일 수: {len(request.investigation_files)}개")
        print(f"법리 기준: {len(request.legal_criteria)}개")
        
        targets = []
        
        # 파일 타입 → 분석 타입 매핑
        file_type_mapping = {
            "VIDEO": "VDO",
            "AUDIO": "STT",
            "IMAGE": "IMG",
            "DOCUMENT": "DOC"
        }
        
        for file_info in request.investigation_files:
            analysis_type = file_type_mapping.get(file_info.file_type.upper(), "DOC")
            
            target = AnalysisTarget(
                origin_name=file_info.origin_name,
                file_type=file_info.file_type,
                analysis_type=analysis_type
            )
            
            targets.append(target)
            print(f"  [{file_info.job_id}] {file_info.origin_name} ({file_info.file_type} → {analysis_type})")
        
        print("=" * 70)
        print(f"✅ {len(targets)}개 파일 분석 대기 (PENDING)")
        print("=" * 70)
        
        return InvestigationFilesResponse(
            status="PENDING",
            targets=targets
        )