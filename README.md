# ADK Agent & Function Manager API

This project provides a FastAPI-based API and a Streamlit web UI to manage Agents and Global Tool Functions for the Google Agent Development Kit (ADK). It allows for creating, retrieving, updating, and deleting both tool functions (stored in `global_tools.py`) and agent configurations (stored in the `managed_agents/` directory) via the API or the web interface.

## Features

*   **Tool Management (via AST manipulation of `global_tools.py`):**
    *   Add new Python functions.
    *   List existing tool function names.
    *   Retrieve the source code of a specific tool function.
    *   Update the source code of an existing tool function.
    *   Delete a tool function.
*   **Agent Management (via file generation in `managed_agents/`):**
    *   Create new agents: generates directory structure (`managed_agents/<agent_name>/`), configuration (`agent_config.json`), `__init__.py` (for imports), and `agent.py` (instantiating `google.adk.agents.Agent` with specified tools).
    *   List existing agent names.
    *   Retrieve the configuration of a specific agent.
    *   Update an existing agent's configuration and regenerate its `agent.py`.
    *   Delete an agent and its associated files/directory.

## Prerequisites

*   Python 3.9+ 

## Setup and Installation

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This installs FastAPI, Uvicorn, Streamlit, streamlit-ace, requests, and other necessary packages.

## Environment Variables

This project uses a `.env` file in the root directory (`adk_kit/`) to manage sensitive information like API keys. Create a file named `.env` in the project root and add the following variables:

```dotenv
# For Google ADK/Gemini API access
# Set GOOGLE_GENAI_USE_VERTEXAI to TRUE if using Vertex AI, FALSE otherwise
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY_HERE

# For the get_weather tool in global_tools.py
OPENWEATHERMAP_API_KEY=YOUR_OPENWEATHERMAP_API_KEY_HERE
```

## Running the Servers

This project includes up to three server components:

1.  **ADK API Server:** The standard server provided by the Google ADK (`adk web`), which handles agent execution and provides the chat UI. By default, it runs on port **8000**.
2.  **FastAPI Wrapper:** This application (`main.py`), which provides the management API for tools and agents. It is configured to run on port **8001**.
3.  **Streamlit UI (Optional):** A web interface (`streamlit_app.py`) for managing agents and tools via the FastAPI wrapper. Runs on port **8501** by default.


A convenience script `start_servers.sh` is provided to start the necessary servers in the background:

```bash
./start_servers.sh

This will start the ADK API server (port 8000) and the FastAPI wrapper server (port 8001).

To start all three components, including the Streamlit UI, use the `--streamlit` flag:

./start_servers.sh --streamlit

Once running:
*   The **ADK API server** (agent execution and chat UI) will be available at `http://localhost:8000`. The chat UI specifically is at `http://localhost:8000/dev-ui`.
*   The **FastAPI management API** documentation (Swagger UI) will be available at `http://localhost:8001/docs`.
*   If started, the **Streamlit Management UI** will be available at `http://localhost:8501`.


## API Endpoints

### Tools (`global_tools.py`)

*   `POST /tools`: Creates a new tool function.
    *   Body: `ToolFunction` model (`name`, `code`)
*   `GET /tools`: Lists names of all existing tool functions.
*   `GET /tools/{function_name}`: Retrieves the `ToolFunction` (name and code) of a specific function.
*   `PUT /tools/{function_name}`: Updates an existing tool function.
    *   Body: `ToolFunction` model (`name`, `code`)
*   `DELETE /tools/{function_name}`: Deletes a specific tool function.

### Agents (`managed_agents/`)

*   `POST /agents`: Creates a new agent.
    *   Body: `AgentConfig` model (`name`, `model`, `instruction`, `tool_references`, etc.)
*   `GET /agents`: Lists names of all existing agents.
*   `GET /agents/{agent_name}`: Retrieves the `AgentRead` configuration of a specific agent.
*   `PUT /agents/{agent_name}`: Updates an existing agent.
    *   Body: `AgentConfig` model
*   `DELETE /agents/{agent_name}`: Deletes a specific agent and its directory.

## Project Structure

*   `main.py`: The main FastAPI application file containing endpoint logic.
*   `global_tools.py`: Stores the Python code for reusable tool functions managed by the API. Automatically created if it doesn't exist.
*   `managed_agents/`: Directory containing subdirectories for each managed agent. Automatically created if it doesn't exist.
    *   `<agent_name>/`: Directory for a specific agent.
        *   `agent_config.json`: Configuration file for the agent.
        *   `agent.py`: Python file defining the ADK agent, generated from the config.
        *   `__init__.py`: Makes the agent directory a Python package.
*   `requirements.txt`: Lists Python dependencies (FastAPI, Uvicorn, Streamlit, streamlit-ace, requests, etc.).
*   `streamlit_app.py`: A Streamlit application providing a web UI for the management API.
*   `start_servers.sh`: Script to start the ADK API server, the wrapper API, and optionally the Streamlit UI.
*   `README.md`: This file.
