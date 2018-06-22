FROM python:3.6.5
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y gettext
RUN mkdir /code
WORKDIR /code
ADD requirements/base.txt requirements/dev.txt /code/
RUN pip install -r base.txt -r dev.txt
ADD . /code/
WORKDIR /code