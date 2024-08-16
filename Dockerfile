# Use an official base image for Python 3.12
FROM python:3.12-slim

# Update and install required packages
RUN apt-get update && apt-get install -y curl tar wget gzip sudo supervisor procps

# Create the /app directory
RUN mkdir -p /app
RUN mkdir -p /app/data

# Copy function code to the container
COPY *.py /app
COPY .env /app

# Install any dependencies (if required)
COPY requirements.txt .
RUN pip install -r requirements.txt 

# Install o11y agent
RUN wget https://artifacts.elastic.co/downloads/beats/elastic-agent/elastic-agent-8.15.0-linux-x86_64.tar.gz && \
    tar xzvf elastic-agent-8.15.0-linux-x86_64.tar.gz && \
    mv elastic-agent-8.15.0-linux-x86_64 /opt/elastic-agent

# Copy the supervisord configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY elastic-agent.yml /opt/elastic-agent

# Set the command to run supervisord
ENTRYPOINT ["/usr/bin/supervisord"]
#CMD ["/bin/sh && cd /var/log"]