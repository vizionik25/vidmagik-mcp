# Use a Python base image
FROM python:3.12-slim

# Install system dependencies
# ffmpeg: required by moviepy
# imagemagick: required by moviepy for TextClip
# libsm6, libxext6, libgl1: required by opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
    uvicorn \
    ffmpeg \
    imagemagick \
    libsm6 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy to allow text/font operations
# This is often necessary in Debian/Ubuntu images for MoviePy's TextClip to work
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
    sed -i 's/domain="path" rights="none" pattern="@\*"/domain="path" rights="read|write" pattern="@\*"/g' /etc/ImageMagick-6/policy.xml; \
    fi

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
# Using uv sync to ensure we have the exact environment from uv.lock
RUN uv sync --frozen --no-cache

# Copy the rest of the application
COPY . .

# Run the server
# We use uv run to execute uvicorn in the synced virtual environment
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
