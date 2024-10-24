# syntax=docker/dockerfile:1.7-labs
FROM node:18 AS build
WORKDIR /lookup/gui/
COPY ./gui/package.json /lookup/gui/package.json
COPY ./gui/package-lock.json /lookup/gui/package-lock.json
RUN npm ci
COPY --exclude=node_modules --exclude=*.md ./gui/ /lookup/gui/
RUN rm -rf /lookup/gui/dist
RUN npm run build

FROM fedora:40 AS serve
RUN yum update -y
RUN yum install -y python3
RUN yum install -y python3-pip
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /lookup
COPY requirements.txt /lookup/
RUN pip install -r requirements.txt
COPY ./lookup /lookup/lookup
COPY --from=build /lookup/gui/dist /lookup/lookup/dist
COPY ./config.json /lookup/config.json
CMD ["python3", "lookup/server.py", "0.0.0.0", "8000"]
