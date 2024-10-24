# syntax=docker/dockerfile:1.7-labs
FROM node:18 AS build
WORKDIR /secdb/gui/
COPY ./gui/package.json /secdb/gui/package.json
COPY ./gui/package-lock.json /secdb/gui/package-lock.json
RUN npm ci
COPY --exclude=node_modules --exclude=*.md ./gui/ /secdb/gui/
RUN rm -rf /secdb/gui/dist
RUN npm run build

FROM fedora:40 AS serve
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
