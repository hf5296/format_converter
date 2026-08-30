"""
Conversion API Routes
Handles file upload, conversion, and download endpoints
With rate limiting and file limits
"""

import os
import uuid
import zipfile
import io
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import Response, StreamingResponse

from ..services.image_converter import (
    convert_image,
    SUPPORTED_INPUT_FORMATS as IMAGE_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS as IMAGE_OUTPUT_FORMATS
)
from ..services.document_converter import (
    convert_document,
    check_libreoffice_available,
    SUPPORTED_INPUT_FORMATS as DOC_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS as DOC_OUTPUT_FORMATS
)
from ..services.rate_limiter import (
    rate_limiter,
    MAX_FILES_PER_REQUEST,
    MAX_CONVERSIONS_PER_DAY
)

router = APIRouter(prefix="/api", tags=["convert"])

# Temporary storage for converted files
TEMP_DIR = Path("/tmp/format_converter")
TEMP_DIR.mkdir(exist_ok=True)

# File expiry time (files older than this will be cleaned up)
FILE_EXPIRY_HOURS = 1

# Conversion presets
PRESETS = [
    {"id": "heic-to-jpg", "name": "HEIC → JPG", "from": "heic", "to": "jpg", "icon": "📷", "category": "image"},
    {"id": "heic-to-png", "name": "HEIC → PNG", "from": "heic", "to": "png", "icon": "📷", "category": "image"},
    {"id": "png-to-jpg", "name": "PNG → JPG", "from": "png", "to": "jpg", "icon": "🖼️", "category": "image"},
    {"id": "jpg-to-png", "name": "JPG → PNG", "from": "jpg", "to": "png", "icon": "🖼️", "category": "image"},
    {"id": "webp-to-jpg", "name": "WebP → JPG", "from": "webp", "to": "jpg", "icon": "🌐", "category": "image"},
    {"id": "webp-to-png", "name": "WebP → PNG", "from": "webp", "to": "png", "icon": "🌐", "category": "image"},
    {"id": "png-to-webp", "name": "PNG → WebP", "from": "png", "to": "webp", "icon": "🌐", "category": "image"},
    {"id": "jpg-to-webp", "name": "JPG → WebP", "from": "jpg", "to": "webp", "icon": "🌐", "category": "image"},
    {"id": "docx-to-pdf", "name": "DOCX → PDF", "from": "docx", "to": "pdf", "icon": "📄", "category": "document"},
    {"id": "doc-to-pdf", "name": "DOC → PDF", "from": "doc", "to": "pdf", "icon": "📄", "category": "document"},
]


def get_client_ip(request: Request) -> str:
    """Get the real client IP, handling proxies."""
    # Check for forwarded headers (common with reverse proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


def cleanup_old_files():
    """Remove files older than FILE_EXPIRY_HOURS."""
    if not TEMP_DIR.exists():
        return
    
    expiry_time = datetime.now() - timedelta(hours=FILE_EXPIRY_HOURS)
    
    for file_path in TEMP_DIR.iterdir():
        if file_path.is_file():
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < expiry_time:
                file_path.unlink()
    
    # Also cleanup stale rate limiter entries
    rate_limiter.cleanup_old_entries()


@router.get("/presets")
async def get_presets():
    """Get available conversion presets."""
    available_presets = []
    libreoffice_available = check_libreoffice_available()
    
    for preset in PRESETS:
        if preset["category"] == "document" and not libreoffice_available:
            preset_copy = preset.copy()
            preset_copy["available"] = False
            preset_copy["reason"] = "LibreOffice not installed"
            available_presets.append(preset_copy)
        else:
            preset_copy = preset.copy()
            preset_copy["available"] = True
            available_presets.append(preset_copy)
    
    return {"presets": available_presets}


@router.get("/formats")
async def get_formats():
    """Get supported input and output formats."""
    return {
        "image": {
            "input": list(IMAGE_INPUT_FORMATS),
            "output": list(IMAGE_OUTPUT_FORMATS)
        },
        "document": {
            "input": list(DOC_INPUT_FORMATS),
            "output": list(DOC_OUTPUT_FORMATS),
            "available": check_libreoffice_available()
        }
    }


