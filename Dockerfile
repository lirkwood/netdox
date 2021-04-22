FROM node:15.8.0-buster-slim AS node

WORKDIR /opt/app
# install required node packages
RUN npm install -g xo-cli
RUN npm install bufferutil@4.0.3
RUN npm install img-diff-js@0.5.2
RUN npm install puppeteer@5.5.0
RUN npm install utf-8-validate@5.0.4

# install kubectl
RUN apt-get update && apt-get install -y apt-transport-https gnupg2 curl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update
RUN apt-get install -y kubectl

# Timezone info
RUN apt-get install -y tzdata


###################################
FROM python:3.9.1-slim-buster AS py

# suppress a warning from python
ENV PYTHONWARNINGS="${PYTHONWARNINGS},ignore:Unverified HTTPS request"
ENV PYTHONUNBUFFERED="true"

# set env vars for ant
ENV ANT_HOME=/opt/ant/apache-ant-1.10.9
ENV PATH=${PATH}:${ANT_HOME}/bin

# set kubeconfig path
ENV KUBECONFIG=/opt/app/src/kubeconfig

# set aws-cli config
ENV AWS_CONFIG_FILE=/opt/app/src/awsconfig

# set tz
ENV TZ="Australia/Sydney"

# make dir for man page to stop jre postinstall script failing
RUN mkdir -p /usr/share/man/man1
RUN apt-get update &&  apt-get install -y --no-install-recommends curl unzip openjdk-11-jre-headless

WORKDIR /opt/ant
# download and decompress ant 1.10.9
RUN curl https://apache.mirror.digitalpacific.com.au//ant/binaries/apache-ant-1.10.9-bin.tar.gz \
-o /opt/ant/apache-ant-1.10.9-bin.tar.gz && gzip -d /opt/ant/apache-ant-1.10.9-bin.tar.gz && \ 
tar -xf /opt/ant/apache-ant-1.10.9-bin.tar && rm -f /opt/ant/apache-ant-1.10.9-bin.tar

WORKDIR /opt/ant/lib
# download pageseeder jar files
RUN curl http://download.pageseeder.com/pub/win/5.9811/pageseeder-publish-api-5.9811.jar \
-o /opt/ant/lib/pageseeder-publish-api-5.9811.jar && \
curl -L http://dl.bintray.com/pageseeder/maven/org/pageseeder/pso-psml/0.6.9/pso-psml-0.6.9.jar \
-o /opt/ant/lib/pso-psml-0.6.9.jar && \
curl -L http://dl.bintray.com/pageseeder/maven/org/pageseeder/xmlwriter/pso-xmlwriter/1.0.2/pso-xmlwriter-1.0.2.jar \
-o /opt/ant/lib/pso-xmlwriter-1.0.2.jar && \
curl -L https://bintray.com/bintray/jcenter/download_file?file_path=org%2Fslf4j%2Fslf4j-api%2F1.7.12%2Fslf4j-api-1.7.12.jar \
-o /opt/ant/lib/slf4j-api-1.7.12.jar && \
curl -L https://bintray.com/bintray/jcenter/download_file?file_path=org%2Fslf4j%2Fslf4j-simple%2F1.7.12%2Fslf4j-simple-1.7.12.jar \
-o /opt/ant/lib/slf4j-simple-1.7.12.jar

WORKDIR /usr/local/bin

# download saxon
RUN curl -L https://sourceforge.net/projects/saxon/files/Saxon-HE/10/Java/SaxonHE10-3J.zip/download \
-o /usr/local/bin/saxon.zip && unzip /usr/local/bin/saxon.zip

# import node and global node modules
COPY --from=node /usr/local/bin /usr/local/bin
COPY --from=node /usr/local/lib /usr/local/lib
# import kubectl
COPY --from=node /usr/bin/kubectl /usr/bin
# import tz
COPY --from=node /usr/share/zoneinfo/${TZ} /etc/localtime
RUN echo "$TZ" > /etc/timezone

# install any packages available through python-pip
RUN pip install beautifulsoup4
RUN pip install lxml
RUN pip install requests
RUN pip install Pillow
RUN pip install awscli
RUN pip install flask
RUN pip install gunicorn

WORKDIR /opt/app

#install puppeteer deps and a few others
RUN apt-get install --no-install-recommends -y gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3\
    libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4\
    libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1\
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation\
    libappindicator1 libnss3 lsb-release xdg-utils wget libgbm-dev zip jq iputils-ping openssl xxd

#purge package cache
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get purge   --auto-remove && \
    apt-get clean

#copy main files and node deps
COPY --from=node /opt/app/node_modules /opt/app/node_modules
COPY netdox /opt/app

ENV FLASK_APP=/opt/app/serve.py

CMD [ "gunicorn", "--reload", "-b", "0.0.0.0:8080", "serve:app" ]