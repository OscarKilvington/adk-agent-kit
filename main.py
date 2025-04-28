import os
import os
import shutil
import ast
import inspect
import importlib.util
import re # Added for sanitization
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator # Added field_validator
from typing import List, Optional, Dict, Any

# --- Configuration ---
GLOBAL_TOOLS_FILE = "global_tools.py"
MANAGED_AGENTS_DIR = "managed_agents"

# --- Ensure Base Files/Directories Exist ---
if not os.path.exists(GLOBAL_TOOLS_FILE):
    with open(GLOBAL_TOOLS_FILE, "w", encoding="utf-8") as f:
        f.write("# Global tool functions managed by the API\n")
        f.write("import datetime\n") # Add common imports maybe?
        f.write("from zoneinfo import ZoneInfo\n\n")
os.makedirs(MANAGED_AGENTS_DIR, exist_ok=True)
# --- Helper Function for Name Sanitization ---

def sanitize_agent_name(name: str) -> str:
    """Converts a string into a valid Python identifier for agent names."""
    if not isinstance(name, str): # Handle potential non-string input
        raise ValueError("Agent name must be a string.")

    # Replace common invalid chars (space, hyphen) with underscore
    name = name.replace(" ", "_").replace("-", "_")

    # Remove any characters that are not letters, digits, or underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)

    # Remove leading/trailing underscores that might be left after substitution
    name = name.strip('_')

    # Prepend underscore if the name starts with a digit
    if name and name[0].isdigit():
        name = "_" + name

    # Ensure the name is not empty after sanitization
    if not name:
        raise ValueError("Agent name cannot be empty or contain only invalid characters after sanitization.")

    # Final check to ensure it's a valid identifier
    if not name.isidentifier():
         # This should ideally not be reached if the logic above is correct, but acts as a safeguard.
         raise ValueError(f"Sanitized name '{name}' is still not a valid Python identifier.")

    return name

# --- Pydantic Models ---

class ToolFunction(BaseModel):
    name: str = Field(..., description="Name of the Python function.")
    code: str = Field(..., description="Full Python code definition of the function, including signature and docstring.")
    # Optional: Could add fields for parameters, return type, docstring separately if needed for validation

class AgentConfig(BaseModel):
    name: str = Field(..., description="Unique name for the agent (will be the directory name)")
    model: str = Field(default="gemini-2.0-flash", description="LLM model ID")
    description: Optional[str] = Field(default=None, description="Description of the agent's purpose")
    instruction: str = Field(..., description="System instructions for the agent")
    # References tools just by function name now
    tool_references: List[str] = Field(default=[], description="List of tool function names (e.g., 'get_weather', 'get_current_time')")
    # env_vars field removed

    @field_validator('name', mode='before')
    @classmethod
    def validate_and_sanitize_name(cls, v):
        """Validates and sanitizes the agent name before standard validation."""
        if not isinstance(v, str):
             # Raise standard ValueError which Pydantic/FastAPI handles
             raise ValueError("Agent name must be a string")
        try:
            sanitized_name = sanitize_agent_name(v)
            # Check if sanitization actually changed the name and log/warn if desired
            # if v != sanitized_name:
            #     print(f"Sanitized agent name from '{v}' to '{sanitized_name}'")
            return sanitized_name
        except ValueError as e:
            # Re-raise the error from sanitize_agent_name
            # Pydantic will wrap this in a ValidationError
            raise ValueError(str(e)) from e

class AgentRead(AgentConfig):
    pass

# --- FastAPI App ---
app = FastAPI(title="ADK Agent & Function Manager API")

# --- AST Helper Functions ---

def read_global_tools_ast():
    """Reads and parses the global tools file into an AST."""
    try:
        with open(GLOBAL_TOOLS_FILE, "r", encoding="utf-8") as f:
            source_code = f.read()
        return ast.parse(source_code)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{GLOBAL_TOOLS_FILE} not found.")
    except SyntaxError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Syntax error in {GLOBAL_TOOLS_FILE}: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read/parse {GLOBAL_TOOLS_FILE}: {e}")

