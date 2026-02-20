FROM docker.io/fedora:42@sha256:b3d16134560afa00d7cc2a9e4967eb5b954512805f3fe27d8e70bbed078e22ea
RUN yum update -y

RUN yum install -y openssl gcc
RUN yum install -y python3 python3-devel
RUN yum install -y postgresql libpq-devel
RUN yum install -y nodejs npm
RUN yum install -y skopeo
RUN yum install -y cargo rust
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
COPY ./updater /paintdry/updater
RUN cd /paintdry/updater && cargo build --release
COPY ./schema.sql /paintdry/schema.sql
COPY ./config/*.json /paintdry/config/
CMD ["/paintdry/updater/target/release/updater"]
