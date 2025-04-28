
import streamlit as st
import requests
import json
from streamlit_ace import st_ace # Import the Ace editor component

# --- Configuration ---
API_BASE_URL = "http://localhost:8001" # The address of your ADK Agent/Tool Manager API

# --- API Client Functions ---
def handle_api_response(response):
    """Helper function to handle API responses and errors."""
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            st.error(f"Error decoding JSON response from API. Status code: {response.status_code}")
            return None
    elif response.status_code == 404:
        # Specifically handle 404 for "not found" cases without showing a big error
        return None
    else:
        try:
            detail = response.json().get("detail", response.text)
        except json.JSONDecodeError:
            detail = response.text
        st.error(f"API Error ({response.status_code}): {detail}")
        return None

def get_agents():
    """Fetches the list of agent names from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/agents")
        data = handle_api_response(response)
        # Ensure data is a list before processing
        if isinstance(data, list):
            # Check if the first element is a string (assuming non-empty list)
            # Or handle empty list case
            if not data or isinstance(data[0], str):
                # API returns a list of strings directly
                return data
            elif isinstance(data[0], dict):
                 # API returns a list of dicts (handle previous assumption just in case)
                 return [agent.get("name") for agent in data if isinstance(agent, dict)]
            else:
                 st.error(f"API returned list with unexpected element type for agents: {type(data[0])}")
                 return []
        elif data is not None:
             st.error(f"API returned unexpected data type for agents: {type(data)}")
             return []
        else:
             # handle_api_response already showed an error or it was a 404
             return []
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error fetching agents: {e}")
        return []

def get_agent_details(agent_name):
    """Fetches the configuration details for a specific agent."""
    try:
        response = requests.get(f"{API_BASE_URL}/agents/{agent_name}")
        return handle_api_response(response)
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error fetching agent details for {agent_name}: {e}")
        return None

def get_tools():
    """Fetches the list of tool names from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/tools")
        data = handle_api_response(response)
        # Ensure data is a list before processing
        if isinstance(data, list):
             # Check if the first element is a string (assuming non-empty list)
             # Or handle empty list case
            if not data or isinstance(data[0], str):
                 # API returns a list of strings directly
                 return data
            elif isinstance(data[0], dict):
                 # API returns a list of dicts (handle previous assumption just in case)
                 return [tool.get("name") for tool in data if isinstance(tool, dict)]
            else:
                 st.error(f"API returned list with unexpected element type for tools: {type(data[0])}")
                 return []
        elif data is not None:
            st.error(f"API returned unexpected data type for tools: {type(data)}")
            return []
        else:
            # handle_api_response already showed an error or it was a 404
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error fetching tools: {e}")
        return []

def get_tool_details(tool_name):
    """Fetches the details (name, code) for a specific tool."""
    try:
        # Note: API endpoint uses 'function_name' path parameter
        response = requests.get(f"{API_BASE_URL}/tools/{tool_name}")
        return handle_api_response(response)
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error fetching tool details for {tool_name}: {e}")
        return None

def create_agent(agent_config):
    """Creates a new agent via the API. Returns True on success."""
    try:
        response = requests.post(f"{API_BASE_URL}/agents", json=agent_config)
        if response.status_code == 201: # Created
            # st.success(f"Agent '{agent_config.get('name')}' created successfully!") # Moved
            return True
        else:
            handle_api_response(response) # Display error via helper
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error creating agent: {e}")
        return False

def create_tool(tool_name, tool_code):
    """Creates a new tool via the API. Returns True on success."""
    try:
        payload = {"name": tool_name, "code": tool_code}
        response = requests.post(f"{API_BASE_URL}/tools", json=payload)
        if response.status_code == 201: # Created
            # st.success(f"Tool '{tool_name}' created successfully!") # Moved
            return True
        else:
            handle_api_response(response) # Display error via helper
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error creating tool: {e}")
        return False

def update_agent(agent_name, agent_config):
    """Updates an existing agent via the API. Returns True on success."""
    try:
        # Ensure the name in the URL matches the payload if it's part of the config
        # Or remove it from the payload if the API doesn't expect it
        payload = agent_config.copy()
        if 'name' in payload and payload['name'] != agent_name:
             st.warning("Agent name in payload differs from URL name. Using URL name for endpoint.")
             # Decide API behavior: some might allow name change via PUT, others not.
             # Assuming name change isn't primary via PUT payload here.
             # If name change is allowed, the API endpoint might need adjustment or payload structure.
             # Let's assume the API uses the name in the URL to identify the agent and updates based on payload.
             # If the API expects the name *in* the payload for validation, keep it.
             # If the API *only* uses the URL name, you might remove payload['name'].
             # For now, we keep it but are aware of potential API design implications.

        response = requests.put(f"{API_BASE_URL}/agents/{agent_name}", json=payload)
        if response.status_code == 200:
            # st.success(f"Agent '{agent_name}' updated successfully!") # Moved
            return True
        else:
            handle_api_response(response) # Display error via helper
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error updating agent {agent_name}: {e}")
        return False

