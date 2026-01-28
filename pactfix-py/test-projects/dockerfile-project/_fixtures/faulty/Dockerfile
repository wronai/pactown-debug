FROM ubuntu:latest

ENV PASSWORD=secret123
ENV API_KEY=abc123

ADD config.txt /app/
ADD script.sh /app/

WORKDIR app

RUN apt-get install -y curl wget

CMD python app.py

ENTRYPOINT /bin/bash start.sh
