import uvicorn
from core.config import config

if __name__ == "__main__":
    uvicorn.run("app.server:app", host=config.API_HOST, port=config.API_PORT, reload=True)
