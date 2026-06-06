"""
Punkt wejścia dla Phusion Passenger na mydevil.net.
mydevil używa WSGI — konwertujemy FastAPI (ASGI) przez asgiref.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from asgiref.wsgi import WsgiToAsgi
from api.index import app as _asgi_app

application = WsgiToAsgi(_asgi_app)
