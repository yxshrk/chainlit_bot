import os
import requests
from dotenv import load_dotenv
import datetime
import time as time_module
import pytz
import re

load_dotenv()

def get_api_key():
    api_key = os.getenv('CALCOM_API_KEY')
    if not api_key:
        raise ValueError("CALCOM_API_KEY is missing. Ensure it is set in the environment variables.")
    return api_key

def get_headers(api_version="2024-08-13"):
    api_key = get_api_key()
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'cal-api-version': api_version
    }


def normalize_timezone(timezone_str):
    timezone_mapping = {
        "singapore": "Asia/Singapore",
        "gmt+8": "Asia/Singapore",
        "est": "America/New_York",
        "pst": "America/Los_Angeles"
    }
    
    normalized = timezone_str.lower().replace(" ", "")
    for key, value in timezone_mapping.items():
        if key in normalized:
            return value
    
    return timezone_str

def parse_date_time(date_str, timezone_str):
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    
    formats = [
        "%d %B %Y %I%p",        # "20 March 2025 7pm"
        "%d %B %Y %I %p",       # "20 March 2025 7 pm"
        "%B %d %Y %I%p",        # "March 20 2025 7pm"
        "%B %d %Y %I %p",       # "March 20 2025 7 pm"
        "%d/%m/%Y %I%p",        # "20/3/2025 7pm"
        "%d/%m/%Y %I %p",       # "20/3/2025 7 pm"
        "%Y-%m-%d %I%p",        # "2025-03-20 7pm"
        "%Y-%m-%d %I %p",       # "2025-03-20 7 pm"
    ]
    
    dt = None
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    
    if not dt:
        if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', date_str):
            return date_str
        raise ValueError(f"Could not parse date string: {date_str}")
    
    tz = pytz.timezone(normalize_timezone(timezone_str))
    local_dt = tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.UTC)
    
    now_utc = datetime.datetime.now(pytz.UTC)
    if utc_dt <= now_utc:
        raise ValueError("Booking time must be in the future.")
    
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def get_all_event_types():
    url = "https://api.cal.com/v2/event-types"
    
    # Use the specific API version required for event types
    headers = get_headers(api_version="2024-06-14")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = f" - Status: {e.response.status_code}, Details: {e.response.text}"
        return {"error": f"Failed to get event types: {str(e)}{error_detail}", "status": "error"}

def find_event_type_by_duration(duration):
    response = get_all_event_types()
    
    if "status" in response and response["status"] == "error":
        return response
    
    if "status" in response and response["status"] == "success" and "data" in response:
        for event_type in response["data"]:
            if "lengthInMinutes" in event_type and event_type["lengthInMinutes"] == duration:
                return {
                    "status": "success", 
                    "event_type_id": event_type["id"],
                    "message": f"Found existing event type with {duration} minute duration"
                }
    
    return {"status": "not_found", "message": f"No event type found with {duration} minute duration"}

