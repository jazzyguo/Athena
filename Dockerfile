# set base image (host OS)
FROM python:3.8

# set the working directory in the container
WORKDIR /app

# Copy the contents into the container at /app
COPY ./requirements.txt ./app.py firebaseAccountKey.json /app/
COPY ./api/ /app/api
COPY .env /app/api

# download and install dependencies
RUN apt-get -y update
RUN apt-get install -y ffmpeg wget python3 python3-pip

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# expose the port
EXPOSE 5000

# specify the entry point and command to run the WSGI server
ENTRYPOINT ["gunicorn"]
CMD ["wsgi:app", "--bind", "0.0.0.0:5000", "--workers", "4"]
