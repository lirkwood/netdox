FROM python:3.9.1
WORKDIR /usr/src/app
COPY netdox-src/ .
RUN pip install beautifulsoup4
RUN pip install requests
CMD ["python", "generate.py"]