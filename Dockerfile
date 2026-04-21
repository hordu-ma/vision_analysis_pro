FROM python:3.12-slim

ARG UV_DEFAULT_INDEX=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX} \
    PATH="/app/.venv/bin:/root/.local/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

ARG INSTALL_ONNX=false
RUN if [ "$INSTALL_ONNX" = "true" ]; then \
        uv sync --frozen --extra onnx; \
    else \
        uv sync --frozen; \
    fi

COPY config ./config
COPY scripts ./scripts
COPY examples ./examples
COPY tests ./tests
COPY ruff.toml pytest.ini ./

EXPOSE 8000

ENV API_HOST=0.0.0.0 \
    API_PORT=8000 \
    INFERENCE_ENGINE=stub \
    YOLO_MODEL_PATH=/app/runs/stage_a_crack/baseline_v0_1/weights/best.pt \
    ONNX_MODEL_PATH=/app/models/stage_a_crack/best.onnx

RUN mkdir -p /app/models /app/data /app/runs

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["sh", "-c", "uv run uvicorn vision_analysis_pro.web.api.main:app --host 0.0.0.0 --port 8000"]
