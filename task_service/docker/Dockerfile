FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

COPY . .

RUN pip install -r requirements.txt

CMD ["uvicorn", "task_service.main:app", "--host", "0.0.0.0", "--port", "8001"]

EXPOSE 8001