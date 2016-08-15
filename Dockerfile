FROM python:3.3.6-slim

RUN apt-get update && \
    apt-get install -y git make gcc libssl-dev libgmp-dev python-dev libxml2-dev libxslt1-dev zlib1g-dev

RUN pip3 install steem-piston scrypt python-dateutil

COPY . /src

CMD ["python", "/src/steemfeed.py"]
