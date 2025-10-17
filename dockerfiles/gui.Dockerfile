# syntax=docker/dockerfile:1.7-labs@sha256:b99fecfe00268a8b556fad7d9c37ee25d716ae08a5d7320e6d51c4dd83246894
FROM node:24.10.0@sha256:377f1c17906eb5a145c34000247faa486bece16386b77eedd5a236335025c2ef AS build
WORKDIR /secdb/gui/
COPY ./gui/package.json /secdb/gui/package.json
COPY ./gui/package-lock.json /secdb/gui/package-lock.json
RUN npm ci
COPY --exclude=node_modules --exclude=*.md ./gui/ /secdb/gui/
RUN rm -rf /secdb/gui/dist
RUN npm run build

FROM fedora:42@sha256:a3b2ef70370a9f3243883549f3a3f1733fc2665d471228c39b65d43e24e689c7 AS serve
RUN yum update -y
RUN yum install -y python3 python3-pip
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /secdb
COPY requirements.txt /secdb/
RUN pip install -r requirements.txt
COPY ./secdb /secdb/secdb
COPY --from=build /secdb/gui/dist /secdb/secdb/dist
COPY ./config/config.json /secdb/config/config.json
COPY ./config/config-override.jso[n] /secdb/config/config.json
CMD ["python3", "secdb/server.py", "0.0.0.0", "8000"]
