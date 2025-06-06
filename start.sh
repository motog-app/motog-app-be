#!/bin/bash
# Start the FastAPI app using uvicorn
uvicorn app.main:app --host=0.0.0.0 --port=8000