def update_tool(tool_name, tool_code):
    """Updates an existing tool (specifically its code) via the API. Returns True on success."""
    try:
        # API expects name and code in the payload for PUT
        payload = {"name": tool_name, "code": tool_code}
        # Note: API endpoint uses 'function_name' path parameter
        response = requests.put(f"{API_BASE_URL}/tools/{tool_name}", json=payload)
        if response.status_code == 200:
            # st.success(f"Tool '{tool_name}' updated successfully!") # Moved
            return True
        else:
            handle_api_response(response) # Display error via helper
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error updating tool {tool_name}: {e}")
        return False

def delete_agent(agent_name):
    """Deletes an agent via the API."""
    try:
        response = requests.delete(f"{API_BASE_URL}/agents/{agent_name}")
        if response.status_code == 200: # OK
             st.success(f"Agent '{agent_name}' deleted successfully!")
             return True
        # Handle cases where deletion might result in 204 No Content as success
        elif response.status_code == 204:
             st.success(f"Agent '{agent_name}' deleted successfully!")
             return True
        else:
            handle_api_response(response) # Display error via helper
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error deleting agent {agent_name}: {e}")
        return False

def delete_tool(tool_name):
    """Deletes a tool via the API."""
    try:
        # Note: API endpoint uses 'function_name' path parameter
        response = requests.delete(f"{API_BASE_URL}/tools/{tool_name}")
        if response.status_code == 200: # OK
             st.success(f"Tool '{tool_name}' deleted successfully!")
             return True
        # Handle cases where deletion might result in 204 No Content as success
        elif response.status_code == 204:
             st.success(f"Tool '{tool_name}' deleted successfully!")
             return True
        else:
            handle_api_response(response) # Display error via helper
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error deleting tool {tool_name}: {e}")
        return False

# --- UI Rendering ---
st.set_page_config(layout="wide") # Use wide layout for better space utilization

# --- Display Success Message (if any) ---
if 'success_message' in st.session_state:
    st.success(st.session_state['success_message'])
    del st.session_state['success_message'] # Clear the message after displaying

st.title("ADK Agent & Tool Manager")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
section = st.sidebar.radio("Go to", ["Agent Management", "Tool Management"])

# --- Main Content Area ---
if section == "Agent Management":
    st.header("Agent Management")

    agent_names = get_agents()
    agent_options = ["--- Create New Agent ---"] + sorted(agent_names) # Add create option and sort

    selected_agent_name = st.selectbox("Select Agent", options=agent_options)

    if selected_agent_name == "--- Create New Agent ---":
        st.subheader("Create New Agent")
        with st.form("create_agent_form", clear_on_submit=True):
            agent_name = st.text_input("Agent Name*", key="create_agent_name")
            agent_model = st.text_input("Model", value="gpt-4", key="create_agent_model") # Default model
            agent_description = st.text_input("Description", key="create_agent_desc")
            agent_instruction = st.text_area("Instruction*", height=200, key="create_agent_instruction")

            # Fetch available tools for the multiselect
            available_tools = get_tools()
            selected_tools = st.multiselect(
                "Select Tools",
                options=available_tools,
                key="create_agent_tools"
            )

            submitted = st.form_submit_button("Create Agent")
            if submitted:
                if not agent_name or not agent_instruction:
                    st.warning("Agent Name and Instruction are required fields.")
                else:
                    agent_config = {
                        "name": agent_name,
                        "model": agent_model,
                        "description": agent_description,
                        "instruction": agent_instruction,
                        "tool_references": selected_tools
                    }
                    if create_agent(agent_config):
                        st.session_state['success_message'] = f"Agent '{agent_name}' created successfully!"
                        st.rerun() # Rerun to show message and update list
                    # Error is handled within create_agent

    elif selected_agent_name:
        st.subheader(f"Details for Agent: {selected_agent_name}")
        agent_details = get_agent_details(selected_agent_name)
        if agent_details:
            st.subheader("Current Configuration")
            st.json(agent_details)

            # --- Chat Button ---
            chat_url = f"http://localhost:8000/dev-ui?app={selected_agent_name}"
            st.link_button("Chat with this Agent", url=chat_url, type="primary")
            st.write("---") # Separator

            st.subheader("Update Agent")
            # Use a unique key based on the agent name to avoid state issues if the selection changes
            with st.form(f"update_agent_{selected_agent_name}_form"):
                # Pre-fill form with existing details
                # Name might be read-only depending on API capability/design choice
                # st.text_input("Agent Name (Read-Only)", value=agent_details.get("name"), key=f"update_agent_name_{selected_agent_name}", disabled=True)
                updated_model = st.text_input("Model", value=agent_details.get("model", "gpt-4"), key=f"update_agent_model_{selected_agent_name}")
                updated_description = st.text_input("Description", value=agent_details.get("description", ""), key=f"update_agent_desc_{selected_agent_name}")
                updated_instruction = st.text_area("Instruction*", value=agent_details.get("instruction", ""), height=200, key=f"update_agent_instruction_{selected_agent_name}")

                available_tools = get_tools()
                # Pre-select current tools
                current_tools = agent_details.get("tool_references", [])
                updated_tools = st.multiselect(
                    "Select Tools",
                    options=available_tools,
                    default=current_tools,
                    key=f"update_agent_tools_{selected_agent_name}"
                )

                update_submitted = st.form_submit_button("Update Agent")
                if update_submitted:
                    if not updated_instruction: # Name is read-only, instruction is key
                         st.warning("Instruction is a required field.")
                    else:
                        updated_agent_config = {
                            "name": selected_agent_name, # Keep original name
                            "model": updated_model,
                            "description": updated_description,
                            "instruction": updated_instruction,
                            "tool_references": updated_tools
                        }
                        if update_agent(selected_agent_name, updated_agent_config):
                            st.session_state['success_message'] = f"Agent '{selected_agent_name}' updated successfully!"
                            st.rerun() # Refresh data and show message
                        # Error handled in update_agent

            st.write("---") # Separator

            # --- Delete Agent Section ---
            st.subheader("Delete Agent")
            st.warning(f"**Warning:** Deleting agent '{selected_agent_name}' cannot be undone.")
            # Use a unique key for the delete button as well
            if st.button("Delete Agent Permanently", key=f"delete_agent_{selected_agent_name}"):
                if delete_agent(selected_agent_name):
                    st.session_state['success_message'] = f"Agent '{selected_agent_name}' deleted successfully!"
                    st.rerun() # Refresh the page to update the list and show message
                # Error handled in delete_agent

        else:
            st.warning(f"Could not retrieve details for agent '{selected_agent_name}'. It might have been deleted.")


