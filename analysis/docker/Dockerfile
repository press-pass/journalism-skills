FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DUCKDB_NO_PROMPT=1

WORKDIR /work

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxml2-dev libxslt1-dev \
    build-essential \
    git \
    fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD ["bash"]
