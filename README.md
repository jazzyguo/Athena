docker build -t athena ./

docker run -p 5000:5000 -it -v ./clips:/app/clips athena
