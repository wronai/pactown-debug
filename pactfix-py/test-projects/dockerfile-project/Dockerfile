FROM ubuntu:latest

ENV PASSWORD=secret123
ENV API_KEY=abc123

# pactfix: Zamieniono ADD na COPY (was: ADD config.txt /app/)
COPY config.txt /app/
# pactfix: Zamieniono ADD na COPY (was: ADD script.sh /app/)
COPY script.sh /app/

# pactfix: Dodano / do WORKDIR (was: WORKDIR app)
WORKDIR /app

RUN apt-get install -y curl wget

CMD python app.py

ENTRYPOINT /bin/bash start.sh
