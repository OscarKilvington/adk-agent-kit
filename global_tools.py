import requests
import datetime
import os
import pytz 
from zoneinfo import ZoneInfo 
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from timezonefinder import TimezoneFinder
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_current_time(city: str) -> dict:
    """
    Retrieves the current date and time for a specified city, accounting for its timezone.

    Uses geopy (Nominatim) for geocoding and timezonefinder for timezone lookup.
    Uses datetime and zoneinfo (or pytz fallback) for time retrieval.

    Args:
        city (str): The name of the city.

    Returns:
        dict: A dictionary containing status and report/error_message.
    """
    try:
        # 1. City to Coordinates using Nominatim (Free OpenStreetMap geocoder)
        #    Requires a unique user_agent string for your application.
        #    Be mindful of Nominatim's usage policy (max 1 req/sec, caching). [9, 10]
        # IMPORTANT: Replace "my_global_tools_app/1.0" with your actual app name/version
        geolocator = Nominatim(user_agent="adk_kit_global_tools/1.0") # Example user agent
        location = geolocator.geocode(city, timeout=10) # [5, 8, 11, 23]

        if location is None:
            return {
                "status": "error",
                "error_message": f"Sorry, I couldn't geocode or find the city '{city}'. Please check the spelling or try a more specific location."
            }

        # 2. Coordinates to Timezone using timezonefinder
        tf = TimezoneFinder() # [17, 23]
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude) # [15, 17, 23]

        if timezone_str is None:
            return {
                "status": "error",
                "error_message": f"Sorry, I couldn't determine the timezone for the location of '{city}' ({location.latitude}, {location.longitude})."
            }

        # 3. Get Current Time using the timezone
        try:
            # Use zoneinfo (Python 3.9+)
            city_tz = ZoneInfo(timezone_str)
        except ImportError:
            # Fallback to pytz for older Python versions
            try:
                city_tz = pytz.timezone(timezone_str) # [15, 30]
            except pytz.UnknownTimeZoneError:
                 return {
                    "status": "error",
                    "error_message": f"Sorry, the timezone '{timezone_str}' found for '{city}' is not recognized."
                 }

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_local = now_utc.astimezone(city_tz)

        # 4. Formatting
        # Format: YYYY-MM-DD HH:MM:SS TZNAMEOFFSET (e.g., 2025-04-28 09:58:00 EDT-0400)
        formatted_time = now_local.strftime('%Y-%m-%d %H:%M:%S %Z%z')

        # Adjust offset format slightly (e.g., +0100 -> +01:00 for readability if desired, but %z gives +0100)
        # If you need the colon: formatted_time = f"{now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}{now_local.strftime('%z')[:3]}:{now_local.strftime('%z')[3:]}"

        return {
            "status": "success",
            "report": f"The current time in {location.address} is {formatted_time}"
        }

    except GeocoderTimedOut:
        return {
            "status": "error",
            "error_message": f"Geocoding service timed out while looking up '{city}'. Please try again later."
        }
    except GeocoderServiceError as e:
        return {
            "status": "error",
            "error_message": f"Geocoding service error for '{city}': {e}"
        }
    except Exception as e:
        # Catch any other unexpected errors
        return {
            "status": "error",
            "error_message": f"An unexpected error occurred while getting the time for '{city}': {e}"
        }

