FROM --platform=linux/amd64 python:3.11-slim as builder


ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1
ENV \
    POETRY_VERSION=$POETRY_VERSION \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN pip install poetry

COPY . .

RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-cache

FROM builder

#CMD ["poetry", "shell"]
#CMD ["aerich", "upgrade"]
#CMD ["poetry", "exit"]