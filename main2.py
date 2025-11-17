
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# ----------------------------------------------------------------------
# KNOWLEDGE BASE (local fallback)
# ----------------------------------------------------------------------
KB = [
    {"id": 1, "tag": "password_reset", "content": "To reset your password, go to Settings > Security > Reset Password."},
    {"id": 2, "tag": "api_issue", "content": "API failures are often due to invalid tokens or rate limits. Regenerate token in Developer Settings."},
    {"id": 3, "tag": "billing", "content": "Invoices are generated on the 1st of each month and downloadable in Billing > Invoices."},
]

# ----------------------------------------------------------------------
# GEMINI API FETCH (NEW)
# ----------------------------------------------------------------------
import requests

GEMINI_API_KEY = "AIzaSyBinl8bQrkM4yUurM5IkGbw2aXgPbFJeZM"   # <--- SET THIS
GEMINI_SEARCH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

# def fetch_from_gemini(query: str):
#     try:
#         payload = {
#             "contents": [{"parts": [{"text": f"Answer this support question strictly based on accurate information: {query}"}]}]
#         }
#         resp = requests.post(
#             GEMINI_SEARCH_URL + f"?key={GEMINI_API_KEY}",
#             json=payload,
#             timeout=15
#         )
#         data = resp.json()
#         if "candidates" in data:
#             return data["candidates"][0]["content"]["parts"][0]["text"]
#         return None
#     except Exception:
#         return None
def fetch_from_gemini(query: str):
    try:
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"You are a customer support AI. Answer ONLY with accurate and concise information for this query: {query}"
                        }
                    ]
                }
            ]
        }

        resp = requests.post(
            GEMINI_SEARCH_URL + f"?key={GEMINI_API_KEY}",
            json=payload,
            timeout=15
        )

        data = resp.json()

        if "candidates" in data:
            cand = data["candidates"][0]
            if "content" in cand and "parts" in cand["content"]:
                return cand["content"]["parts"][0]["text"]

        return None

    except Exception as e:
        print("Gemini API failure:", e)
        return None



# ----------------------------------------------------------------------
KB = [
    {"id": 1, "tag": "password_reset", "content": "To reset your password, go to Settings > Security > Reset Password."},
    {"id": 2, "tag": "api_issue", "content": "API failures are often due to invalid tokens or rate limits. Regenerate token in Developer Settings."},
    {"id": 3, "tag": "billing", "content": "Invoices are generated on the 1st of each month and downloadable in Billing > Invoices."},
]

# ----------------------------------------------------------------------
# PERSONA DETECTION (rule-based demo)
# ----------------------------------------------------------------------
def detect_tone(message: str):
    message = message.lower()
    if any(w in message for w in ["angry", "not working", "stupid", "hate", "wtf", "frustrated"]):
        return "frustrated"
    if any(w in message for w in ["?", "how", "help", "issue"]):
        return "confused"
    return "neutral"


def detect_expertise(message: str):
    msg = message.lower()
    if any(w in msg for w in ["api", "token", "server", "debug", "cli"]):
        return "technical"
    if any(w in msg for w in ["strategy", "roi", "kpi", "executive"]):
        return "business"
    return "beginner"


def detect_urgency(message: str):
    msg = message.lower()
    if any(w in msg for w in ["urgent", "asap", "immediately", "critical"]):
        return "high"
    return "normal"


def detect_customer_tier(message: str):
    msg = message.lower()
    if "vip" in msg:
        return "VIP"
    if "premium" in msg:
        return "premium"
    return "basic"

# ----------------------------------------------------------------------
# KB Retrieval
# ----------------------------------------------------------------------
def retrieve_kb(message: str):
    msg = message.lower()
    # Improved keyword scoring for better KB match
    best_item = None
    best_score = 0
    for item in KB:
        score = 0
        text = (item["content"] + " " + item["tag"]).lower()
        for word in msg.split():
            if word in text:
                score += 1
        if score > best_score:
            best_score = score
            best_item = item
    return best_item

