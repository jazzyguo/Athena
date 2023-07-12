from flask_socketio import SocketIO
from api import create_app


app = create_app()
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    ping_interval=5000,
    ping_timeout=10000,
    transports=['websocket', 'polling'],
)


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    socketio.run(app)


import api.routes
