FROM python:3.11-slim
LABEL org.opencontainers.image.source=https://github.com/netchecks/netchecks

# Configure Poetry
ENV POETRY_VERSION=1.4.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VENV=/opt/poetry-venv \
    POETRY_CACHE_DIR=/opt/.cache

# Install poetry separated from system interpreter
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools --no-cache-dir \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION} --no-cache-dir

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /app

# Install dependencies
COPY poetry.lock* pyproject.toml README.md ./
RUN poetry install --no-root --no-cache

COPY ./netcheck/ /app/netcheck/
RUN poetry install
ENTRYPOINT ["poetry", "run", "netcheck"]
CMD ["http", "-v"]
