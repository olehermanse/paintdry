FROM fedora:40@sha256:7cdd2b48396929bb8723ea2fa60e03bee39cc22e2a853cbd891587fab4eb1bc9 AS build
# RUN apk update && apk upgrade
# RUN apk add --no-cache bash git openssh npm python3 py3-pip curl libpq-dev postgresql-client
RUN yum update -y

RUN yum install -y openssl gcc
RUN yum install -y python3 python3-pip python3-devel
RUN yum install -y postgresql libpq-devel
RUN yum install -y nodejs npm
RUN npm install --global prettier
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /secdb
COPY requirements.txt /secdb/
RUN pip install -r requirements.txt
COPY ./scripts/updater.sh /secdb/scripts/updater.sh
COPY ./schema.sql /secdb/schema.sql
COPY ./config/config.json /secdb/config/config.json
COPY ./secdb /secdb/secdb
COPY ./modules /secdb/modules
CMD ["bash", "scripts/updater.sh"]
