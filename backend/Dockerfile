# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e

FROM ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 AS uv

FROM python:3.14-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

# ARG y no ENV: solo se necesita durante el build y no debe persistir en la imagen.
ARG DEBIAN_FRONTEND=noninteractive

# Bibliotecas nativas que requiere GeoDjango.
RUN apt-get update && apt-get install -y --no-install-recommends \
      binutils \
      gdal-bin \
      libproj-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv

# El venv vive fuera de /app porque el bind mount ./backend:/app de Compose lo ocultaría.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/opt/venv/bin:$PATH

# UID/GID explícitos: deterministas entre reconstrucciones.
RUN groupadd --gid 1000 app \
    && useradd --no-log-init --uid 1000 --gid 1000 --create-home app

WORKDIR /app

# Dependencias antes que el código: editar el código no invalida la capa de uv sync.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Sin --chown: código y venv quedan de root y son de solo lectura para el usuario app.
COPY . .

USER 1000:1000
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
