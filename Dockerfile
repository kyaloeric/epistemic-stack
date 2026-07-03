FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Serve the interrogable web app over the pre-built case data (no API key needed).
# Judges hit http://localhost:8000
EXPOSE 8000
CMD ["sh", "-c", "python web/build_data.py && python server.py"]
