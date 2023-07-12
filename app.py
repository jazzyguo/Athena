from flask_socketio import SocketIO
from api import create_app
from gevent import monkey
import grpc.experimental.gevent as grpc_gevent


monkey.patch_all()
grpc_gevent.init_gevent()


app = create_app()
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    transports=['websocket', 'polling'],
    async_mode='gevent',
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
