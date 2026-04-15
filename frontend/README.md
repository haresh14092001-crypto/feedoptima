# FeedOptima Frontend Preview

This is a simple web frontend for the FeedOptima livestock ration optimization API.

## How to Preview

1. **Start the Backend API first:**
   - Open a terminal in the `backend` folder
   - Run: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
   - Or use the provided start script if available

2. **Open the Frontend:**
   - Open `frontend/index.html` directly in your web browser
   - Or serve it with a local server (recommended for better compatibility):
     - `cd frontend`
     - `python -m http.server 3000` (or any port)
     - Open `http://localhost:3000` in browser

3. **Use the App:**
   - Fill in the animal details
   - Click "Optimize Ration" to get feed recommendations
   - Check "Include AI Explanation" for farmer-friendly advice
   - Click "Load Feed Catalog" to see available ingredients

## Features

- **Ration Optimization**: Calculate optimal feed mixtures based on animal requirements
- **AI Explanations**: Get simplified explanations for farmers
- **Feed Catalog**: Browse available feed ingredients and prices
- **Responsive Design**: Works on desktop and mobile

## API Requirements

The frontend expects the backend API to be running on `http://localhost:8000`. Make sure CORS is enabled in the backend for local development.

## Files

- `index.html` - Main HTML structure
- `styles.css` - Styling and layout
- `script.js` - JavaScript for API calls and UI interactions