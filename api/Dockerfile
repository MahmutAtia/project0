FROM langchain/langchain:0.1.0
RUN apt-get update && apt-get install -y cmake pkg-config && rm -rf /var/lib/apt/lists/*

RUN mkdir /api
WORKDIR /api
COPY requirements.txt /api
RUN pip install --no-cache-dir --upgrade -r /api/requirements.txt
COPY . /api


COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["entrypoint.sh"]

