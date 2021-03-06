FROM python:3.7.1-alpine

RUN mkdir /usr/src/app
WORKDIR /usr/src/app
RUN pip install pytest-cov
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# This is is where the nextcloud package is.
WORKDIR /usr/src/app/src
