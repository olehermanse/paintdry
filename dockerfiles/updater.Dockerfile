FROM docker.io/fedora:42@sha256:99e203b80b1c3d8f7e161ec10a68fd02b081ef83a3963553e513c82846b97814
# RUN apk update && apk upgrade
# RUN apk add --no-cache bash git openssh npm python3 py3-pip curl libpq-dev postgresql-client
RUN yum update -y

RUN yum install -y openssl gcc
RUN yum install -y python3 python3-devel
RUN yum install -y postgresql libpq-devel
RUN yum install -y nodejs npm
RUN yum install -y skopeo
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
COPY ./scripts/updater.sh /paintdry/scripts/updater.sh
COPY ./schema.sql /paintdry/schema.sql
COPY ./config/*.json /paintdry/config/
CMD ["bash", "scripts/updater.sh"]
