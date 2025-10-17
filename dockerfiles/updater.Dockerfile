FROM fedora:42@sha256:a3b2ef70370a9f3243883549f3a3f1733fc2665d471228c39b65d43e24e689c7
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
WORKDIR /paintdry
COPY requirements.txt /paintdry/
RUN pip install -r requirements.txt
COPY ./scripts/updater.sh /paintdry/scripts/updater.sh
COPY ./schema.sql /paintdry/schema.sql
COPY ./config/config.json /paintdry/config/config.json
COPY ./config/config-override.jso[n] /paintdry/config/config.json
COPY ./paintdry /paintdry/paintdry
COPY ./modules /paintdry/modules
CMD ["bash", "scripts/updater.sh"]
