FROM python:3.11.6-slim-bullseye as builder

ENV TZ=Europe/Moscow \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

RUN apt-get update && apt-get install --no-install-recommends -y build-essential && \
    pip config --user set global.index https://repository.svrauto.ru/repository/pypi-group/simple && \
    pip config --user set global.index-url https://repository.svrauto.ru/repository/pypi-group/simple && \
    pip config --user set global.trusted-host svrauto.ru && \
    pip install 'poetry==1.6.1' && \
    poetry config repositories.svrauto-nats https://git.svrauto.ru/api/v4/projects/106/packages/pypi/simple && \
    poetry config http-basic.svrauto-nats __token__ xiS6pSaERssHcZ_smqLz && \
    poetry config repositories.svrauto-logger https://git.svrauto.ru/api/v4/projects/121/packages/pypi/simple && \
    poetry config http-basic.svrauto-logger __token__ xiS6pSaERssHcZ_smqLz && \
    poetry config repositories.svrauto-gatewaypool https://git.svrauto.ru/api/v4/projects/199/packages/pypi/simple && \
    poetry config http-basic.svrauto-gatewaypool __token__ xiS6pSaERssHcZ_smqLz && \
    poetry install --only main --no-root --compile && rm -rf $POETRY_CACHE_DIR

FROM python:3.11.6-slim-bullseye as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY . .

ENTRYPOINT [ "python", "main.py" ]
