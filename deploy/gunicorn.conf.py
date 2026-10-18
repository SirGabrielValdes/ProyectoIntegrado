# Configuración de gunicorn para la instancia EC2 (ver docs/despliegue_aws.md).
import multiprocessing
import os

bind = "127.0.0.1:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
timeout = 60
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = "info"
