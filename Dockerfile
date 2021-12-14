FROM python:3.9-alpine3.13
COPY . /ipmi2mqtt

WORKDIR /ipmi2mqtt

RUN pip3 install -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD python3 -u main.py