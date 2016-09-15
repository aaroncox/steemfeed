FROM python:3.3.6-slim

RUN apt-get update && \
    apt-get install -y git make gcc libssl-dev libgmp-dev python-dev libxml2-dev libxslt1-dev zlib1g-dev

# Create the temp file with requirements and install
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY . /src

CMD ["python", "/src/steemfeed.py"]
