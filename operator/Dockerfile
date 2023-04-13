FROM python:3.11
LABEL org.opencontainers.image.source=https://github.com/netchecks/operator

# Configure Poetry
ENV POETRY_VERSION=1.4.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

# Install poetry separated from system interpreter
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /app

# Install dependencies
COPY poetry.lock* pyproject.toml ./
RUN poetry install --no-root

COPY . /app
RUN poetry install
CMD ["poetry", "run", "kopf", "run", "/app/netchecks_operator/main.py", "--liveness=http://0.0.0.0:8080/healthz"]
