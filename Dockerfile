# CommandIA AI service
#
# The previous image was based on ai-base-env:latest (14.5 GB, CUDA + PyTorch)
# and never installed google-genai, so the container crashed with
# "ModuleNotFoundError: No module named 'google'". The service only needs the
# Python runtime and its dependencies.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Dependencies first so the layer is cached between code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non root user.
RUN useradd --create-home --shell /usr/sbin/nologin commandia \
    && chown -R commandia:commandia /app
USER commandia

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).status == 200 else 1)"

CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
