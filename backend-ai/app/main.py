from fastapi import FastAPI

app = FastAPI(title="OpsPilot AI Module")

@app.get("/")
def root():
    return {
        "service": "backend-ai",
        "status": "ok"
    }