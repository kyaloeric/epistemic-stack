FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: build the demo graph (offline, no API key needed) and serve the viewer.
# Judges hit http://localhost:8000/cases/covid/out/graph.html
EXPOSE 8000
CMD ["sh", "-c", "python -m src.demo && python -m http.server 8000"]
