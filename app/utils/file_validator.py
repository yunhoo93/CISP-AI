# app/utils/file_validator.py (신규 파일)

from pathlib import Path
from typing import Set
from fastapi import HTTPException


class FileValidator:
    """파일 타입 검증 유틸리티"""
    
    DOCUMENT_EXTENSIONS: Set[str] = {".pdf", ".docx", ".xlsx", ".xls", ".txt", ".log", ".csv"}
    IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif"}
    VIDEO_EXTENSIONS: Set[str] = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}
    AUDIO_EXTENSIONS: Set[str] = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
    
    @staticmethod
    def validate_document(file_type: str, file_path: str):
        """문서 파일 검증"""
        extension = Path(file_path).suffix.lower()
        
        if file_type.lower() != "document":
            raise HTTPException(
                status_code=400,
                detail=f"문서 분석은 file_type이 'document'여야 합니다. 현재: '{file_type}'"
            )
        
        if extension not in FileValidator.DOCUMENT_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 문서 형식입니다. 지원 형식: {', '.join(FileValidator.DOCUMENT_EXTENSIONS)}"
            )
    
    @staticmethod
    def validate_image(file_type: str, file_path: str):
        """이미지 파일 검증"""
        extension = Path(file_path).suffix.lower()
        
        if file_type.lower() != "image":
            raise HTTPException(
                status_code=400,
                detail=f"이미지 분석은 file_type이 'image'여야 합니다. 현재: '{file_type}'"
            )
        
        if extension not in FileValidator.IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 이미지 형식입니다. 지원 형식: {', '.join(FileValidator.IMAGE_EXTENSIONS)}"
            )
    
    @staticmethod
    def validate_video(file_type: str, file_path: str):
        """비디오 파일 검증"""
        extension = Path(file_path).suffix.lower()
        
        if file_type.lower() != "video":
            raise HTTPException(
                status_code=400,
                detail=f"비디오 분석은 file_type이 'video'여야 합니다. 현재: '{file_type}'"
            )
        
        if extension not in FileValidator.VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 비디오 형식입니다. 지원 형식: {', '.join(FileValidator.VIDEO_EXTENSIONS)}"
            )
    
    @staticmethod
    def validate_audio(file_type: str, file_path: str):
        """오디오 파일 검증"""
        extension = Path(file_path).suffix.lower()
        
        if file_type.lower() != "audio":
            raise HTTPException(
                status_code=400,
                detail=f"음성 전사는 file_type이 'audio'여야 합니다. 현재: '{file_type}'"
            )
        
        if extension not in FileValidator.AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 오디오 형식입니다. 지원 형식: {', '.join(FileValidator.AUDIO_EXTENSIONS)}"
            )