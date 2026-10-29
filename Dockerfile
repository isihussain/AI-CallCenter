FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OIM_HOST=0.0.0.0 OIM_PORT=8787 OIM_DB=/data/oim.db \
    OIM_SECRET=/data/.secret OIM_RECORDINGS=/recordings
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /data /recordings /tls \
    && chown app:app /data /recordings /tls
COPY oim-mvp/ oim-mvp/
COPY scripts/ scripts/
USER 10001:10001
EXPOSE 8787
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=12 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/health',timeout=2).read()"
CMD ["python", "oim-mvp/backend.py"]

