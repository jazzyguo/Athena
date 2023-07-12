# Use the Heroku Python buildpack
FROM heroku/python

# Set the working directory in the container
WORKDIR /app

# Copy the contents into the container at /app
COPY . .

# Install dependencies 
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose the port
EXPOSE 5000

# Specify the entry point and command to run the WSGI server
CMD ["gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-b", "0.0.0.0:5000" "-w", "1", "app:app"]
