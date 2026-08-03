FROM golang:1.25-bookworm AS nuclei-builder
RUN go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

FROM python:3.11-slim

COPY --from=nuclei-builder /go/bin/nuclei /usr/local/bin/nuclei

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    sqlmap \
    ffuf \
    dirb \
    libcap2-bin \
    build-essential \
    git \
    rustc \
    cargo \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && mkdir -p /usr/share/wordlists \
    && ln -s /usr/share/dirb/wordlists /usr/share/wordlists/dirb \
    && setcap cap_net_raw,cap_net_admin+eip /usr/bin/nmap \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r wraithlink && useradd -r -g wraithlink -d /app -s /usr/sbin/nologin wraithlink

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/evidence && chown -R wraithlink:wraithlink /app /data/evidence

USER wraithlink

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
