import os
from dotenv import load_dotenv
import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
import logging
from redis import Redis
from rq import Queue
from .chatbot.chatbot import HuggingChatWrapper
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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

# Initialize Slack client
slack_token = os.getenv('SLACK_BOT_TOKEN')
slack_client = WebClient(token=slack_token)

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

# Slack event handling route
@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    slack_event = await request.json()

    # Verify the Slack challenge (for URL verification)
    if "challenge" in slack_event:
        return {"challenge": slack_event["challenge"]}

    # Handle message events
    if "event" in slack_event:
        slack_message = slack_event["event"]

        # Ignore bot messages (to avoid infinite loops)
        if slack_message.get("subtype") == "bot_message":
            return {"status": "ok"}

        # Get the message text and channel ID
        message_text = slack_message.get("text")
        channel_id = slack_message.get("channel")
        
        # Check if the message starts with "echo:"
        if message_text.lower().startswith("echo:"):
            # Just echo the message text, removing the "echo:" prefix
            response_message = message_text[5:].strip()  # Remove "echo:" and any surrounding whitespace
        else:
            # Generate a job ID for the chat
            job_id = str(uuid.uuid4())

            # Send the message to your API (use your chatbot endpoint)
            background_tasks.add_task(process_chat, job_id, message_text)

            # Wait for the result (you can add a timeout here)
            result = r.get(job_id)

            if result is None:
                response_message = "Processing your request..."
            else:
                response_message = result

        # Respond to Slack with the generated response
        try:
            response = slack_client.chat_postMessage(
                channel=channel_id,
                text=response_message
            )
        except SlackApiError as e:
            response = e.response
            logging.error(f"Error sending message to Slack: {e.response['error']}")

    return {"res": response}
