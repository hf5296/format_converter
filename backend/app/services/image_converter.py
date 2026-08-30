"""
Image Converter Service
Handles conversion between image formats: PNG, JPG, HEIC, WebP
"""

import io
from pathlib import Path
from PIL import Image
import pillow_heif

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

# Supported conversions
SUPPORTED_INPUT_FORMATS = {'png', 'jpg', 'jpeg', 'heic', 'heif', 'webp', 'bmp', 'gif', 'tiff'}
SUPPORTED_OUTPUT_FORMATS = {'png', 'jpg', 'jpeg', 'webp'}

# Format mappings for Pillow
FORMAT_MAP = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
}


def get_output_format(format_str: str) -> str:
    """Get Pillow format string from extension."""
    return FORMAT_MAP.get(format_str.lower(), format_str.upper())


def convert_image(
    input_bytes: bytes,
    input_format: str,
    output_format: str,
    quality: int = 90
) -> bytes:
    """
    Convert an image from one format to another.
    
    Args:
        input_bytes: Raw bytes of the input image
        input_format: Input file extension (e.g., 'heic', 'png')
        output_format: Output file extension (e.g., 'jpg', 'png')
        quality: Output quality for lossy formats (1-100)
    
    Returns:
        Converted image as bytes
    """
    input_format = input_format.lower().lstrip('.')
    output_format = output_format.lower().lstrip('.')
    
    if input_format not in SUPPORTED_INPUT_FORMATS:
        raise ValueError(f"Unsupported input format: {input_format}")
    
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    # Open the image
    image = Image.open(io.BytesIO(input_bytes))
    
    # Convert RGBA to RGB if saving to JPEG (JPEG doesn't support alpha)
    if output_format in ('jpg', 'jpeg') and image.mode in ('RGBA', 'LA', 'P'):
        # Create white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    elif image.mode == 'P':
        image = image.convert('RGB')
    
    # Save to bytes
    output_buffer = io.BytesIO()
    pillow_format = get_output_format(output_format)
    
    save_kwargs = {'format': pillow_format}
    if output_format in ('jpg', 'jpeg', 'webp'):
        save_kwargs['quality'] = quality
    if output_format == 'png':
        save_kwargs['optimize'] = True
    
    image.save(output_buffer, **save_kwargs)
    output_buffer.seek(0)
    
    return output_buffer.getvalue()


def get_image_info(input_bytes: bytes) -> dict:
    """Get information about an image."""
    image = Image.open(io.BytesIO(input_bytes))
    return {
        'width': image.width,
        'height': image.height,
        'mode': image.mode,
        'format': image.format,
    }