# ----------------------------------------------------------------------
# Response Generator
# ----------------------------------------------------------------------
def generate_response(message: str):
    tone = detect_tone(message)
    expertise = detect_expertise(message)
    urgency = detect_urgency(message)
    tier = detect_customer_tier(message)
    kb_item = retrieve_kb(message)

    # Escalate rules
    if tone == "frustrated" and urgency == "high":
        return {
            "reply": "I'm escalating this to a human support specialist immediately. Please stay online.",
            "escalate": True,
            "context": {
                "user_message": message,
                "tone": tone,
                "expertise": expertise,
                "urgency": urgency,
                "tier": tier,
            }
        }

    # Tone adaptation
    if tone == "frustrated":
        prefix = "I’m really sorry you're experiencing this. Let me help you right away. "
    elif tone == "confused":
        prefix = "Sure, I can guide you. "
    else:
        prefix = "Happy to assist! "

    # Expertise adaptation
    if expertise == "technical":
        style = "Here’s the technical detail you might need: "
    elif expertise == "business":
        style = "Let me give you a concise executive-level summary: "
    else:
        style = "Here’s a simple explanation: "

    # KB content
  # Try Gemini if KB didn't match
    gemini_answer = fetch_from_gemini(message)

    if gemini_answer:
        kb_text = gemini_answer
    elif kb_item:
        kb_text = kb_item["content"]
    else:
        kb_text = "I couldn't find an exact match, please give me more details."


    return {
        "reply": prefix + style + kb_text,
        "escalate": False,
        "context": {
            "tone": tone,
            "expertise": expertise,
            "urgency": urgency,
            "tier": tier,
        }
    }

# ----------------------------------------------------------------------
# API Endpoint
# ----------------------------------------------------------------------
class Query(BaseModel):
    message: str

@app.post("/ask")
def ask(query: Query):
    return generate_response(query.message)

# ----------------------------------------------------------------------
# FRONTEND UI
@app.get("/", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <head>
    <script src='https://www.noupe.com/embed/019a916eb87c7edd8cf04e686511dc2ac656.js'></script>
        <title>Persona-Adaptive Support Agent</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', sans-serif;
                background: var(--bg);
                color: var(--text);
                transition: background 0.3s, color 0.3s;
            }

            :root {
                --bg: #f5f5f5;
                --text: #222;
                --card-bg: rgba(255,255,255,0.85);
                --border: #ddd;
                --button-bg: #4CAF50;
                --button-text: white;
            }

            .dark {
                --bg: #101418;
                --text: #f2f2f2;
                --card-bg: rgba(30, 35, 40, 0.85);
                --border: #555;
                --button-bg: #66bb6a;
                --button-text: #000;
            }

            .container {
                max-width: 700px;
                margin: 40px auto;
                padding: 30px;
                background: var(--card-bg);
                backdrop-filter: blur(12px);
                border-radius: 16px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                border: 1px solid var(--border);
            }

            h2 {
                text-align: center;
                margin-bottom: 20px;
                font-weight: 700;
            }

            textarea {
                width: 100%;
                padding: 14px;
                border-radius: 10px;
                border: 1px solid var(--border);
                font-size: 16px;
                background: var(--bg);
                color: var(--text);
            }

            button {
                margin-top: 15px;
                width: 100%;
                padding: 14px;
                background: var(--button-bg);
                color: var(--button-text);
                border: none;
                border-radius: 10px;
                cursor: pointer;
                font-size: 17px;
                font-weight: bold;
                transition: 0.2s;
            }

            button:hover {
                opacity: 0.9;
                transform: scale(1.02);
            }

            #responseBox {
                margin-top: 25px;
                padding: 20px;
                border-left: 5px solid #2196F3;
                background: rgba(33,150,243,0.10);
                border-radius: 10px;
                display: none;
                animation: fadeIn 0.4s ease-in-out;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .toggle-btn {
                position: absolute;
                top: 20px;
                right: 20px;
                padding: 10px 18px;
                border-radius: 20px;
                background: var(--card-bg);
                cursor: pointer;
                border: 1px solid var(--border);
                font-weight: bold;
            }
        </style>
    </head>

    <body>
        <div class="toggle-btn" onclick="toggleMode()">🌙 Dark / ☀ Light</div>

        <div class="container">
            <h2>Persona-Adaptive Customer Support Agent</h2>

            <label>Your Message:</label>
            <textarea id="msg" rows="5"></textarea>

            <button onclick="send()">Ask Agent</button>

            <div id="responseBox"></div>
        </div>

        <script>
            function toggleMode() {
                document.body.classList.toggle('dark');
            }

            async function send() {
                const msg = document.getElementById('msg').value;

                const res = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg })
                });

                const data = await res.json();

                let html = `
                    <strong>💬 Agent Response:</strong><br>${data.reply}<br><br>
                    <strong>🧠 Persona Detection:</strong><br>
                    • Tone: ${data.context.tone}<br>
                    • Expertise: ${data.context.expertise}<br>
                    • Urgency: ${data.context.urgency}<br>
                    • Tier: ${data.context.tier}<br>
                `;

                if (data.escalate) {
                    html += `<br><strong style='color:red'>⚠ Escalation triggered → A human agent will join shortly.</strong>`;
                }

                const box = document.getElementById('responseBox');
                box.innerHTML = html;
                box.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    uvicorn.run("persona_support_agent:app", host="0.0.0.0", port=8000, reload=True)
