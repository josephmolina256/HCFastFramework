from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

# Assuming the chatbot logic is in a separate file (chatbot/chatbot.py)
from .chatbot.chatbot import HuggingChatWrapper


app = FastAPI()
chat_wrapper = HuggingChatWrapper() # singleton instance

# dependency injection helper
def get_chat_wrapper() -> HuggingChatWrapper:
    return chat_wrapper

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

@app.post("/chat/")
async def chat(query: Query, wrapper: HuggingChatWrapper = Depends(get_chat_wrapper)):
    """
    Calls the HuggingChat API and returns the response.
    """
    try:
        response = wrapper.get_chatbot().chat(query.text).wait_until_done()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during chat: {str(e)}")
    

@app.get("/list_llms/")
async def list_llms(wrapper: HuggingChatWrapper = Depends(get_chat_wrapper)):
    """
    Calls the HuggingChat API and returns the response.
    """
    try:
        response = wrapper.get_chatbot().get_remote_llms()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during chat: {str(e)}")
