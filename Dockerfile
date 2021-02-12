FROM python:3.9.1-slim

RUN pip install beautifulsoup4
RUN pip install requests

RUN apt-get update && apt-get install -y apt-transport-https gnupg2 curl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update
RUN apt-get install -y kubectl

ENV KUBECONFIG=/usr/.kube/config

RUN apt-get install -y jq

WORKDIR /opt/app
COPY .kube /usr/.kube
COPY linktest /opt/app/linktest
COPY src /opt/app/src
COPY authentication.json /opt/app/src
COPY netdox /opt/app/netdox

WORKDIR /opt/app/netdox
CMD [ "python3", "generate.py" ]