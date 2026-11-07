# Satura on fe-pro (see deploy/docker-compose.yml and fe-pro's SERVER.md).
# Code and Python's files stay root-owned; the container runs as satura (2007, set in the compose file)
# and can write only /data.
FROM python:3.12.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY config.py wsgi.py ./
COPY app ./app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"
# ONE worker process with threads: live game sessions are held in process memory (app/game/session.py), so with
# several processes each one had its own copy of a game and players saw it flip between states. Threads share the
# one copy, as under Flask's threaded dev server. Don't raise --workers without moving that state out of process.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--worker-class", "gthread", "--threads", "8", "--worker-tmp-dir", "/tmp", "--no-control-socket", \
     "--forwarded-allow-ips", "172.31.70.20", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
