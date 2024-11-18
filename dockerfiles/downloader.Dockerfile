FROM fedora:40@sha256:d0207dbb078ee261852590b9a8f1ab1f8320547be79a2f39af9f3d23db33735e AS build
# RUN apk update && apk upgrade
# RUN apk add --no-cache bash git openssh npm python3 py3-pip curl libpq-dev postgresql-client
RUN yum update -y

RUN yum install -y openssl
RUN yum install -y gcc
RUN yum install -y git
RUN yum install -y python3
RUN yum install -y python3-pip
RUN yum install -y python3-devel

RUN yum install -y nodejs
RUN npm install --global prettier
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /secdb
COPY requirements.txt /secdb/
RUN pip install -r requirements.txt
COPY ./config/config.json /secdb/config/config.json
COPY ./config/secrets.json /secdb/config/secrets.json
COPY ./secdb /secdb/secdb
COPY ./modules /secdb/modules
COPY ./scripts/downloader.sh /secdb/scripts/downloader.sh
CMD ["bash", "scripts/downloader.sh"]