def get_weather(city: str) -> dict:
    """
    Retrieves a current weather summary for a specified city using OpenWeatherMap OneCall API v3.0.

    Args:
        city (str): The name of the city.

    Returns:
        dict: A dictionary containing status and report/error_message.
    """
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "error_message": "OpenWeatherMap API key not configured. Please set the OPENWEATHERMAP_API_KEY environment variable."
        }

    try:
        # 1. Geocode city to get latitude and longitude
        geolocator = Nominatim(user_agent="adk_kit_global_tools/1.0") # Use the same user agent
        location = geolocator.geocode(city, timeout=10)

        if location is None:
            return {
                "status": "error",
                "error_message": f"Sorry, I couldn't geocode or find the city '{city}'. Please check the spelling or try a more specific location."
            }

        lat = location.latitude
        lon = location.longitude
        city_name_found = location.address # Use geocoded address for clarity

        # 2. Call OpenWeatherMap OneCall API v3.0
        # Base URL for OneCall API v3.0
        base_url = "https://api.openweathermap.org/data/3.0/onecall"
        # Parameters for the API call
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric', # Get temperature in Celsius
            'exclude': 'minutely,hourly,daily,alerts' # We only want current weather
        }

        # 3. API Integration: Make the HTTP request
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX, 5XX)

        # 4. Data Parsing (v3.0 structure)
        weather_data = response.json()

        # Check for API errors within the JSON response (though raise_for_status handles most)
        # Note: v3.0 might not use 'cod' like v2.5. Check response structure on error.
        if 'message' in weather_data and response.status_code != 200:
             return {
                "status": "error",
                "error_message": f"OpenWeatherMap API error for '{city}': {weather_data['message']}"
            }

        # Extract relevant info from the 'current' block
        current_weather = weather_data.get("current")
        if not current_weather:
            return {
                "status": "error",
                "error_message": f"Could not find 'current' weather data in OpenWeatherMap v3.0 response for '{city}'."
            }

        temp_c = current_weather.get("temp")
        weather_desc_list = current_weather.get("weather")
        description = weather_desc_list[0].get("description") if weather_desc_list else "N/A"

        if temp_c is None:
             return {
                "status": "error",
                "error_message": f"Could not find temperature data in OpenWeatherMap v3.0 response for '{city}'."
            }

        # 5. Report Generation & Units
        # Convert Celsius to Fahrenheit
        temp_f = (temp_c * 9/5) + 32

        report = (f"The weather in {city_name_found} is currently {temp_c:.1f}°C "
                  f"({temp_f:.1f}°F) with {description}.")

        return {
            "status": "success",
            "report": report
        }

    # Handle Geocoding errors separately
    except GeocoderTimedOut:
        return {
            "status": "error",
            "error_message": f"Geocoding service timed out while looking up '{city}'. Please try again later."
        }
    except GeocoderServiceError as e:
        return {
            "status": "error",
            "error_message": f"Geocoding service error for '{city}': {e}"
        }
    # Handle API request errors
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        # Try to get error message from response body if available
        try:
            api_error_message = http_err.response.json().get('message', str(http_err))
        except ValueError: # Handle cases where response is not JSON
            api_error_message = str(http_err)

        if status_code == 401: # Unauthorized
            error_message = f"Authentication error for '{city}'. Check your OpenWeatherMap API key (ensure it's valid and activated for v3.0)."
        elif status_code == 400: # Bad Request (often invalid lat/lon or parameters)
             error_message = f"Bad request to OpenWeatherMap API for '{city}'. Check coordinates or parameters. API message: {api_error_message}"
        elif status_code == 429: # Too Many Requests
            error_message = f"Rate limit exceeded for OpenWeatherMap API. You may need to wait or check your plan limits."
        else:
            error_message = f"HTTP error occurred while getting weather for '{city}': {api_error_message}"
        return {"status": "error", "error_message": error_message}
    except requests.exceptions.ConnectionError:
         return {
            "status": "error",
            "error_message": f"Network error: Could not connect to OpenWeatherMap to get weather for '{city}'."
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "error_message": f"Request timed out while getting weather for '{city}'."
        }
    except requests.exceptions.RequestException as req_err:
        return {
            "status": "error",
            "error_message": f"An error occurred during the weather request for '{city}': {req_err}"
        }
    except Exception as e:
        # Catch any other unexpected errors (like JSON parsing issues not caught above)
        return {
            "status": "error",
            "error_message": f"An unexpected error occurred while getting the weather for '{city}': {e}"
        }

def update_crm_account_notes(customer_id: str, note: str, chat_id: str) -> dict:
    """
    Adds a note to the specified customer's account in the CRM.

    Args:
        customer_id (str): The identifier for the customer in CRM.
        note (str): The content of the note to add.
        chat_id (str, optional): The identifier for the current chat or interaction, if available.

    Returns:
        dict: A dictionary indicating the outcome.
              {'status': 'success', 'message': 'Note added successfully.'} on success.
              {'status': 'error', 'error_message': 'Details about the error.'} on failure.
    """
    print(f"--- Tool: update_crm_account_notes ---")
    print(f"  - Customer ID: {customer_id}")
    print(f"  - Note: {note}")
    # In a live scenario, this would interact with CRM API, potentially logging the chat_id with the note.
    # For now, we simulate success
    return {"status": "success", "message": f"Note added successfully for customer {customer_id}."}

def report_problem(problem_description: str, session_id: str) -> dict:
    """
    Reports a problem encountered during the process to the designated manager or system.

    Use this tool when you encounter an issue you cannot resolve yourself,
    such as persistent tool errors after retrying (if applicable),
    critically missing information preventing any action, or unexpected situations
    not covered by standard procedures.

    Args:
        problem_description (str): A clear and concise description of the problem encountered.
        session_id (str, optional): The identifier for the current chat session.

    Returns:
        dict: A dictionary indicating the outcome.
              {'status': 'success', 'message': 'Problem reported successfully.'} on success.
              {'status': 'error', 'error_message': 'Details about the reporting error.'} on failure.
    """
    print(f"--- Tool: report_problem ---")
    print(f"  - Session ID: {session_id if session_id else 'Not Provided'}")
    print(f"  - Problem Description: {problem_description}")
    # In a real scenario, this could send a notification (email, Slack, etc.)
    # or log to a specific monitoring system, including the session_id for context.
    # For now, we simulate success.
    return {"status": "success", "message": "Problem reported successfully."}



