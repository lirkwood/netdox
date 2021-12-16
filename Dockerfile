FROM python:3.9.8-slim-bullseye AS build

COPY . /opt/netdox
WORKDIR /opt/netdox
RUN python3 setup.py bdist_wheel

FROM python:3.9.8-slim-bullseye

RUN pip install pyppeteer && pyppeteer-install && \
    apt update && apt install -y gconf-service libxext6 \
    libxi6 libxrandr2 libxrender1 libcairo2 libcups2 \
    libdbus-1-3 libexpat1 libfontconfig1 libgcc1 \
    libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 \
    libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 \
    libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
    libxcursor1 libxdamage1 libxss1 libxtst6 \
    libnss3 libasound2 libatk1.0-0 libc6 ca-certificates \
    libxfixes3 fonts-liberation lsb-release xdg-utils wget

COPY scripts/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

RUN mkdir /opt/wheels
COPY --from=build /opt/netdox/dist/*.whl /opt/wheels/
RUN for file in /opt/wheels/*.whl; do pip install $file; done

CMD [ "/opt/entrypoint.sh" ]