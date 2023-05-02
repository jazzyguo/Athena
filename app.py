from flask import Flask, request, abort
from athena import process_video

app = Flask(__name__)


@app.route('/')
def index():
    return ''


@app.route('/process_video', methods=['POST'])
def process_file():
    uploaded_video = request.files['file']

    if uploaded_video is None:
        abort(400, 'Required video file is missing')

    print(f'Video uploaded - {uploaded_video}')

    uploaded_video.save('/tmp/uploaded_file')

    try:
        process_video('/tmp/uploaded_file')
    except ValueError as e:
        abort(400, str(e))

    return True


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
