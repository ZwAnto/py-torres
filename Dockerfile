FROM python:3.8.13-slim-buster

RUN apt-get update && apt-get install -y python3 python3-venv python3-dev curl poppler-utils locales

RUN sed -i 's/^# *\(fr_FR.UTF-8\)/\1/' /etc/locale.gen && locale-gen

#RUN pip install git+https://github.com/ZwAnto/py-torres.git
ADD . /app

RUN pip install /app

CMD ['uvicorn', 'pytorres.main:app', '--host', '0.0.0.0']