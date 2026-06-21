import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self._clients = {}

    @property
    def client(self) -> AsyncIOMotorClient:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop not in self._clients:
            logger.info(f"Initializing AsyncIOMotorClient for event loop: {loop}")
            self._clients[loop] = AsyncIOMotorClient(settings.MONGODB_URI)
        return self._clients[loop]

    @property
    def db(self):
        return self.client[settings.MONGODB_DB_NAME]

db_client = MongoDB()

async def connect_to_mongo():
    logger.info("MongoDB client dynamic loading initialized.")
    # Warm up client
    _ = db_client.client
    logger.info(f"Database context: {settings.MONGODB_DB_NAME}")

async def close_mongo_connection():
    logger.info("Closing all MongoDB client connections...")
    for client in list(db_client._clients.values()):
        client.close()
    db_client._clients.clear()
    logger.info("MongoDB client connections closed.")

def get_database():
    return db_client.db
