# VenueFlow AI

![VenueFlow AI Preview](./app/static/venueflow_frontend_verification.webp)

A state-of-the-art, high-performance web application designed to eliminate friction points during large-scale live events. It leverages real-time simulation and Google's Gemini Flash model to create a "smart" venue concierge.

## Features
-   **Multi-Agent AI Concierge:** Features an Orchestrator that routes user queries to specialized Gemini sub-agents (Navigator, Foodie, Safety).
-   **Simulation Engines:** Event Timeline, M/M/c Queueing model, and Crowd Density generator running asynchronously and pushing data via WebSockets.
-   **Stadium Noir UI:** A premium CSS/JS frontend with glassmorphism, 60fps animations, interactive SVG heatmaps, live ticker, and operator dashboard.
-   **Performance-First:** Less than 1MB repository size (no massive node_modules), pure Python/FastAPI backend, and vanilla JS/CSS frontend.

## Prerequisites
-   Python 3.10+
-   Gemini API Key (Get one free at Google AI Studio)

## Quick Start
1.  **Clone down the repository:**
    ```bash
    git clone https://github.com/your-username/venueflow-ai.git
    cd venueflow-ai
    ```
2.  **Create `.env` file and add API key:**
    ```bash
    cp .env.example .env
    # Edit .env and insert your GEMINI_API_KEY
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the application:**
    ```bash
    python run.py
    ```
    The server will start on `http://localhost:8000`.

## Directory Structure
```
venueflow-ai/
├── app/
│   ├── ai/              # Gemini agent prompts & orchestration
│   ├── api/             # REST API routes & WebSocket handler
│   ├── simulation/      # Core logic (Venue, Crowd, Queue, Timeline)
│   ├── static/          # Frontend assets (CSS, JS, SVG)
│   ├── config.py        # Environment variables and settings
│   ├── main.py          # FastAPI application factory
│   └── security.py      # Middleware for rate-limiting, CSP, etc.
├── run.py               # Uvicorn entry point
├── requirements.txt     # Python dependencies
└── .gitignore           # Keeps repository bloat-free
```

## Challenge Alignment
This project addresses the **Physical Event Experience** vertical.
It provides attendees with spatial awareness, personalized AI advice, and waiting duration approximations using advanced crowd & queue engines married with LLMs.

---
*Built for the Google Deepmind challenge.*
