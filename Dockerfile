FROM klakegg/saxon:9.9.1-7-he-graal AS saxon
FROM node:15.8.0-buster-slim AS node

WORKDIR /usr/local
#install required node packages
RUN npm install -g xo-cli
RUN npm install -g bufferutil@4.0.3
RUN npm install -g odiff-bin@2.0.0
RUN npm install -g puppeteer@5.5.0
RUN npm install -g utf-8-validate@5.0.4

#install kubectl
RUN apt-get update && apt-get install -y apt-transport-https gnupg2 curl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update
RUN apt-get install -y kubectl

FROM python:3.9.1-slim-buster AS py

#import xslt
COPY --from=saxon /bin/xslt /bin
COPY --from=saxon /bin/saxon /bin
COPY --from=saxon /bin/xquery /bin

#import node and node modules
COPY --from=node /usr/local/bin /usr/local/bin
COPY --from=node /usr/local/lib /usr/local/lib
#also import kubectl
COPY --from=node /usr/bin/kubectl /usr/bin

#import python deps
RUN pip install beautifulsoup4
RUN pip install lxml
RUN pip install requests

#pass paths to any files in .kube with config in name
ARG _kubeconfig
ENV KUBECONFIG=${_kubeconfig}

WORKDIR /opt/app
COPY .kube /usr/.kube
COPY linktest /opt/app/linktest
WORKDIR /opt/app/linktest
#install puppeteer deps
RUN apt-get update
RUN apt-get install --no-install-recommends -y gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3\
    libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4\
    libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1\
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation\
    libappindicator1 libnss3 lsb-release xdg-utils wget libgbm-dev 
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get purge   --auto-remove && \
    apt-get clean
COPY src /opt/app/src
#copy auth details
COPY authentication.json /opt/app/src
COPY netdox /opt/app/netdox

WORKDIR /opt/app/netdox
# CMD [ "python3", "generate.py" ]
CMD [ "bash" ]