"""
Punkt wejścia dla Phusion Passenger na mydevil.net.
Używamy a2wsgi do konwersji ASGI (FastAPI) -> WSGI (Passenger).
init_db() wywołane tutaj bo startup lifespan nie odpala przez a2wsgi.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.database import init_db
init_db()

from a2wsgi import ASGIMiddleware
from api.index import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
