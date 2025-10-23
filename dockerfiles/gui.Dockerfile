# syntax=docker/dockerfile:1.7-labs@sha256:b99fecfe00268a8b556fad7d9c37ee25d716ae08a5d7320e6d51c4dd83246894
FROM docker.io/node:24.10.0@sha256:377f1c17906eb5a145c34000247faa486bece16386b77eedd5a236335025c2ef AS build
WORKDIR /paintdry/gui/
COPY ./gui/package.json /paintdry/gui/package.json
COPY ./gui/package-lock.json /paintdry/gui/package-lock.json
RUN npm ci
COPY ./gui/ /paintdry/gui/
RUN rm -rf /paintdry/gui/dist
RUN rm /paintdry/gui/README.md
RUN npm run build

FROM docker.io/fedora:42@sha256:a3b2ef70370a9f3243883549f3a3f1733fc2665d471228c39b65d43e24e689c7 AS serve
RUN yum update -y
RUN yum install -y python3 python3-pip
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /paintdry
COPY requirements.txt /paintdry/
RUN pip install -r requirements.txt
COPY ./paintdry /paintdry/paintdry
COPY --from=build /paintdry/gui/dist /paintdry/paintdry/dist
COPY ./config/*.json /paintdry/config/
CMD ["python3", "paintdry/server.py", "0.0.0.0", "8000"]
