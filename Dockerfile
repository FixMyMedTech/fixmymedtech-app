# Bootstrap image: Python + Docker CLI + project pip requirements
# Build on the ARM server:  docker build --platform linux/arm64 -t fixmymedtech-bootstrap .
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://get.docker.com | sh

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash"]
