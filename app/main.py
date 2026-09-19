from fastapi import FastAPI
import secrets

app = FastAPI()


@app.get("/")
def root():
    return {
        "service": "SBID API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/token")
def generate_token():
    return {
        "token": secrets.token_urlsafe(32)
    }
