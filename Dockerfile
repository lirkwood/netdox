FROM python:3.9.1-slim-buster AS py

# suppress a warning from python
ENV PYTHONWARNINGS="${PYTHONWARNINGS},ignore:Unverified HTTPS request"
ENV PYTHONUNBUFFERED="true"

# set flask app
ENV FLASK_APP=/opt/app/serve.py

#install puppeteer deps and a few others
RUN apt-get update && apt-get install --no-install-recommends -y gconf-service libasound2 libatk1.0-0 libc6 \
    libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 \
    libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 \
    libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
    libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 \
    lsb-release xdg-utils wget xxd

#purge package cache
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get purge   --auto-remove && \
    apt-get clean

RUN pip install beautifulsoup4
RUN pip install lxml
RUN pip install requests
RUN pip install Pillow
RUN pip install flask
RUN pip install gunicorn
RUN pip install paramiko
RUN pip install websockets
RUN pip install boto3
RUN pip install kubernetes
RUN pip install pyppeteer
RUN pip install diffimg

RUN python3 -c 'import pyppeteer; pyppeteer.chromium_downloader.download_chromium()'

WORKDIR /opt/app

COPY netdox /opt/app

CMD [ "/bin/bash", "netdox", "start" ]