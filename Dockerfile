# syntax=docker/dockerfile:1

FROM python:3.10-slim
WORKDIR /app
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD [ "uvicorn", "main:app", "--host=0.0.0.0", "--port=8082" ]
