# app/models/__init__.py

from .case_schema import CaseRequest, CaseResponse, CaseSummary
from .legal_criteria_schema import (
    LegalCriteriaRequest, 
    LegalCriteriaResponse,
    LegalIssue,
    LegalCriterion,
    CriteriaEvaluation
)
from .criteria_evaluation_schema import (
    CriteriaEvaluationRequest,
    CriteriaEvaluationResponse
)
from .investigation_file_schema import (
    FileUploadResponse,
    InvestigationFilesRequest,
    InvestigationFilesResponse,
    AnalysisTarget
)
from .analysis_document_schema import (
    AnalysisDocumentRequest,
    AnalysisDocumentResponse
)
from .analysis_image_schema import (
    AnalysisImageRequest,
    AnalysisImageResponse
)
from .analysis_media_schema import (
    AnalysisMediaRequest,
    AnalysisMediaResponse
)
from .analysis_callback_schema import (
    AnalysisCallbackRequest,
    AnalysisCallbackResponse
)
from .analysis_final_schema import (
    AnalysisFinalRequest,
    AnalysisFinalResponse
)
from .report_interim_schema import (
    ReportInterimRequest,
    ReportInterimResponse
)
from .report_final_schema import (
    ReportFinalRequest,
    ReportFinalResponse
)
from .report_decision_schema import (
    ReportDecisionRequest,
    ReportDecisionResponse
)
from .chat_schema import (
    ChatRequest,
    ChatResponse,
    UsedContext
)
from .report_schema import (
    ReportListItem,
    ReportDetail,
    ReportListResponse
)

__all__ = [
    "CaseRequest",
    "CaseResponse",
    "CaseSummary",
    "LegalCriteriaRequest",
    "LegalCriteriaResponse",
    "LegalIssue",
    "LegalCriterion",
    "CriteriaEvaluation",
    "CriteriaEvaluationRequest",
    "CriteriaEvaluationResponse",
    "FileUploadResponse",
    "InvestigationFilesRequest",
    "InvestigationFilesResponse",
    "AnalysisTarget",
    "AnalysisDocumentRequest",
    "AnalysisDocumentResponse",
    "AnalysisImageRequest",
    "AnalysisImageResponse",
    "AnalysisMediaRequest",
    "AnalysisMediaResponse",
    "AnalysisCallbackRequest",
    "AnalysisCallbackResponse",
    "AnalysisFinalRequest",
    "AnalysisFinalResponse",
    "ReportInterimRequest",
    "ReportInterimResponse",
    "ReportFinalRequest",
    "ReportFinalResponse",
    "ReportDecisionRequest",
    "ReportDecisionResponse",
    "ChatRequest",
    "ChatResponse",
    "UsedContext",
    "ReportListItem",
    "ReportDetail",
    "ReportListResponse",
]