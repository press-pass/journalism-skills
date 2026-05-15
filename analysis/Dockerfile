FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl jq build-essential libxml2-dev libxslt1-dev \
    fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    polars==1.5.0 \
    duckdb==1.1.1 \
    lxml==5.2.2 \
    orjson==3.10.6 \
    plotly==5.22.0 \
    kaleido==0.2.1 \
    matplotlib==3.9.0 \
    seaborn==0.13.2 \
    altair==5.3.0 \
    vl-convert-python==1.5.0 \
    pyarrow==17.0.0 \
    fastparquet==2024.5.0 \
    rapidfuzz==3.9.4 \
    tqdm==4.66.4 \
    jinja2==3.1.4 \
    requests==2.32.3

WORKDIR /workspace
CMD ["bash"]
