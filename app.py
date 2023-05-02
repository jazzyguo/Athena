from flask import Flask, request
from athena import process_video

app = Flask(__name__)


@app.route('/')
def index():
    return ''


@app.route('/process_video', methods=['POST'])
def process_file():
    uploaded_video = request.files['file']

    print(f'Video uploaded - {uploaded_video}')

    # save the file to a temporary location
    uploaded_video.save('/tmp/uploaded_file')

    # call your main function on the uploaded file
    process_video('/tmp/uploaded_file')

    # return the result to the user
    return True


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
