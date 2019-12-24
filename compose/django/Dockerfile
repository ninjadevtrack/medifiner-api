FROM python:3.6.5
ENV PYTHONUNBUFFERED=1

ENV GDAL_VERSION=2.2.1

RUN apt-get update && apt-get install -y \
	gettext \
	build-essential \
	binutils \
	libproj-dev \
	libgdal-dev \
	gdal-bin

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN mkdir /code
WORKDIR /code
ADD requirements/base.txt requirements/dev.txt /code/
RUN pip install --upgrade pip
RUN pip install -r dev.txt
ADD . /code/
WORKDIR /code

CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT medfinder.wsgi:application --workers 2 --timeout 9000
