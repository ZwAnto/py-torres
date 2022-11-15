FROM python:3.8.13-slim-buster

RUN apt-get update && apt-get install -y python3 python3-venv python3-dev curl poppler-utils locales

RUN sed -i "s/^# *\(fr_FR.UTF-8\)/\1/" /etc/locale.gen && locale-gen

ADD . /app

RUN pip install /app

CMD ["python", "-m", "uvicorn", "pytorres.main:app", "--host", "0.0.0.0"]