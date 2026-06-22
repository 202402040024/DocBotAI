import os
import sys
import logging

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from server.main import app
from mangum import Mangum

handler = Mangum(app, lifespan="auto")
