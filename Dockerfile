FROM python:3.9.1-slim AS py

WORKDIR /usr/src/app

RUN pip install beautifulsoup4
RUN pip install requests

COPY netdox/ .

CMD [ "python3", "generate.py" ]