"""
Document Converter Service
Handles conversion of DOC/DOCX to PDF using LibreOffice headless
"""

import asyncio
import subprocess
import tempfile
import shutil
from pathlib import Path

# Supported conversions
SUPPORTED_INPUT_FORMATS = {'doc', 'docx', 'odt', 'rtf', 'txt'}
SUPPORTED_OUTPUT_FORMATS = {'pdf'}


def check_libreoffice_available() -> bool:
    """Check if LibreOffice is available on the system."""
    # Try different possible LibreOffice command names
    for cmd in ['soffice', 'libreoffice', '/usr/bin/soffice', '/usr/bin/libreoffice']:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return False


def get_libreoffice_command() -> str:
    """Get the LibreOffice command available on the system."""
    for cmd in ['soffice', 'libreoffice', '/usr/bin/soffice', '/usr/bin/libreoffice']:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return cmd
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    raise RuntimeError("LibreOffice not found. Please install LibreOffice for document conversion.")


async def convert_document(
    input_bytes: bytes,
    input_format: str,
    output_format: str = 'pdf'
) -> bytes:
    """
    Convert a document from one format to another using LibreOffice.
    
    Args:
        input_bytes: Raw bytes of the input document
        input_format: Input file extension (e.g., 'docx', 'doc')
        output_format: Output file extension (currently only 'pdf' supported)
    
    Returns:
        Converted document as bytes
    """
    input_format = input_format.lower().lstrip('.')
    output_format = output_format.lower().lstrip('.')
    
    if input_format not in SUPPORTED_INPUT_FORMATS:
        raise ValueError(f"Unsupported input format: {input_format}")
    
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    # Create temporary directory for conversion
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write input file
        input_file = temp_path / f"input.{input_format}"
        input_file.write_bytes(input_bytes)
        
        # Get LibreOffice command
        lo_cmd = get_libreoffice_command()
        
        # Run LibreOffice conversion
        cmd = [
            lo_cmd,
            '--headless',
            '--convert-to', output_format,
            '--outdir', str(temp_path),
            str(input_file)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"LibreOffice conversion failed: {error_msg}")
        
        # Read output file
        output_file = temp_path / f"input.{output_format}"
        
        if not output_file.exists():
            raise RuntimeError("Conversion failed: output file not created")
        
        return output_file.read_bytes()


def convert_document_sync(
    input_bytes: bytes,
    input_format: str,
    output_format: str = 'pdf'
) -> bytes:
    """Synchronous version of convert_document for non-async contexts."""
    return asyncio.run(convert_document(input_bytes, input_format, output_format))
