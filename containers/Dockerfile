# Use an official base image for Python 3.12
FROM python:3.12-slim

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create the /app directory
RUN mkdir -p /app/data /app/log /home/appuser/.local && \
    chown -R appuser:appuser /app /home/appuser/.local

# Update and install required packages
RUN apt-get update && apt-get install -y curl tar wget gzip sudo procps

COPY entrypoint.sh /app
RUN chmod +x /app/entrypoint.sh

# Set the working directory
WORKDIR /app

USER appuser

# Copy function code to the container
COPY ./tmp/*.py /app
COPY ./tmp/.env /app

# Install o11y agent
RUN wget https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-8.15.0-linux-x86_64.tar.gz && \
    tar xzvf elastic-agent-8.15.0-linux-x86_64.tar.gz && \
    mv elastic-agent-8.15.0-linux-x86_64 /app/elastic-agent

# Install any dependencies (if required)
COPY ./tmp/requirements.txt .
RUN pip install --user -r requirements.txt 

COPY elastic-agent.yml /app/elastic-agent

ENTRYPOINT ["/app/entrypoint.sh"]
#CMD ["/bin/sh"]