def write_global_tools_ast(tree):
    """Writes the AST back to the global tools file."""
    try:
        new_source_code = ast.unparse(tree) # Requires Python 3.9+
        # Add a newline at the end if missing
        if not new_source_code.endswith('\n'):
            new_source_code += '\n'
        with open(GLOBAL_TOOLS_FILE, "w", encoding="utf-8") as f:
            f.write(new_source_code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to write {GLOBAL_TOOLS_FILE}: {e}")

def find_function_node(tree, func_name):
    """Finds a function definition node by name in the AST."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    return None

def get_function_code(tree, func_name):
    """Extracts the source code of a function from the AST."""
    node = find_function_node(tree, func_name)
    if node:
        return ast.unparse(node)
    return None

# --- Other Helper Functions ---

def get_agent_dir(agent_name: str) -> str:
    """Constructs the full path for an agent directory and validates name."""
    if "/" in agent_name or "\\" in agent_name or "." in agent_name:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid characters in agent name.")
    return os.path.join(MANAGED_AGENTS_DIR, agent_name)

def generate_agent_py_code(config: AgentConfig) -> str:
    """Generates the Python code string for an agent's agent.py file using static imports."""
    import_statement = ""
    tools_list_definition = ""
    agent_tools_arg = ""

    if config.tool_references:
        # Ensure unique tool names
        unique_tools = sorted(list(set(config.tool_references)))
        # Use relative import from agent.py's location (two levels up)
        import_statement = f"from global_tools import {', '.join(unique_tools)}"
        tools_list_definition = f"tools_list = [{', '.join(unique_tools)}]"
        agent_tools_arg = "    tools=tools_list,"

    # Escape triple quotes within the instruction string
    escaped_instruction = config.instruction.replace('"""', '\\"\\"\\"')

    code = f"""\
from google.adk.agents import Agent
{import_statement}

{tools_list_definition}

# Agent definition generated from config
root_agent = Agent(
    name="{config.name}",
    model="{config.model}",
    description="{config.description or ''}",
    instruction=\"\"\"{escaped_instruction}\"\"\",
{agent_tools_arg}
)
"""
    # Ensure final newline
    if not code.endswith("\n"):
        code += "\n"

    # Adjust indentation for agent_tools_arg if present
    if agent_tools_arg:
        code = code.replace("\n)", ",\n)") # Ensure comma before closing parenthesis if tools are last

    # A final clean-up for potential trailing commas before the closing parenthesis if tools were added
    code = code.replace(",\n)", "\n)")

    return code

# (Removed write_agent_env_file function)

def write_agent_init_file(agent_dir: str):
    """
    Writes the __init__.py file for the agent, including code to add the
    project root to sys.path to allow absolute imports from global_tools.py.
    """
    filepath = os.path.join(agent_dir, "__init__.py")
    init_content = """\
import sys
import os

# Calculate the path to the project root directory (adk_kit)
# This __init__.py is assumed to be at <project_root>/managed_agents/<agent_name>/__init__.py
# We need to go up 3 levels from this file's location to get to the project root.
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add the project root to sys.path if it's not already there.
# Inserting at index 0 ensures it's checked first.
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now that the project root is potentially in sys.path, the absolute import
# 'from global_tools import ...' inside agent.py should work.
from . import agent
"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(init_content)
    except IOError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to write __init__.py file: {e}")

def write_agent_py_file(agent_dir: str, config: AgentConfig):
    """Generates and writes the agent.py file."""
    filepath = os.path.join(agent_dir, "agent.py")
    code = generate_agent_py_code(config)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
    except IOError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to write agent.py file: {e}")

def write_agent_config_file(agent_dir: str, config: AgentConfig):
    """Writes the agent configuration to agent_config.json."""
    filepath = os.path.join(agent_dir, "agent_config.json")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(config.model_dump_json(indent=2))
    except IOError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to write agent_config.json: {e}")


# --- Tool Function Management Endpoints ---

@app.post("/tools", status_code=status.HTTP_201_CREATED, response_model=ToolFunction)
async def create_tool_function(tool_func: ToolFunction):
    """
    Adds a new function definition to the global_tools.py file.
    """
    tree = read_global_tools_ast()
    if find_function_node(tree, tool_func.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Function '{tool_func.name}' already exists.")

    try:
        # Parse the new function code into an AST node
        new_func_tree = ast.parse(tool_func.code.strip())
        if not new_func_tree.body or not isinstance(new_func_tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
             raise ValueError("Provided code does not contain a valid function definition.")
        new_func_node = new_func_tree.body[0]
        if new_func_node.name != tool_func.name:
             raise ValueError(f"Function name in code ('{new_func_node.name}') does not match provided name ('{tool_func.name}').")

        # Append the new function node to the body of the module AST
        tree.body.append(new_func_node)
        write_global_tools_ast(tree)
        return tool_func
    except (SyntaxError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid function code provided: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add function: {e}")


@app.get("/tools", response_model=List[str])
async def list_tool_functions():
    """
    Lists the names of all functions defined in the global_tools.py file.
    """
    tree = read_global_tools_ast()
    function_names = [
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    return function_names

@app.get("/tools/{function_name}", response_model=ToolFunction)
async def get_tool_function(function_name: str):
    """
    Retrieves the code definition of a specific function from global_tools.py.
    """
    tree = read_global_tools_ast()
    code = get_function_code(tree, function_name)
    if code is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Function '{function_name}' not found.")
    return ToolFunction(name=function_name, code=code)

@app.put("/tools/{function_name}", response_model=ToolFunction)
async def update_tool_function(function_name: str, tool_func: ToolFunction):
    """
    Updates the code definition of an existing function in global_tools.py.
    The function_name in the path must match the name in the request body.
    """
    if function_name != tool_func.name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Function name in path does not match name in body.")

    tree = read_global_tools_ast()
    existing_node = find_function_node(tree, function_name)
    if existing_node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Function '{function_name}' not found.")

    try:
        # Parse the new function code
        new_func_tree = ast.parse(tool_func.code.strip())
        if not new_func_tree.body or not isinstance(new_func_tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
             raise ValueError("Provided code does not contain a valid function definition.")
        new_func_node = new_func_tree.body[0]
        if new_func_node.name != function_name:
             raise ValueError(f"Function name in code ('{new_func_node.name}') does not match target name ('{function_name}').")

        # Find the index of the old node and replace it
        for i, node in enumerate(tree.body):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                # Preserve original line numbers if possible (though unparse might reset)
                new_func_node.lineno = node.lineno
                new_func_node.col_offset = node.col_offset
                tree.body[i] = new_func_node
                break
        else:
             # Should not happen if find_function_node succeeded, but defensive check
             raise HTTPException(status_code=500, detail="Failed to find node index for replacement.")

        write_global_tools_ast(tree)
        return tool_func
    except (SyntaxError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid function code provided: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update function: {e}")


@app.delete("/tools/{function_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_function(function_name: str):
    """
    Deletes a specific function definition from the global_tools.py file.
    """
    tree = read_global_tools_ast()
    new_body = [
        node for node in tree.body
        if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name)
    ]

    if len(new_body) == len(tree.body): # Check if anything was actually removed
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Function '{function_name}' not found.")

    tree.body = new_body
    write_global_tools_ast(tree)
    return None


# --- Agent Management Endpoints ---
# (Keep create_agent, list_agents, get_agent, update_agent, delete_agent from previous version)
# ... [omitted for brevity - assume they are here] ...
@app.post("/agents", status_code=status.HTTP_201_CREATED, response_model=AgentRead)
async def create_agent(agent_config: AgentConfig):
    """
    Creates a new agent directory, configuration file (agent_config.json),
    .env file, __init__.py, and generates the agent.py file based on the config.
    """
    agent_dir = get_agent_dir(agent_config.name)
    if os.path.exists(agent_dir):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Agent '{agent_config.name}' already exists.")

    try:
        os.makedirs(agent_dir)
        write_agent_config_file(agent_dir, agent_config)
        # Removed call to write_agent_env_file
        write_agent_init_file(agent_dir)
        write_agent_py_file(agent_dir, agent_config)
        return AgentRead(**agent_config.model_dump())
    except Exception as e:
        if os.path.exists(agent_dir):
            shutil.rmtree(agent_dir)
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create agent: {e}")

@app.get("/agents", response_model=List[str])
async def list_agents():
    """
    Lists the names of all agent directories within the managed_agents directory.
    """
    try:
        agents = [d for d in os.listdir(MANAGED_AGENTS_DIR) if os.path.isdir(os.path.join(MANAGED_AGENTS_DIR, d))]
        return agents
    except FileNotFoundError:
        return []
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list agents: {e}")

@app.get("/agents/{agent_name}", response_model=AgentRead)
async def get_agent(agent_name: str):
    """
    Retrieves the configuration of a specific agent by reading its agent_config.json file.
    """
    agent_dir = get_agent_dir(agent_name)
    config_filepath = os.path.join(agent_dir, "agent_config.json")

    if not os.path.exists(agent_dir) or not os.path.exists(config_filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_name}' or its config file not found.")

    try:
        with open(config_filepath, "r", encoding="utf-8") as f:
            config_data = AgentConfig.model_validate_json(f.read())
        if config_data.name != agent_name:
             print(f"Warning: Agent name in config file ('{config_data.name}') does not match directory name ('{agent_name}'). Returning config anyway.")
        return AgentRead(**config_data.model_dump())
    except FileNotFoundError:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent config file not found for '{agent_name}'.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read or parse agent config for '{agent_name}': {e}")

@app.put("/agents/{agent_name}", response_model=AgentRead)
async def update_agent(agent_name: str, agent_config: AgentConfig):
    """
    Updates an existing agent's configuration by overwriting its config, .env,
    and regenerating its agent.py file. The agent_name in the path must match the name in the body.
    """
    if agent_name != agent_config.name:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent name in path does not match name in body.")

    agent_dir = get_agent_dir(agent_name)
    if not os.path.exists(agent_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_name}' not found.")

    try:
        write_agent_config_file(agent_dir, agent_config)
        # Removed call to write_agent_env_file
        write_agent_init_file(agent_dir)
        write_agent_py_file(agent_dir, agent_config)
        return AgentRead(**agent_config.model_dump())
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update agent '{agent_name}': {e}")

@app.delete("/agents/{agent_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_name: str):
    """
    Deletes a specific agent's directory and all its contents.
    """
    agent_dir = get_agent_dir(agent_name)
    if not os.path.exists(agent_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_name}' not found.")

    try:
        shutil.rmtree(agent_dir)
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete agent '{agent_name}': {e}")


# --- Model Listing Endpoint ---

@app.get("/models", response_model=List[str])
async def list_models():
    """
    Returns a list of available models.
    """
    return ["gemini-2.0-flash", "gemini-2.5-pro-preview-03-25"]
