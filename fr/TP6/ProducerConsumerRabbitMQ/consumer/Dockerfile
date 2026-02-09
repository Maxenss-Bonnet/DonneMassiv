FROM python:3.10-slim
WORKDIR /app
COPY consumer.py .
RUN pip install pika
CMD ["python", "consumer.py"]
