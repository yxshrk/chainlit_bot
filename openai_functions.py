import json
import os
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import calcom_api


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

functions = [
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Book a new event with the specified details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type_id": {
                        "type": "integer",
                        "description": "The ID of the event type to book. Set this to the appropriate ID (e.g., 2092097 for a 30-minute meeting) if you know it, or leave it as 0 if you're specifying a custom duration instead."
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Custom duration of the meeting in minutes (e.g., 45 for a 45-minute meeting). The system will find or create an appropriate event type. Set this to the requested duration, or leave it as 0 if you're using a specific event_type_id instead."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in a human-readable format (e.g., '10 April 2025 2pm') or ISO 8601 format. This will be properly formatted."
                    },
                    "attendee_name": {
                        "type": "string",
                        "description": "Name of the attendee."
                    },
                    "attendee_email": {
                        "type": "string",
                        "description": "Email of the attendee."
                    },
                    "attendee_timezone": {
                        "type": "string",
                        "description": "Timezone of the attendee (e.g., 'America/New_York', 'Asia/Singapore')."
                    }
                },
                "required": ["event_type_id", "duration", "start_time", "attendee_name", "attendee_email", "attendee_timezone"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_bookings",
            "description": "List all scheduled bookings.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel a specific booking by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "integer",
                        "description": "ID of the booking to cancel."
                    }
                },
                "required": ["booking_id"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_booking",
            "description": "Reschedule an existing booking to a new time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_uid": {
                        "type": "string",
                        "description": "The unique identifier (UID) of the booking to reschedule."
                    },
                    "new_start_time": {
                        "type": "string",
                        "description": "New start time in a human-readable format (e.g., '10 April 2025 2pm') or ISO 8601 format. Must be in the future."
                    },
                    "attendee_timezone": {
                        "type": "string",
                        "description": "Timezone of the attendee (e.g., 'America/New_York', 'Asia/Singapore')."
                    }
                },
                "required": ["booking_uid", "new_start_time", "attendee_timezone"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
]

def format_date_with_model(date_text, timezone, message_history=None):
    if not message_history:
        message_history = []
        
    system_message = (
        "You are a date formatting assistant. Your sole job is to convert date and time strings "
        "to ISO 8601 format with millisecond precision in UTC timezone. Output ONLY the ISO string "
        "without any explanation or additional text. Format: YYYY-MM-DDTHH:MM:SS.000Z"
    )
    
    prompt = (
        f"Convert this date and time: '{date_text}' in timezone '{timezone}' to ISO 8601 format. "
        f"Return ONLY the formatted date string in format 'YYYY-MM-DDTHH:MM:SS.000Z' in UTC timezone."
    )
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0, 
            max_tokens=50
        )
        
        formatted_date = response.choices[0].message.content.strip()
        
        if "T" in formatted_date and "Z" in formatted_date:
            return formatted_date
        else:
            return calcom_api.parse_date_time(date_text, timezone)
            
    except Exception as e:
        print(f"Error formatting date with model: {str(e)}")
        return calcom_api.parse_date_time(date_text, timezone)

#the earlier version of the function was using user_prompts, we keep the variable passed for future modifications
def handle_function_call(function_name, arguments, user_prompt=""):
    """Execute the appropriate Cal.com API function based on the function name and arguments."""
    print(f"Handling function call: {function_name}")
    print(f"Arguments: {arguments}")
    
    try:
        if function_name == "create_booking":
            event_type_id = arguments.get("event_type_id", 0)
            duration = arguments.get("duration", 30)
            start_time = arguments.get("start_time")
            attendee_name = arguments.get("attendee_name")
            attendee_email = arguments.get("attendee_email")
            attendee_timezone = arguments.get("attendee_timezone", "America/New_York")
            
            try:
                if not (start_time.endswith('Z') and 'T' in start_time):
                    formatted_start_time = format_date_with_model(start_time, attendee_timezone)
                else:
                    formatted_start_time = start_time
                
                print(f"Original start time: {start_time}")
                print(f"Formatted start time: {formatted_start_time}")
            except Exception as e:
                print(f"Error formatting start time with model: {str(e)}")
                formatted_start_time = start_time
            
            #if there is an event id 
            if event_type_id and event_type_id > 0:
                return calcom_api.create_booking(
                    event_type_id=event_type_id,
                    start_time=formatted_start_time,
                    attendee_name=attendee_name,
                    attendee_email=attendee_email,
                    attendee_timezone=attendee_timezone
                )
            else:
                return calcom_api.create_booking(
                    event_type_id=None,
                    start_time=formatted_start_time,
                    attendee_name=attendee_name,
                    attendee_email=attendee_email,
                    attendee_timezone=attendee_timezone,
                    duration=duration
                )
            
        
        elif function_name == "list_bookings":
            return calcom_api.list_bookings()
        
        elif function_name == "cancel_booking":
            booking_id = arguments.get("booking_id")
            return calcom_api.cancel_booking(booking_id)
        
        elif function_name == "reschedule_booking":
            booking_uid = arguments.get("booking_uid")
            new_start_time = arguments.get("new_start_time")
            attendee_timezone = arguments.get("attendee_timezone", "America/New_York")
        
            try:
                formatted_start_time = format_date_with_model(new_start_time, attendee_timezone)
                print(f"Formatted new start time: {formatted_start_time}")
            except Exception as e:
                print(f"Error formatting new start time: {str(e)}")
                formatted_start_time = new_start_time
                
            return calcom_api.reschedule_booking(
                booking_uid=booking_uid,
                new_start_time=formatted_start_time,
                attendee_timezone=attendee_timezone
            )
        
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    except Exception as e:
        print(f"Error in function call: {str(e)}")
        return {"error": f"Error executing {function_name}: {str(e)}"}

