"""
Punkt wejścia dla Phusion Passenger na mydevil.net.
Używamy a2wsgi do konwersji ASGI (FastAPI) -> WSGI (Passenger).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from a2wsgi import ASGIMiddleware
from api.index import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
