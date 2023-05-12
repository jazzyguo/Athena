from flask import Flask
from flask_cors import CORS
from controllers.file_processing import process_file
from controllers.twitch_vod_processing import twitch_vod_processing

app = Flask(__name__)

CORS(app)


@app.route('/')
def index():
    return ''


@app.route('/process_file', methods=['POST'])
def process_file_route():
    return process_file()


@app.route('/twitch/process_vod/<vod_id>', methods=['POST'])
def twitch_vod_processing_route(vod_id):
    return twitch_vod_processing(vod_id)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