def openai_function_calling(user_sessions, user_id, prompt):

    #we save user sessions with pending functions and parameters to ensure that the user can continue providing inputs
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "conversation_history": [],
            "pending_function": None,
            "pending_params": {}
        }
    
    session = user_sessions[user_id]


    #we are adding user's latest message to conversation history, ensuring their new input becomes part of the context
    session["conversation_history"].append({"role": "user", "content": prompt})
    
    if session["pending_function"]:
        function_name = session["pending_function"]
        current_params = session["pending_params"]
        
        #we add special system message that isn't part of the permanent conversation history, but gives GPT instructions on interpreting current turn
        messages = session["conversation_history"].copy()
        messages.append({
            "role": "system", 
            "content": (
                f"The user is providing additional information for the '{function_name}' function. " +
                f"Current parameters: {json.dumps(current_params)}. " +
                "Extract any missing required parameters from their message. " + 
                "For dates and times, be very precise and extract exact date, time, and timezone information. " +
                "For event durations, extract the exact number of minutes for the meeting. " +
                "For create_booking, when setting the duration parameter, extract it directly from the user's request. " +
                "Make sure to verify that dates are in the future. If the user says 'tomorrow', check the current date " +
                "to ensure accuracy. Always include the timezone when formatting dates."
            )
        })
        
        # extracting parameters 
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=functions,
            tool_choice={"type": "function", "function": {"name": function_name}}
        )
        
        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            new_args = json.loads(tool_calls[0].function.arguments)
            current_params.update(new_args)
            
            
            for f in functions:
                if f["function"]["name"] == function_name:
                    required_fields = f["function"]["parameters"].get("required", [])
                    missing_fields = [field for field in required_fields if field not in current_params]
                    
                    if not missing_fields:
                        function_result = handle_function_call(function_name, current_params, prompt)
                        
                        #records that GPT decided to call a function X with certain parameters
                        session["conversation_history"].append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_" + function_name,
                                    "type": "function",
                                    "function": {
                                        "name": function_name,
                                        "arguments": json.dumps(current_params)
                                    }
                                }
                            ]
                        })
                        
                        #records the result of executing the function in the conversation history where tool_call_id matches id from above
                        session["conversation_history"].append({
                            "role": "tool",
                            "tool_call_id": "call_" + function_name,
                            "content": json.dumps(function_result)
                        })
                        
                        
                        session["pending_function"] = None
                        session["pending_params"] = {}
                        

                        final_response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=session["conversation_history"]
                        )
                        
                        response_message = final_response.choices[0].message
                        session["conversation_history"].append(response_message)
                        
                        return response_message.content
                    else:
                        missing_str = ", ".join(missing_fields)
                        return f"I still need the following information to {function_name.replace('_', ' ')}: {missing_str}"
    
    
    #we assume here that there are no pending functions
    messages = session["conversation_history"].copy()
    
    messages.insert(0, {
        "role": "system",
        "content": (
            "You are a helpful assistant that helps users manage their calendar using Cal.com. "
            "You can help users book new meetings, list their scheduled events where you will always include the booking UID, and cancel meetings but remember to showcase, "
            "the booking timings in the local time of the user as specified on the Cal.com platform. "
            "When helping users book a meeting, collect all necessary information like date, time, "
            "and attendee details. "
            "\n\nWhen users indicate they want a meeting of a specific duration (e.g., '45-minute call', "
            "'25-minute meeting'), always set that in the 'duration' parameter for create_booking. "
            "For the 'event_type_id' parameter, you can use 0 as a placeholder value if you're using duration. "
            "Only use specific event_type_ids (like 2092097 for 30 minutes) if the user specifically requests that ID. "
            "\n\nWhen handling dates and times, be extremely precise. Always confirm the timezone, "
            "and make sure to check that the requested date is in the future. If the user says 'tomorrow', "
            "verify the current date to ensure accuracy. Always confirm actions before executing them "
            "and explain the outcomes clearly to the user."
            "For reschedule_booking, you'll need the booking UID from a previous list_bookings call. "
            "When listing bookings, always point out the 'uid' or 'reschedule_uid' field to the user "
            "and explain they'll need this value to reschedule the meeting. "
            "Ask users to list their bookings first if they want to reschedule but don't provide a booking UID. "
        )
    })
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=functions,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    

    session["conversation_history"].append(response_message)
    
    if tool_calls:
        function_responses = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            missing_fields = []
            for f in functions:
                if f["function"]["name"] == function_name:
                    required_fields = f["function"]["parameters"].get("required", [])
                    missing_fields = [field for field in required_fields if field not in function_args]
                    break
            
            #if there are missing fields, we instantiate the session pending function and pending params fields
            if missing_fields:
                session["pending_function"] = function_name
                session["pending_params"] = function_args
                missing_str = ", ".join(missing_fields)
                return f"To {function_name.replace('_', ' ')}, I need the following information: {missing_str}"
            

            function_result = handle_function_call(function_name, function_args, prompt)
            function_responses.append({
                "tool_call_id": tool_call.id,
                "function_name": function_name,
                "result": function_result
            })
            

            session["conversation_history"].append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(function_result)
            })
        
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=session["conversation_history"]
        )
        
        final_message = final_response.choices[0].message
        session["conversation_history"].append(final_message)
        
        return final_message.content
    
    
    return response_message.content