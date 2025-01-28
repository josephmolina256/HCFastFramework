import os
from dotenv import load_dotenv
import uuid
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import logging
from redis import Redis
from rq import Queue
from .chatbot.chatbot import HuggingChatWrapper

load_dotenv()
# Retrieve Redis configuration from environment variables
redis_host = os.getenv('REDIS_HOST')
redis_port = int(os.getenv('REDIS_PORT', 11835))
redis_password = os.getenv('REDIS_PASSWORD')

r = Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)
queue = Queue("tasks", connection=r)

# FastAPI app
app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# In-memory logging of job results (for demonstration)
job_results = {}

# Chat wrapper
chat_wrapper = HuggingChatWrapper()  # Singleton chat wrapper

# Pydantic model for requests
class Query(BaseModel):
    text: str

# Function to process chat asynchronously
def process_chat(job_id: str, text: str):
    try:
        chatbot = chat_wrapper.get_chatbot()
        response = chatbot.chat(text).wait_until_done()  # Blocking call to LLM
        logging.info(f"Job {job_id} completed with response: {response}")
        # Store the result in Redis
        r.set(job_id, response)
    except Exception as e:
        logging.error(f"Job {job_id} failed: {str(e)}")
        # Store error message in Redis
        r.set(job_id, f"Error: {str(e)}")

@app.post("/chat/")
async def chat(query: Query, background_tasks: BackgroundTasks):
    """
    Accepts a chat request, runs it in the background, and returns a job ID.
    """
    # Generate a unique job ID
    job_id = str(uuid.uuid4())

    # Add the job to the Redis queue
    background_tasks.add_task(process_chat, job_id, query.text)

    # Return the job ID to the client
    return {"job_id": job_id, "status": "processing"}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    """
    Fetches the result of a chat job by its ID from Redis.
    """
    result = r.get(job_id)
    if result is None:
        return {"status": "processing", "message": "Job is still being processed."}
    return {"status": "completed", "response": result}

@app.get("/")
async def ping():
    return {"message": "Hello, World!"}
