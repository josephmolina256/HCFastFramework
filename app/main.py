from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Query(BaseModel):
    text: str

@app.get("/")
async def ping():
    """
    Health check for the API
    """
    return {"message": "Hello, World!"}

@app.post("/echo/")
async def echo(query: Query):
    """
    Echo's back the user's input. 
    Good test for when the LLM integration comes in.
    """
    if not query.text.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return {"echo": query.text}

