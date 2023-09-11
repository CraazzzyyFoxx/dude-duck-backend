FROM python:3.11-slim-buster

RUN pip install poetry

COPY . .

RUN poetry config virtualenvs.create false
RUN poetry install --only main

