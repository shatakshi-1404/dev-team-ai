# Image used ONLY to run generated tests. Run by the backend with --network none, non-root, read-only rootfs.
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest fastapi httpx sqlalchemy pydantic pyjwt bcrypt email-validator \
    python-multipart uvicorn \
 && useradd --uid 65534 --no-create-home sandbox-unused || true
WORKDIR /workspace
