#!/bin/bash

# --- Configuration ---
RUN_STREAMLIT=false

# --- Argument Parsing ---
# Simple loop to check for the --streamlit flag
for arg in "$@"
do
    if [ "$arg" == "--streamlit" ]
    then
        RUN_STREAMLIT=true
        # Optional: remove the flag from arguments if passing them down later
        # shift
    fi
done

# --- Start Servers ---

# Start the ADK API server (port 8000) in the managed_agents directory in the background
echo "Starting ADK API server (localhost:8000)..."
(cd managed_agents && adk web &)
ADK_PID=$! # Store PID

# Start the API wrapper server (port 8001) in the current directory in the background
echo "Starting API wrapper server (localhost:8001)..."
uvicorn main:app --reload --host 0.0.0.0 --port 8001 &
WRAPPER_PID=$! # Store PID

# --- Conditionally Start Streamlit ---
if [ "$RUN_STREAMLIT" = true ] ; then
    echo "Starting Streamlit UI (localhost:8501)..."
    streamlit run streamlit_app.py &
    STREAMLIT_PID=$! # Store PID
    echo "All three servers started in the background."
else
    echo "ADK and Wrapper servers started in the background."
    echo "Run with --streamlit flag to also start the UI."
fi

# --- Wait for processes ---
# Wait for all background jobs started by this script to finish
# This allows Ctrl+C to terminate them gracefully (usually)
wait
