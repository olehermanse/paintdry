# syntax=docker/dockerfile:1.7-labs@sha256:b99fecfe00268a8b556fad7d9c37ee25d716ae08a5d7320e6d51c4dd83246894
FROM docker.io/node:24.16.0-alpine3.23@sha256:2bdb65ed1dab192432bc31c95f94155ca5ad7fc1392fb7eb7526ab682fa5bf14 AS build
WORKDIR /paintdry/gui/
COPY ./gui/package.json /paintdry/gui/package.json
COPY ./gui/package-lock.json /paintdry/gui/package-lock.json
RUN npm ci
COPY ./gui/ /paintdry/gui/
RUN rm -rf /paintdry/gui/dist
RUN rm /paintdry/gui/README.md
RUN npm run build

FROM docker.io/fedora:42@sha256:99e203b80b1c3d8f7e161ec10a68fd02b081ef83a3963553e513c82846b97814 AS serve
RUN yum update -y
RUN yum install -y python3
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /paintdry
COPY pyproject.toml /paintdry/
COPY ./paintdry /paintdry/paintdry
RUN uv pip install --system .
COPY --from=build /paintdry/gui/dist /paintdry/paintdry/dist
COPY ./config/*.json /paintdry/config/
CMD ["python3", "paintdry/server.py", "0.0.0.0", "8000"]