elif section == "Tool Management":
    st.header("Tool Management")

    tool_names = get_tools()
    tool_options = ["--- Create New Tool ---"] + sorted(tool_names) # Add create option and sort

    selected_tool_name = st.selectbox("Select Tool", options=tool_options)

    if selected_tool_name == "--- Create New Tool ---":
        st.subheader("Create New Tool")
        with st.form("create_tool_form", clear_on_submit=True):
            tool_name = st.text_input("Tool Name*", key="create_tool_name")
            # Replace st.text_area with st_ace
            tool_code = st_ace(
                language="python",
                theme="tomorrow_night", # Example theme, many available
                key="create_tool_code_ace",
                height=300,
                auto_update=True # Update value on change
            )

            submitted = st.form_submit_button("Create Tool")
            if submitted:
                if not tool_name or not tool_code:
                    st.warning("Tool Name and Code are required fields.")
                else:
                    if create_tool(tool_name, tool_code):
                        st.session_state['success_message'] = f"Tool '{tool_name}' created successfully!"
                        st.rerun() # Rerun to update the selectbox and show message
                    # Error is handled within create_tool

    elif selected_tool_name:
        st.subheader(f"Details for Tool: {selected_tool_name}")
        tool_details = get_tool_details(selected_tool_name)
        if tool_details:
            st.subheader("Current Code")
            # Display name, but don't make it an input field for update
            st.text(f"Name: {tool_details.get('name', 'N/A')}")
            st.code(tool_details.get('code', '# No code found'), language='python')

            st.subheader("Update Tool Code")
            # Use a unique key based on the tool name
            with st.form(f"update_tool_{selected_tool_name}_form"):
                 # Name is usually not updatable via PUT code endpoint, treat as read-only display
                 st.text(f"Updating code for: {selected_tool_name}")
                 # Replace st.text_area with st_ace, pre-filled with current code
                 updated_tool_code = st_ace(
                     value=tool_details.get('code', ''),
                     language="python",
                     theme="tomorrow_night", # Use the same theme
                     key=f"update_tool_code_ace_{selected_tool_name}", # Unique key
                     height=300,
                     auto_update=True # Update value on change
                 )

                 update_submitted = st.form_submit_button("Update Tool Code")
                 if update_submitted:
                     if not updated_tool_code:
                         st.warning("Tool Code is required.")
                     else:
                         if update_tool(selected_tool_name, updated_tool_code):
                             st.session_state['success_message'] = f"Tool '{selected_tool_name}' updated successfully!"
                             st.rerun() # Refresh data and show message
                         # Error handled in update_tool

            st.write("---") # Separator

            # --- Delete Tool Section ---
            st.subheader("Delete Tool")
            st.warning(f"**Warning:** Deleting tool '{selected_tool_name}' cannot be undone. This might break agents using this tool.")
            # Use a unique key for the delete button
            if st.button("Delete Tool Permanently", key=f"delete_tool_{selected_tool_name}"):
                if delete_tool(selected_tool_name):
                    st.session_state['success_message'] = f"Tool '{selected_tool_name}' deleted successfully!"
                    st.rerun() # Refresh the page to update the list and show message
                # Error handled in delete_tool

        else:
             st.warning(f"Could not retrieve details for tool '{selected_tool_name}'. It might have been deleted.")


# --- Helper Functions (e.g., for refreshing lists) ---
# (We might add some here later)
