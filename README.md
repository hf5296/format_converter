# Format Converter

A self-hosted file format converter with a beautiful UI and one-click presets. Perfect for running on a Raspberry Pi.

![Format Converter](https://img.shields.io/badge/Self--Hosted-Raspberry%20Pi-red?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?style=flat-square)

## Features

- 🖼️ **Image Conversion**: PNG, JPG, HEIC, WebP, BMP, GIF, TIFF
- 📄 **Document Conversion**: DOC, DOCX → PDF
- ⚡ **One-Click Presets**: Common conversions with a single click
- 📁 **Drag & Drop**: Easy file upload
- 📦 **Batch Processing**: Convert multiple files at once
- 🎨 **Beautiful Dark UI**: Modern glassmorphism design
- 🔒 **Self-Hosted**: Your files never leave your network

## Quick Start

### Option 1: Docker (Recommended for Raspberry Pi)

```bash
# Clone or copy the project to your Pi
cd format_converter

# Build and run with Docker Compose
docker-compose up -d

# Access at http://your-pi-ip:8080
```

### Option 2: Run Locally

```bash
# Create virtual environment
cd format_converter/backend
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Access at http://localhost:8000
```

## Supported Conversions

### Images
| From | To |
|------|-----|
| HEIC/HEIF | JPG, PNG, WebP |
| PNG | JPG, WebP |
| JPG | PNG, WebP |
| WebP | JPG, PNG |
| BMP, GIF, TIFF | JPG, PNG, WebP |

### Documents
| From | To |
|------|-----|
| DOCX | PDF |
| DOC | PDF |
| ODT, RTF, TXT | PDF |

> **Note**: Document conversion requires LibreOffice. This is included in the Docker image.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/presets` | GET | Get available presets |
| `/api/formats` | GET | Get supported formats |
| `/api/convert` | POST | Convert a single file |
| `/api/batch-convert` | POST | Convert multiple files (returns ZIP) |
| `/api/health` | GET | Health check |

## Project Structure

```
format_converter/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── routes/convert.py    # API endpoints
│   │   └── services/
│   │       ├── image_converter.py
│   │       └── document_converter.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Raspberry Pi Notes

- **Image conversions** are fast and lightweight
- **Document conversions** use LibreOffice headless and may take a few seconds
- The app uses about **100-200MB RAM** during normal operation
- LibreOffice adds ~500MB to the Docker image size

## License

MIT License - Feel free to use and modify!
