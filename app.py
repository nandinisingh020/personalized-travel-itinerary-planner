import json
import os
import re
import io
from datetime import date, timedelta, datetime
from collections import defaultdict

import streamlit as st

APP_TITLE = "Personalized Travel Itinerary Planner"
st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide")

st.markdown("""
<style>
.block-container {max-width:1440px;padding-top:1.4rem;padding-bottom:2.5rem;}
.hero {padding:1.6rem 1.8rem;border-radius:20px;color:#fff;background:linear-gradient(120deg,#123b36,#1f766e 55%,#e0a458);margin-bottom:1rem;}
.hero h1 {margin:0 0 .45rem 0;font-size:2.1rem;}
.hero p {margin:0;opacity:.92;}
div[data-testid="stMetric"] {border:1px solid #e5e7eb;border-radius:14px;padding:12px;background:white;}
.pill {display:inline-block;border-radius:999px;padding:.25rem .65rem;background:#e8f5f1;color:#155e52;font-size:.82rem;font-weight:650;margin:.12rem;}
.note {color:#667085;font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

# -------- Helpers --------
def safe_json(raw):
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip(), flags=re.I)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("AI response did not contain a JSON object.")
    return json.loads(raw[start:end + 1])

def ai_json(api_provider, api_key, prompt):
    if api_provider == "Gemini":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.45)
        )
        return safe_json(response.text)
    if api_provider == "Groq":
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Return only valid JSON. Be honest about uncertainty and avoid inventing live opening hours or current prices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.45,
            response_format={"type": "json_object"}
        )
        return safe_json(response.choices[0].message.content)
    raise ValueError("Choose Gemini or Groq.")

def money(amount, currency="INR"):
    symbols = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    return f"{symbols.get(currency, currency + ' ')}{amount:,.0f}"

def get_demo_recommendations(prefs):
    mood = prefs["vibe"]
    if mood == "Beach":
        return [
            {"city":"Goa, India","tags":["Beach","Food","Nightlife"],"why":"Beach time, seafood, markets, and a lively evening scene.","best_for":"Couples and friends","budget_fit":"Budget to moderate"},
            {"city":"Da Nang, Vietnam","tags":["Beach","Adventure","Food"],"why":"Coastline, day trips, and approachable food experiences.","best_for":"Adventure and relaxed trips","budget_fit":"Budget to moderate"},
            {"city":"Phuket, Thailand","tags":["Beach","Nightlife","Adventure"],"why":"Island excursions, beaches, and a wide range of stays.","best_for":"Friends and couples","budget_fit":"Moderate"}
        ]
    if mood == "Mountains":
        return [
            {"city":"Manali, India","tags":["Mountains","Adventure","Relaxed"],"why":"Mountain scenery, cafés, and outdoor excursions.","best_for":"Friends and couples","budget_fit":"Budget to moderate"},
            {"city":"Kathmandu, Nepal","tags":["Culture","Mountains","History"],"why":"Heritage sites with access to Himalayan viewpoints and hikes.","best_for":"Culture and adventure","budget_fit":"Budget to moderate"},
            {"city":"Tbilisi, Georgia","tags":["Mountains","Food","Culture"],"why":"Old-town streets, food, and mountain day-trip options.","best_for":"Food and culture","budget_fit":"Moderate"}
        ]
    if mood == "Cultural":
        return [
            {"city":"Jaipur, India","tags":["History","Architecture","Food"],"why":"Forts, palaces, craft markets, and Rajasthani cuisine.","best_for":"Families and history lovers","budget_fit":"Budget to moderate"},
            {"city":"Kyoto, Japan","tags":["Temples","Tradition","Food"],"why":"Historic districts, gardens, temples, and seasonal culture.","best_for":"Culture-focused trips","budget_fit":"Moderate to luxury"},
            {"city":"Istanbul, Türkiye","tags":["History","Food","Markets"],"why":"Historic landmarks, bazaars, and distinctive food culture.","best_for":"History and food","budget_fit":"Moderate"}
        ]
    return [
        {"city":"Singapore","tags":["Urban","Food","Family"],"why":"Efficient city transport, gardens, museums, and varied dining.","best_for":"Families and first-time city trips","budget_fit":"Moderate to luxury"},
        {"city":"Kuala Lumpur, Malaysia","tags":["Urban","Food","Shopping"],"why":"Food neighborhoods, city views, shopping, and cultural sites.","best_for":"Friends and food lovers","budget_fit":"Budget to moderate"},
        {"city":"Lisbon, Portugal","tags":["Urban","History","Food"],"why":"Walkable historic areas, viewpoints, and cafés.","best_for":"Couples and relaxed explorers","budget_fit":"Moderate"}
    ]

def demo_itinerary(prefs):
    destination = prefs["destination"].strip() or get_demo_recommendations(prefs)[0]["city"]
    days = prefs["days"]
    interests = prefs["interests"]
    budget_factor = {"Budget": 0.75, "Moderate": 1.0, "Luxury": 1.8}[prefs["budget"]]
    activity_pool = [
        ("Morning Sightseeing", "Explore a well-known landmark or historic district", 450, "History"),
        ("Lunch Recommendation", "Try a popular local restaurant or food market", 500, "Food"),
        ("Afternoon Leisure", "Visit a garden, waterfront, museum, or neighborhood", 350, "Culture"),
        ("Evening Dining & Entertainment", "Enjoy a local dinner area and relaxed evening walk", 800, "Nightlife")
    ]
    plan = []
    for day_num in range(1, days + 1):
        # Repeatable generic structure; destinations and opening hours should be verified.
        slots = []
        for idx, (slot, activity, cost, tag) in enumerate(activity_pool):
            slots.append({
                "time": ["09:00–12:00", "12:30–14:00", "14:30–17:00", "18:30–21:00"][idx],
                "slot": slot,
                "activity": activity if not interests or tag in interests else f"{activity} (adapt to your interest: {', '.join(interests)})",
                "area": f"Suggested nearby area for day {day_num}",
                "estimated_cost": round(cost * budget_factor),
                "currency": "INR",
                "transport_note": "Group stops in one neighborhood where possible; verify route and travel time before leaving."
            })
        plan.append({"day": day_num, "theme": f"Day {day_num}: Explore {destination}", "items": slots})
    return {
        "destination": destination,
        "currency": "INR",
        "days": plan,
        "notes": "Demonstration itinerary with illustrative activities and costs. Venue names, routes, opening hours, and prices are not live-verified."
    }

def make_pdf(trip):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TripTitle", parent=styles["Title"], textColor=colors.HexColor("#155e52"), alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="DayHead", parent=styles["Heading2"], textColor=colors.HexColor("#155e52"), spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], fontSize=8, textColor=colors.HexColor("#667085"), leading=10))
    story = [
        Paragraph("✦ Personalized Travel Guide ✦", styles["TripTitle"]),
        Paragraph(f"<b>Destination:</b> {trip.get('destination','—')}", styles["BodyText"]),
        Paragraph(f"<b>Dates:</b> {trip.get('start_date','Flexible')} · <b>Party:</b> {trip.get('party','—')} · <b>Budget:</b> {trip.get('budget','—')}", styles["BodyText"]),
        Spacer(1, 8),
    ]
    for day in trip.get("itinerary", {}).get("days", []):
        story.append(Paragraph(day.get("theme", f"Day {day.get('day','')}"), styles["DayHead"]))
        rows = [["Time", "Plan", "Area / route note", "Est. cost"]]
        for item in day.get("items", []):
            activity = str(item.get("activity", "")).replace("&", "&amp;")
            area = str(item.get("area", "")).replace("&", "&amp;")
            rows.append([
                item.get("time", ""),
                f"<b>{item.get('slot','')}</b><br/>{activity}",
                area,
                money(float(item.get("estimated_cost", 0)), item.get("currency", "INR"))
            ])
        table = Table(rows, colWidths=[25*mm, 70*mm, 53*mm, 25*mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#155e52")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#d0d5dd")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f6faf9")]),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.extend([table, Spacer(1, 6)])
    story.extend([
        Spacer(1, 10),
        Paragraph("Travel checklist", styles["DayHead"]),
        Paragraph("□ Passport / government ID and visa requirements checked<br/>□ Accommodation and transport confirmations saved offline<br/>□ Travel insurance and emergency contacts saved<br/>□ Prescribed medicines and basic first-aid items packed<br/>□ Local emergency number and nearest hospital identified<br/>□ Weather forecast and venue opening hours checked before departure", styles["BodyText"]),
        Spacer(1, 8),
        Paragraph("Costs, travel times, venue details, and route suggestions are estimates. Confirm all details with official providers before travel.", styles["SmallNote"])
    ])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -------- Sidebar --------
with st.sidebar:
    st.title("🧭 Trip Studio")
    st.caption("Skill Wallet Capstone · Project 4")
    provider = st.selectbox("AI provider", ["Gemini", "Groq"])
    api_key = st.text_input(f"{provider} API key", type="password", help="Kept in session memory; do not paste keys into shared screenshots.")
    st.info("Demo mode is active." if not api_key.strip() else f"{provider} mode selected.")
    st.markdown("---")
    st.markdown("**Architecture**")
    st.caption("Streamlit UI → LLM JSON → itinerary state → PDF export")
    st.caption("Trips are saved in session memory; no database required.")

st.markdown("""
<div class="hero">
<h1>🧭 Personalized Travel Itinerary Planner</h1>
<p>Plan by destination, budget, and vibe — then customize each day and export a portable travel guide.</p>
</div>
""", unsafe_allow_html=True)

# -------- Preferences --------
st.subheader("Trip preferences")
with st.form("trip_preferences"):
    c1, c2, c3 = st.columns(3)
    with c1:
        destination = st.text_input("Destination (optional)", placeholder="e.g., Kyoto, Japan")
        vibe = st.selectbox("Travel vibe", ["Beach", "Mountains", "Cultural", "Urban"])
        days = st.number_input("Trip duration (days)", min_value=1, max_value=21, value=4)
    with c2:
        start_date = st.date_input("Start date", value=date.today() + timedelta(days=30))
        budget = st.selectbox("Budget level", ["Budget", "Moderate", "Luxury"], index=1)
        party = st.selectbox("Travel party", ["Solo", "Couple", "Family", "Friends"])
    with c3:
        pace = st.selectbox("Pace", ["Relaxed", "Moderate", "Fast-Paced"], index=1)
        interests = st.multiselect("Interests", ["Food", "Adventure", "History", "Nightlife", "Nature", "Shopping", "Art", "Wellness"], default=["Food", "History"])
        notes = st.text_input("Extra preferences", placeholder="e.g., vegetarian food, avoid stairs")
    submitted = st.form_submit_button("Save preferences", type="primary")

if "prefs" not in st.session_state:
    st.session_state.prefs = {
        "destination": "", "vibe": "Cultural", "days": 4, "start_date": str(date.today() + timedelta(days=30)),
        "budget": "Moderate", "party": "Couple", "pace": "Moderate", "interests": ["Food", "History"], "notes": ""
    }
if submitted:
    st.session_state.prefs = {
        "destination": destination.strip(), "vibe": vibe, "days": int(days), "start_date": str(start_date),
        "budget": budget, "party": party, "pace": pace, "interests": interests, "notes": notes
    }
    st.success("Preferences saved for this session.")

prefs = st.session_state.prefs
tabs = st.tabs(["1 · Destination Recommender", "2 · Optimized Itinerary", "3 · Customize & Swap", "4 · Trip History & PDF"])

# -------- Tab 1 --------
with tabs[0]:
    st.subheader("Find a destination that fits your vibe")
    if prefs["destination"]:
        st.info(f"You entered **{prefs['destination']}**. Clear the destination field and save preferences to explore open-ended recommendations.")
    if st.button("Recommend top 3 destinations", type="primary", key="recommend"):
        prompt = f"""Recommend exactly 3 destination cities for a traveler. Return JSON:
{{"recommendations":[{{"city":"", "tags":[""], "why":"", "best_for":"", "budget_fit":""}}]}}
Preferences: vibe={prefs['vibe']}, days={prefs['days']}, start_date={prefs['start_date']}, budget={prefs['budget']}, party={prefs['party']}, pace={prefs['pace']}, interests={prefs['interests']}, extra={prefs['notes']}.
Consider typical seasonality for the date, affordability, and mood. Do not claim live weather. Be concise and avoid unsupported safety claims."""
        try:
            if api_key.strip():
                recommendations = ai_json(provider, api_key.strip(), prompt).get("recommendations", [])
                if not recommendations:
                    raise ValueError("No recommendations returned.")
            else:
                recommendations = get_demo_recommendations(prefs)
            st.session_state["recommendations"] = recommendations[:3]
            st.session_state["recommendations_demo"] = not bool(api_key.strip())
        except Exception as exc:
            st.warning(f"Could not generate AI recommendations ({exc}). Showing demonstration suggestions.")
            st.session_state["recommendations"] = get_demo_recommendations(prefs)
            st.session_state["recommendations_demo"] = True
    recs = st.session_state.get("recommendations", [])
    if st.session_state.get("recommendations_demo") and recs:
        st.caption("Demonstration suggestions; not based on live weather, current prices, or availability.")
    if recs:
        cols = st.columns(3)
        for i, rec in enumerate(recs):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"### {rec.get('city','Destination')}")
                    for tag in rec.get("tags", []):
                        st.markdown(f'<span class="pill">{tag}</span>', unsafe_allow_html=True)
                    st.write(rec.get("why", "A possible match for your preferences."))
                    st.caption(f"Best for: {rec.get('best_for','—')}")
                    st.caption(f"Budget fit: {rec.get('budget_fit','—')}")
                    if st.button("Use this destination", key=f"use_dest_{i}"):
                        st.session_state.prefs["destination"] = rec.get("city", "")
                        st.success(f"Selected {rec.get('city','destination')}. Open the itinerary tab to generate a plan.")

# -------- Tab 2 --------
with tabs[1]:
    st.subheader("Generate a day-by-day itinerary")
    st.write("The planner groups stops by area where possible. Verify routes and venue details before traveling.")
    if st.button("Generate itinerary", type="primary", key="generate_plan"):
        dest = prefs["destination"] or get_demo_recommendations(prefs)[0]["city"]
        prompt = f"""Create a practical day-by-day itinerary and return ONLY JSON:
{{"destination":"", "currency":"INR", "days":[{{"day":1,"theme":"","items":[{{"time":"09:00-12:00","slot":"Morning Sightseeing","activity":"","area":"","estimated_cost":0,"currency":"INR","transport_note":""}}]}}], "notes":""}}
Make exactly {prefs['days']} days. Each day must have sequential slots: Morning Sightseeing, Lunch Recommendation, Afternoon Leisure, Evening Dining & Entertainment. Keep same-day activities geographically close and avoid backtracking. Use realistic broad cost estimates in the destination's local currency if known; include currency code for each item. Do not invent precise opening hours, current availability, or live transit times. State when venue names are suggestions requiring verification.
Traveler preferences: destination={dest}, vibe={prefs['vibe']}, dates={prefs['start_date']} for {prefs['days']} days, budget={prefs['budget']}, party={prefs['party']}, pace={prefs['pace']}, interests={prefs['interests']}, extra={prefs['notes']}.
Respect the requested pace and interests. Prefer accessible, sensible activities."""
        try:
            if api_key.strip():
                itinerary = ai_json(provider, api_key.strip(), prompt)
                if not itinerary.get("days"):
                    raise ValueError("AI response did not contain itinerary days.")
                demo = False
            else:
                itinerary, demo = demo_itinerary(prefs), True
            st.session_state["current_itinerary"] = itinerary
            st.session_state["current_trip_meta"] = {
                "destination": itinerary.get("destination", dest), "start_date": prefs["start_date"],
                "party": prefs["party"], "budget": prefs["budget"], "pace": prefs["pace"],
                "vibe": prefs["vibe"], "days_count": prefs["days"], "interests": prefs["interests"],
                "notes": prefs["notes"]
            }
            st.session_state["itinerary_demo"] = demo
        except Exception as exc:
            st.warning(f"AI itinerary failed ({exc}). Using a demonstration itinerary.")
            st.session_state["current_itinerary"] = demo_itinerary(prefs)
            st.session_state["current_trip_meta"] = {
                "destination": prefs["destination"] or get_demo_recommendations(prefs)[0]["city"],
                "start_date": prefs["start_date"], "party": prefs["party"], "budget": prefs["budget"],
                "pace": prefs["pace"], "vibe": prefs["vibe"], "days_count": prefs["days"],
                "interests": prefs["interests"], "notes": prefs["notes"]
            }
            st.session_state["itinerary_demo"] = True
    itinerary = st.session_state.get("current_itinerary")
    if itinerary:
        if st.session_state.get("itinerary_demo"):
            st.warning("Demonstration itinerary — activities and costs are illustrative, not live-verified.")
        all_costs = [float(item.get("estimated_cost", 0) or 0) for day in itinerary.get("days", []) for item in day.get("items", [])]
        total = sum(all_costs)
        a, b, c = st.columns(3)
        a.metric("Destination", itinerary.get("destination", "—"))
        b.metric("Planned days", len(itinerary.get("days", [])))
        c.metric("Activity cost estimate", f"{itinerary.get('currency','INR')} {total:,.0f}", help="Simple sum; mixed currencies are not converted.")
        cumulative = 0
        for day in itinerary.get("days", []):
            st.markdown(f"### {day.get('theme', 'Day ' + str(day.get('day','')))}")
            for item in day.get("items", []):
                cost = float(item.get("estimated_cost", 0) or 0)
                cumulative += cost
                with st.container(border=True):
                    st.markdown(f"**{item.get('time','')} · {item.get('slot','Activity')}**")
                    st.write(item.get("activity", "Activity"))
                    st.caption(f"Area: {item.get('area','Verify area')} · Est. cost: {money(cost, item.get('currency', itinerary.get('currency','INR')))}")
                    if item.get("transport_note"):
                        st.caption(item["transport_note"])
            st.caption(f"Running cumulative estimate (same numeric currency only): {itinerary.get('currency','INR')} {cumulative:,.0f}")
        if itinerary.get("notes"):
            st.info(itinerary["notes"])

# -------- Tab 3 --------
with tabs[2]:
    st.subheader("Customize a slot or regenerate one day")
    itinerary = st.session_state.get("current_itinerary")
    if not itinerary or not itinerary.get("days"):
        st.info("Generate an itinerary first in Tab 2.")
    else:
        day_options = [int(d.get("day", i + 1)) for i, d in enumerate(itinerary["days"])]
        selected_day = st.selectbox("Choose a day", day_options)
        day_obj = next((d for i, d in enumerate(itinerary["days"]) if int(d.get("day", i+1)) == selected_day), itinerary["days"][0])
        item_options = [f"{i+1}. {item.get('slot','Activity')} — {item.get('activity','')[:45]}" for i, item in enumerate(day_obj.get("items", []))]
        selected_item_label = st.selectbox("Choose a time slot", item_options)
        item_idx = item_options.index(selected_item_label) if item_options else 0
        current_item = day_obj.get("items", [])[item_idx] if day_obj.get("items") else {}
        st.write("Current activity:", current_item.get("activity", "—"))
        change_request = st.text_input("What would you like instead?", placeholder="e.g., replace museum with outdoor market; vegetarian lunch")
        left, right = st.columns(2)
        with left:
            if st.button("Swap selected activity", type="primary", key="swap_activity"):
                if not change_request.strip():
                    st.warning("Describe the change you want first.")
                elif api_key.strip():
                    prompt = f"""Return JSON with one key "item" containing an updated itinerary item with keys time, slot, activity, area, estimated_cost, currency, transport_note.
Destination: {itinerary.get('destination')}; selected day: {selected_day}; current item: {json.dumps(current_item)}; requested change: {change_request}.
Keep the same time slot and day. Respect local context and budget. Do not invent live availability or exact opening hours."""
                    try:
                        updated = ai_json(provider, api_key.strip(), prompt).get("item")
                        if not updated:
                            raise ValueError("No replacement item returned.")
                        day_obj["items"][item_idx] = updated
                        st.session_state["current_itinerary"] = itinerary
                        st.success("Selected activity updated; the rest of the itinerary was preserved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not swap with AI: {exc}")
                else:
                    current_item["activity"] = f"{change_request.strip()} (demonstration swap — verify local options)"
                    current_item["transport_note"] = "Replacement is a placeholder; verify location, route, opening hours, and price."
                    st.session_state["current_itinerary"] = itinerary
                    st.success("Updated this slot only. Other days and slots were preserved.")
                    st.rerun()
        with right:
            if st.button("Regenerate this day only", key="regen_day"):
                if api_key.strip():
                    prompt = f"""Return JSON with key "day" containing a day object with day, theme, items. Generate exactly 4 sequential slots (Morning Sightseeing, Lunch Recommendation, Afternoon Leisure, Evening Dining & Entertainment) for day {selected_day} of a trip to {itinerary.get('destination')}. Current day: {json.dumps(day_obj)}. Preferences: {json.dumps(prefs)}. Group nearby locations, avoid backtracking, include cost/currency and transport_note. No live availability claims."""
                    try:
                        new_day = ai_json(provider, api_key.strip(), prompt).get("day")
                        if not new_day or not new_day.get("items"):
                            raise ValueError("No day returned.")
                        new_day["day"] = selected_day
                        idx = next(i for i, d in enumerate(itinerary["days"]) if int(d.get("day", i+1)) == selected_day)
                        itinerary["days"][idx] = new_day
                        st.session_state["current_itinerary"] = itinerary
                        st.success(f"Day {selected_day} regenerated; all other days were preserved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not regenerate day: {exc}")
                else:
                    day_obj["theme"] = f"Day {selected_day}: {itinerary.get('destination','Explore')} at your own pace"
                    for item in day_obj.get("items", []):
                        item["transport_note"] = "Demonstration refresh: cluster nearby stops and verify routes locally."
                    st.session_state["current_itinerary"] = itinerary
                    st.success(f"Day {selected_day} refreshed in demonstration mode; other days were preserved.")
                    st.rerun()

# -------- Tab 4 --------
with tabs[3]:
    st.subheader("Trip history & offline PDF export")
    st.write("Save trips in this browser session, then download a portable PDF guide.")
    itinerary = st.session_state.get("current_itinerary")
    meta = st.session_state.get("current_trip_meta", {})
    if itinerary:
        if st.button("Save current trip to history", type="primary", key="save_trip"):
            trip = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "destination": meta.get("destination", itinerary.get("destination", "Trip")),
                "start_date": meta.get("start_date", "Flexible"),
                "party": meta.get("party", "—"), "budget": meta.get("budget", "—"),
                "pace": meta.get("pace", "—"), "vibe": meta.get("vibe", "—"),
                "itinerary": itinerary
            }
            if "trip_history" not in st.session_state:
                st.session_state.trip_history = []
            st.session_state.trip_history.insert(0, trip)
            st.success("Trip saved to session history.")
        try:
            pdf_bytes = make_pdf({
                **meta,
                "destination": meta.get("destination", itinerary.get("destination", "Trip")),
                "itinerary": itinerary
            })
            st.download_button("Download current itinerary PDF", data=pdf_bytes,
                               file_name="personalized_travel_guide.pdf", mime="application/pdf")
        except Exception as exc:
            st.error(f"PDF export failed: {exc}")
        st.download_button("Download itinerary JSON", json.dumps(itinerary, indent=2, ensure_ascii=False),
                           file_name="travel_itinerary.json", mime="application/json")
    else:
        st.info("Generate an itinerary before saving or exporting.")
    history = st.session_state.get("trip_history", [])
    st.markdown("#### Saved trips in this session")
    if history:
        for trip in history:
            with st.container(border=True):
                st.markdown(f"**{trip['destination']}**")
                st.caption(f"Saved {trip['saved_at']} · {trip['start_date']} · {trip['party']} · {trip['budget']}")
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if st.button("Load trip", key=f"load_{trip['id']}"):
                        st.session_state["current_itinerary"] = trip["itinerary"]
                        st.session_state["current_trip_meta"] = {k: trip.get(k) for k in ["destination", "start_date", "party", "budget", "pace", "vibe"]}
                        st.success("Trip loaded. Open the itinerary or customization tab.")
                with col_b:
                    try:
                        pdf = make_pdf(trip)
                        st.download_button("Download this trip PDF", data=pdf, file_name=f"travel_guide_{trip['id']}.pdf",
                                           mime="application/pdf", key=f"pdf_{trip['id']}")
                    except Exception as exc:
                        st.caption(f"PDF unavailable: {exc}")
    else:
        st.caption("No trips saved yet. Session history clears when the app session resets.")

st.markdown("---")
st.markdown('<p class="note">Prototype note: Demo suggestions, itinerary items, and costs are illustrative. Confirm visas, safety guidance, venue hours, transport, weather, and prices with official/current sources before booking.</p>', unsafe_allow_html=True)
