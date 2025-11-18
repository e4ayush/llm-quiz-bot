# Start from a standard Python 3.11 image
FROM python:3.11-slim

# Force Python logs to be unbuffered
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy and install our Python libraries
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- THIS IS THE NEW FIX ---
# Instead of a manual list of libraries,
# we let Playwright's tool install *all* its own
# system dependencies AND the browser.
# This works because we are 'root' inside the Dockerfile.
RUN playwright install --with-deps chromium
# --- END OF FIX ---

# Copy the rest of our app code
COPY . .

# Tell Render what command to run
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app"]