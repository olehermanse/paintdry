# syntax=docker/dockerfile:1.7-labs@sha256:b99fecfe00268a8b556fad7d9c37ee25d716ae08a5d7320e6d51c4dd83246894
FROM node:18@sha256:64bf6df8b584404b4ced498ffb5440b259e8087ce76e466c3946ea3ce29acfed AS build
WORKDIR /secdb/gui/
COPY ./gui/package.json /secdb/gui/package.json
COPY ./gui/package-lock.json /secdb/gui/package-lock.json
RUN npm ci
COPY --exclude=node_modules --exclude=*.md ./gui/ /secdb/gui/
RUN rm -rf /secdb/gui/dist
RUN npm run build

FROM fedora:40@sha256:7cdd2b48396929bb8723ea2fa60e03bee39cc22e2a853cbd891587fab4eb1bc9 AS serve
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
