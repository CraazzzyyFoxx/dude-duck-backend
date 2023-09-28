FROM python:3.11-slim-bullseye

RUN pip install poetry

COPY . .

RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-cache

