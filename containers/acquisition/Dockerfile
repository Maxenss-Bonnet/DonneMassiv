FROM python:3.12-slim

LABEL org.opencontainers.image.authors="John Samuel"

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY acquisition.py /app/

USER appuser

CMD ["python3", "acquisition.py"]

