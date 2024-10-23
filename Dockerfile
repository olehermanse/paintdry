FROM fedora:39 AS build
RUN yum update -y
RUN yum install -y python3
RUN yum install -y python3-pip
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /lookup
COPY requirements.txt /lookup/
RUN pip install -r requirements.txt
COPY ./lookup /lookup/lookup
COPY ./config.json /lookup/config.json
CMD ["python3", "lookup/server.py", "0.0.0.0", "8000"]
