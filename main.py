from fastapi import FastAPI

app = FastAPI(title="CommandIA Webhook API")

@app.get("/")
def read_root():
    return {"status": "CommandIA API is running", "version": "1.0.0"}