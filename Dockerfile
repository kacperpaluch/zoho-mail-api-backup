FROM python:3.12-slim
COPY backup.py /backup.py
CMD ["python", "/backup.py"]
