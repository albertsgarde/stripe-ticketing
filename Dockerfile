FROM python:3.11-slim as compiler
ENV PYTHONUNBUFFERED=1

RUN python -m venv .env
ENV PATH="/.env/bin:$PATH"

COPY ./requirements.txt requirements.txt
RUN pip install -Ur requirements.txt


FROM python:3.11-slim as runner
ENV PYTHONUNBUFFERED=1
COPY --from=compiler .env .env

ENV PATH="/.env/bin:$PATH"

COPY server.py server.py

EXPOSE $PORT
CMD uvicorn server:app --host 0.0.0.0 --port $PORT