@router.get("/limits")
async def get_limits(request: Request):
    """Get current usage limits for the client."""
    client_ip = get_client_ip(request)
    remaining = rate_limiter.get_remaining(client_ip)
    
    return {
        "max_files_per_request": MAX_FILES_PER_REQUEST,
        "max_conversions_per_day": MAX_CONVERSIONS_PER_DAY,
        "remaining_today": remaining
    }


@router.post("/convert")
async def convert_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    output_format: str = Form(...),
    quality: int = Form(100)
):
    """
    Convert a single file to the specified format.
    Returns the converted file directly.
    """
    background_tasks.add_task(cleanup_old_files)
    
    # Rate limiting
    client_ip = get_client_ip(request)
    allowed, message = rate_limiter.check_limit(client_ip, 1)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    input_format = Path(file.filename).suffix.lower().lstrip('.')
    output_format = output_format.lower().lstrip('.')
    
    content = await file.read()
    
    # Convert
    if input_format in IMAGE_INPUT_FORMATS and output_format in IMAGE_OUTPUT_FORMATS:
        try:
            converted = convert_image(content, input_format, output_format, quality)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image conversion failed: {str(e)}")
    
    elif input_format in DOC_INPUT_FORMATS and output_format in DOC_OUTPUT_FORMATS:
        if not check_libreoffice_available():
            raise HTTPException(
                status_code=503,
                detail="Document conversion requires LibreOffice, which is not installed"
            )
        try:
            converted = await convert_document(content, input_format, output_format)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Document conversion failed: {str(e)}")
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported conversion: {input_format} → {output_format}"
        )
    
    # Record usage AFTER successful conversion
    rate_limiter.record_usage(client_ip, 1)
    
    original_name = Path(file.filename).stem
    output_filename = f"{original_name}.{output_format}"
    
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'pdf': 'application/pdf'
    }
    content_type = content_types.get(output_format, 'application/octet-stream')
    
    return Response(
        content=converted,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"',
            "X-Remaining-Conversions": str(rate_limiter.get_remaining(client_ip))
        }
    )


@router.post("/batch-convert")
async def batch_convert(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    output_format: str = Form(...),
    quality: int = Form(100)
):
    """
    Convert multiple files to the specified format.
    Returns a ZIP file containing all converted files.
    """
    background_tasks.add_task(cleanup_old_files)
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Rate limiting
    client_ip = get_client_ip(request)
    file_count = len(files)
    
    allowed, message = rate_limiter.check_limit(client_ip, file_count)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)
    
    output_format = output_format.lower().lstrip('.')
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    converted_count = 0
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            if not file.filename:
                continue
            
            input_format = Path(file.filename).suffix.lower().lstrip('.')
            content = await file.read()
            
            try:
                if input_format in IMAGE_INPUT_FORMATS and output_format in IMAGE_OUTPUT_FORMATS:
                    converted = convert_image(content, input_format, output_format, quality)
                elif input_format in DOC_INPUT_FORMATS and output_format in DOC_OUTPUT_FORMATS:
                    if not check_libreoffice_available():
                        continue
                    converted = await convert_document(content, input_format, output_format)
                else:
                    continue
                
                original_name = Path(file.filename).stem
                output_filename = f"{original_name}.{output_format}"
                zip_file.writestr(output_filename, converted)
                converted_count += 1
                
            except Exception:
                continue
    
    if converted_count == 0:
        raise HTTPException(status_code=400, detail="No files could be converted")
    
    # Record usage for successful conversions only
    rate_limiter.record_usage(client_ip, converted_count)
    
    zip_buffer.seek(0)
    zip_filename = f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
            "X-Converted-Count": str(converted_count),
            "X-Remaining-Conversions": str(rate_limiter.get_remaining(client_ip))
        }
    )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "libreoffice_available": check_libreoffice_available()
    }
