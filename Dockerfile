# 1. Use Python 3.12 Slim (Standard for 2026 production apps)
FROM python:3.12-slim

# 2. Set working directory
WORKDIR /app

# 3. Install build tools needed for technical analysis libraries
# We combine these to keep the image size small
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements and install
# Upgrading pip first prevents most "No matching distribution" errors
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy your bot's Python code
COPY . .

# 6. Start the engine
CMD ["python", "main_bot.py"]

# Tell the Python code we are in Docker
ENV AM_I_IN_DOCKER=true