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
