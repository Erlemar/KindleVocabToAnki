FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
