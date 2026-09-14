# app/services/report_storage_service.py

import uuid
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_date():
    """날짜 포맷: YYYY.MM.DD."""
    return datetime.now().strftime("%Y.%m.%d.")


# ============================================================
# 한글 폰트 등록
# ============================================================

def register_korean_font():
    """한글 폰트 등록"""
    font_paths = [
        "app/fonts/malgun.ttf",
        "./fonts/malgun.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("korean_font", font_path))
                print(f"   ✅ 폰트 등록: {font_path}")
                return "korean_font"
            except Exception as e:
                print(f"   ⚠️ 폰트 등록 실패: {font_path} - {e}")
                continue

    print("   ⚠️ 기본 폰트 사용 (Helvetica)")
    return "Helvetica"


KOREAN_FONT = register_korean_font()

# 경찰 로고 경로
POLICE_LOGO_PATH = "app/images/police_logo.png"


def escape_xml(text: str) -> str:
    """XML 특수문자 이스케이프"""
    if not text:
        return ""
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


class ReportStorageService:
    """
    보고서 저장 서비스
    - 메모리에 JSON 저장
    - PDF 파일로 저장 (app/reports/)
    """
    
    # 메모리 저장소
    _reports: Dict[str, Dict[str, Any]] = {}
    
    # PDF 저장 경로
    PDF_SAVE_DIR = Path("app/reports")
    
    @staticmethod
    def _ensure_pdf_dir():
        """PDF 저장 디렉토리 생성"""
        ReportStorageService.PDF_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def save_report(
        report_type: str,
        case_id: str,
        title: str,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        보고서 저장
        - 메모리에 JSON 저장
        - PDF 파일로 저장 (app/reports/)
        
        Returns:
            저장된 보고서 정보 (report_id, pdf_path 포함)
        """
        report_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        
        # PDF 파일 생성
        pdf_path = ReportStorageService._save_as_pdf(
            report_id=report_id,
            report_type=report_type,
            title=title,
            content=content
        )
        
        report_data = {
            "report_id": report_id,
            "report_type": report_type,
            "case_id": case_id,
            "title": title,
            "content": content,
            "pdf_path": str(pdf_path),
            "created_at": created_at
        }
        
        # 메모리 저장
        ReportStorageService._reports[report_id] = report_data
        
        print(f"📁 보고서 저장 완료: {report_id} ({report_type})")
        print(f"📄 PDF 저장 위치: {pdf_path}")
        
        return report_data
    
    @staticmethod
    def _save_as_pdf(
        report_id: str,
        report_type: str,
        title: str,
        content: Dict[str, Any]
    ) -> Path:
        """보고서를 PDF로 저장 (경찰 공식 양식)"""
        ReportStorageService._ensure_pdf_dir()
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_{timestamp}_{report_id[:8]}.pdf"
        pdf_path = ReportStorageService.PDF_SAVE_DIR / filename
        
        # PDF 생성
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=15*mm,
            bottomMargin=20*mm
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # ========== 스타일 정의 ==========
        
        # 양식번호 (좌측 상단, 작게)
        form_style = ParagraphStyle(
            'form',
            parent=styles['Normal'],
            fontName=KOREAN_FONT,
            fontSize=9,
            alignment=TA_LEFT
        )
        
        # 소속관서 제목 (중앙, 크게)
        org_title_style = ParagraphStyle(
            'org_title',
            parent=styles['Heading1'],
            fontName=KOREAN_FONT,
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=3*mm
        )
        
        # 날짜 (우측)
        date_style = ParagraphStyle(
            'date',
            parent=styles['Normal'],
            fontName=KOREAN_FONT,
            fontSize=10,
            alignment=TA_CENTER
        )
        
        # 제목
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=KOREAN_FONT,
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # 섹션 헤더
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=KOREAN_FONT,
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15
        )
        
        # 본문
        body_style = ParagraphStyle(
            'body',
            parent=styles['Normal'],
            fontName=KOREAN_FONT,
            fontSize=10,
            leading=16,
            alignment=TA_LEFT,
            leftIndent=8*mm
        )
        
        # 용지규격 (우측 하단)
        paper_style = ParagraphStyle(
            'paper',
            parent=styles['Normal'],
            fontName=KOREAN_FONT,
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        
        # ========== 1. 양식번호 (좌측 상단) ==========
        form_numbers = {
            "INTERIM": "■ 범죄수사규칙 [별지 제156호서식]",
            "FINAL": "■ 범죄수사규칙 [별지 제174호서식]",
            "DECISION": "■ 경찰수사규칙 [별지 제114호서식]"
        }
        
        form_number = form_numbers.get(report_type, "")
        if form_number:
            story.append(Paragraph(escape_xml(form_number), form_style))
            story.append(Spacer(1, 5*mm))
        
        # ========== 2. 경찰 로고 (중앙, 25mm) ==========
        if os.path.exists(POLICE_LOGO_PATH):
            try:
                logo = Image(POLICE_LOGO_PATH, width=25*mm, height=25*mm)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 3*mm))
            except Exception as e:
                print(f"   ⚠️ 로고 로딩 실패: {e}")
        
        # ========== 3. 소속관서 제목 (중앙, 크게) ==========
        story.append(Paragraph(escape_xml("소 속 관 서"), org_title_style))
        story.append(Spacer(1, 10*mm))
        
        # ========== 4. 날짜 (중앙) ==========
        story.append(Paragraph(escape_xml(format_date()), date_style))
        story.append(Spacer(1, 5*mm))
        
        # ========== 5. 제목 ==========
        story.append(Paragraph(escape_xml(title), title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # ========== 6. 내용 ==========
        for key, value in content.items():
            # 섹션 제목
            story.append(Paragraph(escape_xml(str(key)), heading_style))
            
            # 섹션 내용
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    text = f"<b>{escape_xml(str(sub_key))}:</b> {escape_xml(str(sub_value))}"
                    story.append(Paragraph(text, body_style))
                    story.append(Spacer(1, 0.2*cm))
            else:
                # 줄바꿈 처리
                lines = str(value).split('\n')
                for line in lines:
                    if line.strip():
                        story.append(Paragraph(escape_xml(line), body_style))
                        story.append(Spacer(1, 0.1*cm))
            
            story.append(Spacer(1, 0.5*cm))
        
        # ========== 7. 용지규격 (하단 중앙) ==========
        story.append(Spacer(1, 15*mm))
        story.append(Paragraph("210㎜ × 297㎜(백상지 80g/㎡)", paper_style))
        
        # PDF 빌드
        try:
            doc.build(story)
            return pdf_path
        except Exception as e:
            print(f"   ❌ PDF 생성 실패: {e}")
            # 에러 시에도 경로 반환 (빈 파일이라도)
            return pdf_path
    
    @staticmethod
    def get_report(report_id: str) -> Optional[Dict[str, Any]]:
        """보고서 조회"""
        return ReportStorageService._reports.get(report_id)
    
    @staticmethod
    def get_all_reports() -> List[Dict[str, Any]]:
        """모든 보고서 조회"""
        return list(ReportStorageService._reports.values())
    
    @staticmethod
    def delete_report(report_id: str) -> bool:
        """보고서 삭제 (메모리 + PDF 파일)"""
        if report_id in ReportStorageService._reports:
            report = ReportStorageService._reports[report_id]
            
            # PDF 파일 삭제
            pdf_path = Path(report.get("pdf_path", ""))
            if pdf_path.exists():
                pdf_path.unlink()
                print(f"📄 PDF 파일 삭제: {pdf_path}")
            
            # 메모리에서 삭제
            del ReportStorageService._reports[report_id]
            print(f"🗑️ 보고서 삭제 완료: {report_id}")
            return True
        return False
    
    @staticmethod
    def get_reports_by_case(case_id: str) -> List[Dict[str, Any]]:
        """특정 사건의 모든 보고서 조회"""
        return [
            report for report in ReportStorageService._reports.values()
            if report.get("case_id") == case_id
        ]