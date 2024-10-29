# syntax=docker/dockerfile:1.7-labs
FROM node:18@sha256:ddd173cd94537e155b378342056e0968e8299eb3da9dd5d412d3b7f796ac38c0  AS build
WORKDIR /secdb/gui/
COPY ./gui/package.json /secdb/gui/package.json
COPY ./gui/package-lock.json /secdb/gui/package-lock.json
RUN npm ci
COPY --exclude=node_modules --exclude=*.md ./gui/ /secdb/gui/
RUN rm -rf /secdb/gui/dist
RUN npm run build

FROM fedora:40@sha256:d0207dbb078ee261852590b9a8f1ab1f8320547be79a2f39af9f3d23db33735e AS serve
RUN yum update -y
RUN yum install -y python3
RUN yum install -y python3-pip
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /secdb
COPY requirements.txt /secdb/
RUN pip install -r requirements.txt
COPY ./secdb /secdb/secdb
COPY --from=build /secdb/gui/dist /secdb/secdb/dist
COPY ./config.json /secdb/config.json
CMD ["python3", "secdb/server.py", "0.0.0.0", "8000"]
