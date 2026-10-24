# Personalized Travel Itinerary Planner

A Streamlit capstone prototype featuring:
- Preference capture for destination/vibe, dates, duration, budget, party, pace, and interests
- Top-three vibe-based destination recommendations
- Day-wise itinerary with time slots, rough cost estimates, and same-day geographic clustering instructions
- Single-slot swap and single-day regeneration
- Session-based trip history, JSON download, and offline PDF export with a travel checklist
- Gemini or Groq API support, plus clearly labelled demonstration mode

## Run locally

Python 3.9+ is the project target; Python 3.10+ is recommended for current dependencies.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Enter a Gemini or Groq API key in the sidebar to enable AI. Without a key, the app uses demonstration recommendations and an illustrative itinerary. API keys are not written to files by the app.

## Deploy to Streamlit Community Cloud

1. Push `app.py`, `requirements.txt`, and `README.md` to a GitHub repository.
2. Create a Streamlit Community Cloud app pointing to `app.py`.
3. Deploy and enter an API key in the sidebar if AI features are needed.
4. Never commit API keys to GitHub. For administrator-managed deployments, use Streamlit Secrets and update the configuration deliberately.

## Important limitations

- Trip history is stored in Streamlit session state only. It is not durable across sessions/restarts and is not a real user account database.
- Destination recommendations are not based on live weather, current prices, bookings, or availability.
- The demo itinerary uses generic placeholders; the AI itinerary may suggest venues, but details must be checked before travel.
- Cost totals simply sum numbers and do not convert mixed currencies. Verify the currency before using a total.
- Geographic clustering is prompted/represented through neighborhood and transport notes; there is no live maps/geocoding/routing integration.
- PDF is generated locally in memory using ReportLab.
- The app is a deployable educational prototype, not a fully production-hardened multi-user SaaS. Authentication, durable persistence, rate limiting, observability, and live travel APIs would be needed for production.
