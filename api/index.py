"""
Vercel Entrance Port
Bridges the FastAPI application with Vercel's serverless environment.
"""
import os
import sys

# Add the project root to path so we can import 'app'
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

# Vercel needs the 'app' variable to be exposed
# No changes needed to local app.main logic
