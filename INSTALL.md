# Installation Guide

This guide covers installing DOI2BibTex v3 with all its dependencies.

## Requirements

- Python 3.8 or higher
- pip (Python package manager)

## Basic Installation

For basic functionality without async processing:

```bash
# Clone the repository
git clone https://github.com/Ajaykhanna/DOI2BibTex
cd DOI2BibTex

# Install basic dependencies
pip install streamlit requests typing-extensions
```

## Full Installation (Recommended)

For full functionality including high-performance async processing:

```bash
# Install all dependencies
pip install streamlit requests aiohttp typing-extensions

# Or install from pyproject.toml
pip install -e .
```

## Development Installation

For development with testing and code quality tools:

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Or manually install dev dependencies
pip install pytest pytest-asyncio pytest-cov black mypy ruff
```

## Verification

Test your installation:

```bash
# Run the comprehensive test suite
python run_tests.py

# Or run just the validation
python -c "from core.config import AppConfig; print('✅ Installation successful!')"
```

## Running the Application

### Basic Streamlit App
```bash
streamlit run streamlit_app_v3.py
```

### Original Version (for comparison)
```bash
streamlit run streamlit_app.py
```

## Optional Dependencies

### Async Processing (`aiohttp`)
- **Purpose**: High-performance concurrent DOI processing
- **Speed improvement**: 5-10x faster for large batches
- **Installation**: `pip install aiohttp`

### Testing (`pytest`)
- **Purpose**: Unit testing and validation
- **Installation**: `pip install pytest pytest-asyncio`

### Code Quality (`black`, `mypy`, `ruff`)
- **Purpose**: Code formatting and type checking
- **Installation**: `pip install black mypy ruff`

## Troubleshooting

### Windows Encoding Issues
If you see Unicode errors on Windows:
```bash
# Set UTF-8 encoding
set PYTHONIOENCODING=utf-8
python run_tests.py
```

### Missing Dependencies
The application gracefully handles missing optional dependencies:
- **Without `aiohttp`**: Sync processing only (still functional)
- **Without `pytest`**: Testing not available (app works fine)

### Port Issues (Streamlit)
If port 8501 is in use:
```bash
streamlit run streamlit_app_v3.py --server.port 8502
```

## Docker Installation (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e ".[dev]"

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app_v3.py", "--server.address", "0.0.0.0"]
```

## Performance Notes

- **Batch size**: Start with 50 DOIs per batch
- **Concurrency**: Use 3-5 concurrent requests
- **Rate limiting**: Built-in exponential backoff
- **Memory**: ~10MB per 1000 DOIs processed

## Support

- **Issues**: [GitHub Issues](https://github.com/Ajaykhanna/DOI2BibTex/issues)
- **Email**: akhanna2@ucmerced.edu
- **Documentation**: See README.md for usage details
