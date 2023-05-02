from flask import Flask, request
from athena import processFile

app = Flask(__name__)

@app.route('/')
def index():
    return ''

@app.route('/process_file', methods=['POST'])
def process_file():
    uploaded_file = request.files['file']

    print(f'File uploaded - {uploaded_file}')

    # save the file to a temporary location
    uploaded_file.save('/tmp/uploaded_file')

    # call your main function on the uploaded file
    processFile('/tmp/uploaded_file')

    # return the result to the user
    return True

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
