FROM python:3.9.16 AS builder
# Ensure that the python output is sent straight to terminal

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /npdb
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

FROM python:3.9.16

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /npdb /app

ENTRYPOINT ["/bin/sh", "-c" , "python manage.py makemigrations cdb_rest && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
CMD ["/bin/bash"]