def create_event_type(title, slug, length_in_minutes):
    url = "https://api.cal.com/v2/event-types"
    
    headers = get_headers(api_version="2024-06-14")
    
    payload = {
        "title": title,
        "slug": slug,
        "lengthInMinutes": length_in_minutes
    }
    
    print(f"Creating event type: {title}, {length_in_minutes} minutes")
    print(f"Request payload: {payload}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = f" - Status: {e.response.status_code}, Details: {e.response.text}"
        print(f"Failed to create event type: {str(e)}{error_detail}")
        return {"error": f"Failed to create event type: {str(e)}{error_detail}", "status": "error"}

def get_or_create_event_type(duration):
    result = find_event_type_by_duration(duration)
    
    if result["status"] == "success":
        print(f"Found existing event type: {result['message']}")
        return result
    
    if result["status"] == "not_found":
        print(f"Creating new event type for {duration} minutes")
        
        timestamp = int(time_module.time())
        title = f"{duration}-Minute Meeting"
        slug = f"{duration}min-meeting-{timestamp}"
        
        creation_result = create_event_type(title, slug, duration)
        
        if "status" in creation_result and creation_result["status"] == "error":
            return creation_result
        
        if "data" in creation_result and "id" in creation_result["data"]:
            return {
                "status": "success", 
                "event_type_id": creation_result["data"]["id"],
                "message": f"Created new event type with {duration} minute duration"
            }
    
    return {"status": "error", "message": "Failed to find or create event type"}

def get_available_slots(event_type_id, start_date, end_date):
    url = "https://api.cal.com/v1/slots"
    
    start_time = f"{start_date}T00:00:00Z"
    end_time = f"{end_date}T23:59:59Z"
    
    params = {
        "apiKey": get_api_key(),
        "eventTypeId": event_type_id,
        "startTime": start_time,
        "endTime": end_time
    }
    
    print(f"Getting available slots for event type {event_type_id}")
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.get(url, headers=headers, params=params)
        print(f"Response Status: {response.status_code}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = f" - Status: {e.response.status_code}, Details: {e.response.text}"
        return {"error": f"Failed to get available slots: {str(e)}{error_detail}", "status": "error"}

def create_booking(event_type_id, start_time, attendee_name, attendee_email, attendee_timezone="America/New_York", duration=None):
    if duration is not None and (event_type_id is None or event_type_id == 0):
        result = get_or_create_event_type(duration)
        if result["status"] == "success" and "event_type_id" in result:
            event_type_id = result["event_type_id"]
            print(f"Using event type ID: {event_type_id} - {result['message']}")
        else:
            return result
    
    url = "https://api.cal.com/v1/bookings"
    
    try:
        event_type_id = int(event_type_id)
    except (ValueError, TypeError):
        return {"error": f"Invalid event type ID: {event_type_id}", "status": "error"}
    
    attendee_timezone = normalize_timezone(attendee_timezone)
    
    if not (start_time.endswith('Z') and 'T' in start_time):
        try:
            start_time = parse_date_time(start_time, attendee_timezone)
        except ValueError as e:
            return {"error": str(e), "status": "error"}
    

    payload = {
        "eventTypeId": event_type_id,
        "start": start_time,
        "responses": {
            "name": attendee_name,
            "email": attendee_email,
            "location": {
                "value": "inPerson",
                "optionValue": ""
            }
        },
        "timeZone": attendee_timezone,
        "language": "en",
        "metadata": {}
    }
    
    params = {
        "apiKey": get_api_key()
    }
    
    print(f"Creating booking for event type {event_type_id}")
    print(f"Payload: {payload}")
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers, params=params)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = f" - Status: {e.response.status_code}, Details: {e.response.text}"
        return {"error": f"Failed to create booking: {str(e)}{error_detail}", "status": "error"}

def list_bookings():
    url = "https://api.cal.com/v1/bookings"
    
    params = {
        "apiKey": get_api_key()
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.get(url, headers=headers, params=params)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = f" - Status: {e.response.status_code}, Details: {e.response.text}"
        return {"error": f"Failed to list bookings: {str(e)}{error_detail}", "status": "error"}


def cancel_booking(booking_id):
    url = f"https://api.cal.com/v1/bookings/{booking_id}"
    
    params = {
        "apiKey": get_api_key()
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.delete(url, headers=headers, params=params)
        
        response.raise_for_status()
        return {"status": "success", "message": "Booking cancelled successfully"}
    except requests.exceptions.RequestException as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = f" - Status: {e.response.status_code}, Details: {e.response.text}"
        return {"error": f"Failed to cancel booking: {str(e)}{error_detail}", "status": "error"}

def reschedule_booking(booking_uid, new_start_time, attendee_timezone="America/New_York"):
    url = f"https://api.cal.com/v2/bookings/{booking_uid}/reschedule"
    
    attendee_timezone = normalize_timezone(attendee_timezone)
    
    if not (new_start_time.endswith('Z') and 'T' in new_start_time):
        try:
            new_start_time = parse_date_time(new_start_time, attendee_timezone)
        except ValueError as e:
            return {"error": str(e), "status": "error"}
    

    payload = {
        "start": new_start_time,
        "rescheduledBy": "USER",  # Use "USER" as a default value
        "reschedulingReason": "User wanted to reschedule"
    }
    
    headers = get_headers(api_version="2024-08-13")
    
    print(f"Rescheduling booking {booking_uid} to {new_start_time}")
    print(f"Payload: {payload}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_detail = ""
        if hasattr(e, 'response') and e.response is not None:
            error_detail = f" - Status: {e.response.status_code}, Details: {e.response.text}"
        return {"error": f"Failed to reschedule booking: {str(e)}{error_detail}", "status": "error"}

