FROM python:3.9.1-slim AS py

WORKDIR /usr/src/app
COPY netdox-src/ .

RUN pip install beautifulsoup4
RUN pip install requests

CMD [ "python3", "generate.py" ]