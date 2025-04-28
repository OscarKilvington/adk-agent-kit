from google.adk.agents import Agent
from global_tools import get_current_time, get_weather, report_problem

tools_list = [get_current_time, get_weather, report_problem]

# Agent definition generated from config
root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description="Agent to answer questions about the time and weather in a city.!",
    instruction="""You are a helpful agent who can answer user questions about the time and weather in a city. When asked about a country you will ask if the checking for the capital city of that country is ok""",
    tools=tools_list,
)
