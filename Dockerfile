# set base image (host OS)
FROM python:3.8

# set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# download and install dependencies
RUN apt-get -y update
RUN apt-get install -y ffmpeg wget python3 python3-pip

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# expose the port
EXPOSE 5000

VOLUME /app/clips

# command to run on container start
CMD [ "flask", "run" ]
