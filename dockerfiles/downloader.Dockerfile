FROM docker.io/fedora:42@sha256:b3d16134560afa00d7cc2a9e4967eb5b954512805f3fe27d8e70bbed078e22ea AS build
# RUN apk update && apk upgrade
# RUN apk add --no-cache bash git openssh npm python3 py3-pip curl libpq-dev postgresql-client
RUN yum update -y

RUN yum install -y openssl gcc git gpg
RUN yum install -y python3 python3-devel
RUN yum install -y nodejs npm
RUN npm install --global prettier
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /paintdry
COPY pyproject.toml /paintdry/
COPY ./paintdry /paintdry/paintdry
COPY ./modules /paintdry/modules
RUN uv pip install --system .
COPY ./config/*.json /paintdry/config/
COPY ./scripts/downloader.sh /paintdry/scripts/downloader.sh
CMD ["bash", "scripts/downloader.sh"]
