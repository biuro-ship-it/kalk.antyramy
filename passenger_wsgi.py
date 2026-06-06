"""
Punkt wejścia dla Phusion Passenger na mydevil.net.
Passenger obsługuje ASGI od wersji 6 — przekazujemy app FastAPI bezpośrednio.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.index import app as application
