# Full app (scraper + API + player). The static edition for GitHub Pages does not need this.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "opencv-python-headless<5"
COPY . .
VOLUME ["/app/media"]
EXPOSE 8000
CMD ["python", "-m", "corecore", "serve", "--host", "0.0.0.0", "--port", "8000"]
