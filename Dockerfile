# Use an official Ubuntu as a parent image
FROM ubuntu:20.04

# Set environment variables to non-interactive (this prevents some prompts)
ENV DEBIAN_FRONTEND=non-interactive

# Clean
RUN apt-get clean

# Update and install wget
RUN apt-get update -y && apt-get install -y wget

# Run package updates and install packages
RUN apt-get update \
    && apt-get install -y \
        firefox \
        python3 \
        python3-pip
    
# Geckodriver version
ARG GECKODRIVER_VERSION=0.30.0

# Install Geckodriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/v$GECKODRIVER_VERSION/geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz \
    && tar -xvzf geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz


COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

WORKDIR /app
COPY . /app

# Make port 80 available to the world outside this container
EXPOSE 80

# Environment variable for the script, to know that it is running in a docker image,
# So it logs properly.
ENV DOCKER 1

CMD [ "python3", "crawler.py"]