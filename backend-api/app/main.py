from fastapi import FastAPI

app = FastAPI(title="OpsPilot API")

@app.get("/")
def root():
    return {
        "service": "backend-api",
        "status": "ok"
    }
