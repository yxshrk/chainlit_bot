import chainlit as cl
from openai_functions import openai_function_calling
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dictionary to store user sessions
user_sessions = {}

@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session."""
    # Send a welcome message
    await cl.Message(
        content="Hello! I'm your Cal.com assistant. I can help you with:\n\n"
               "1. Booking new events\n"
               "2. Listing your scheduled events\n"
               "3. Canceling events\n\n"
               "How can I assist you today?",
    ).send()
    
    # Check for API keys
    if not os.getenv("OPENAI_API_KEY"):
        await cl.Message(
            content="⚠️ OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.",
        ).send()
    
    if not os.getenv("CALCOM_API_KEY"):
        await cl.Message(
            content="⚠️ Cal.com API key not found. Please set the CALCOM_API_KEY environment variable.",
        ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Process user messages and respond with AI-generated content."""
    try:
        await cl.Message(content="").send()
        user_id = message.author or "default_user"
        response = openai_function_calling(user_sessions, user_id, message.content)
        
        await cl.Message(content=response).send()
    
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        await cl.Message(content=error_message).send()


@cl.on_chat_start
async def setup_actions():
    actions = [
        cl.Action(
            name="book_event", 
            payload={"action": "book"},
            label="Book a new event",
            tooltip="Create a new calendar event"
        ),
        cl.Action(
            name="view_events", 
            payload={"action": "view"},
            label="View my events",
            tooltip="Show all scheduled events"
        ),
        cl.Action(
            name="cancel_event", 
            payload={"action": "cancel"},
            label="Cancel an event",
            tooltip="Cancel an existing event"
        ),
        cl.Action(
            name="reschedule_event", 
            payload={"action": "reschedule"},
            label="Reschedule an event",
            tooltip="Reschedule an existing event"
        )
    ]
    
    await cl.Message(
        content="You can also use these quick actions:",
        actions=actions
    ).send()
    
@cl.action_callback("book_event")
async def on_book_event(action):
    await cl.Message(content="Let's book a new event. Please provide the following information:\n\n"
                           "1. The event type ID\n"
                           "2. Date and time for the meeting\n"
                           "3. Your name\n"
                           "4. Your email address").send()

@cl.action_callback("view_events")
async def on_view_events(action):
    await cl.Message(content=openai_function_calling(user_sessions, "default_user", "help me view my scheduled events")).send()

@cl.action_callback("cancel_event")
async def on_cancel_event(action):
    await cl.Message(content=openai_function_calling(user_sessions, "default_user", "list all my scheduled events with their UIDs for me to select one to cancel")).send()

@cl.action_callback("reschedule_event")
async def on_reschedule_event(action):
    await cl.Message(content=openai_function_calling(user_sessions, "default_user", "list all my scheduled events with their UIDs for me to select one to reschedule")).send()