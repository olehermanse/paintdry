FROM alpine AS build
RUN apk update && apk upgrade
RUN apk add --no-cache bash git openssh npm python3 py3-pip curl libpq-dev
RUN npm install --global prettier
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /lookup
COPY requirements.txt /lookup/
RUN pip install -r requirements.txt
COPY . /lookup/

# syntax=docker/dockerfile:1
FROM python:3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /lookup
COPY requirements.txt /lookup/
RUN pip install -r requirements.txt
COPY --from=build /lookup /lookup
CMD ["python", "server.py", "0.0.0.0", "8000"]
