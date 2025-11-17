# Start from a standard Python 3.11 image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# 1. This is the fix: Manually install all of Playwright's
#    system dependencies as the ROOT user.
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgdk-pixbuf-2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    --no-install-recommends

# 2. Copy and install our Python libraries
COPY requirements.txt .
RUN pip install -r requirements.txt

# 3. Now, install just the browser (no '--with-deps' needed)
RUN playwright install chromium

# 4. Copy the rest of our app code
COPY . .

# 5. Tell Render what command to run (same as your Procfile)
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app"]