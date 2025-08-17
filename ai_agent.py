#Visualization & Chat GPT file fixed
import os
import requests
import base64
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import mimetypes

load_dotenv()
PRELOADED_FILE_PATH = os.path.join('HR Department Report.pdf')

# Create the Flask application
app = Flask(__name__)

# --- CONFIGURATION ---
#API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# This system instruction tells Gemini how to format data for Chart.js
SYSTEM_INSTRUCTION = """
You are a helpful and conversational AI assistant. Your primary role is to answer questions and engage in conversation. A document may be preloaded as context, and you should use it to answer questions when they relate to the document's content.
A document has been preloaded as your primary source of information. Your main task is to answer any questions based on the contents of this document.

You also have a special skill for data visualization.
If, and only if, the user explicitly asks you to **create, make, draw, or plot a chart or graph**, then your response MUST be a single, valid JSON object with two keys: "analysis" and "chart".

1.  "analysis": A string containing a brief, insightful summary or analysis of the data from the document.
2.  "chart": The Chart.js JSON object, which MUST have 'type', 'data', and 'options' keys.
    - For the title, use the 'plugins' key: "options": { "plugins": { "title": { "display": true, "text": "Chart Title" } } }
    - For scales, use the modern object format: "scales": { "y": { "beginAtZero": true } }

Example of a valid chart request: "Plot a bar chart of the sales figures from the document"
Example of a valid JSON response:
{
  "analysis": "Based on the data in the document, Bananas are the top-selling fruit, outperforming Apples by 50%.",
  "chart": {
    "type": "bar",
    "data": {
      "labels": ["Apples", "Bananas"],
      "datasets": [{
        "label": "Fruit Sales",
        "data": [50, 75],
        "backgroundColor": ["rgba(255, 99, 132, 0.5)", "rgba(54, 162, 235, 0.5)"]
      }]
    },
    "options": {
      "responsive": true,
      "plugins": { "title": { "display": true, "text": "Fruit Sales Data" } }
    }
  }
}
For ALL other questions or request, including general conversation or questions about the document that do not require a visual chart, you MUST respond in plain text using markdown for formatting. Do not default to creating a chart unless specifically asked.
"""

# --- HTML, CSS, and JavaScript for the Frontend ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KRATTOS Agent</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --sidebar-bg: #f9f9f9; --main-bg: #ffffff; --chat-bg: #ffffff;
            --text-color: #343541; --border-color: rgba(0, 0, 0, 0.1); --input-bg: #ffffff;
        }
        body, html { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--main-bg); color: var(--text-color); overflow: hidden; }
        .page-container { display: flex; height: 100%; }
        .sidebar { width: 260px; background-color: var(--sidebar-bg); padding: 10px; display: flex; flex-direction: column; flex-shrink: 0; border-right: 1px solid var(--border-color); }
        .chat-area { flex-grow: 1; display: flex; flex-direction: column; position: relative; }
        .new-chat-btn { border: 1px solid var(--border-color); border-radius: 5px; padding: 12px; width: 100%; text-align: left; cursor: pointer; background-color: transparent; color: var(--text-color); font-size: 14px; display: flex; align-items: center; gap: 8px; }
        .new-chat-btn:hover { background-color: #ececec; }
        #history-list { flex-grow: 1; margin-top: 20px; overflow-y: auto; }
        .history-item { padding: 12px; border-radius: 5px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 14px; }
        .history-item.active, .history-item:hover { background-color: #ececec; }
        .chat-history { flex-grow: 1; overflow-y: auto; padding: 20px 0; }
        .message-wrapper { padding: 24px 15%; display: flex; gap: 20px; }
        .message-wrapper.ai-message { background-color: var(--sidebar-bg); border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color); }
        .message-icon { width: 30px; height: 30px; border-radius: 5px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .message-icon svg { width: 20px; height: 20px; color: white; }
        .user-icon { background-color: #5b21b6; }
        .ai-icon { background-color: #19c37d; }

        /* --- NEW: Basic styling for rendered markdown elements --- */
        .message-content { padding-top: 2px; line-height: 1.7; }
        .message-content p:first-child { margin-top: 0; }
        .message-content p:last-child { margin-bottom: 0; }
        .message-content table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        .message-content th, .message-content td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
        .message-content th { background-color: #f0f0f0; }
        .message-content ul, .message-content ol { padding-left: 20px; }

        .chart-message { background-color: #fff; padding: 20px; border: 1px solid var(--border-color); border-radius: 12px; margin: 0 auto; max-width: 90%; width: 100%; box-sizing: border-box; }
        .prompt-form-wrapper { padding: 10px 24px 24px 24px; width: 100%; background: linear-gradient(to top, rgba(255,255,255,1) 0%, rgba(255,255,255,0) 100%); }
        .prompt-form-container { max-width: 768px; margin: 0 auto; }
        .prompt-form { position: relative; }
        #file-display { font-size: 12px; color: #666; background-color: #f0f0f0; padding: 4px 8px; border-radius: 4px; margin-bottom: 8px; display: none; }
        #attach-btn { position: absolute; left: 15px; bottom: 12px; background: transparent; border: 0px solid var(--border-color); width: 32px; height: 32px; border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        #file-input { display: none; }
        #prompt-input { width: 100%; background-color: var(--input-bg); border-radius: 12px; border: 1px solid var(--border-color); padding: 15px 50px 15px 60px; color: var(--text-color); font-size: 16px; resize: none; box-sizing: border-box; max-height: 200px; line-height: 1.5; padding-left: 15px; }
        #prompt-input:focus { outline: none; box-shadow: 0 0 0 1px var(--border-color); }
        #submit-button { position: absolute; right: 15px; bottom: 12px; background-color: var(--text-color); border: none; cursor: pointer; width: 32px; height: 32px; border-radius: 5px; display: flex; align-items: center; justify-content: center; }
        #submit-button:disabled { background-color: #ccc; }
        #submit-button svg { width: 16px; height: 16px; color: var(--main-bg); }
    </style>
</head>
<body>

<svg width="0" height="0" style="display:none;"><symbol id="user-icon-svg" viewBox="0 0 24 24"><path fill="currentColor" d="M12,12A5,5 0,1,0 7,7A5,5 0,0,0 12,12M12,14A10,10 0,0,0 2,24A1,1 0,0,0 3,25H21A1,1 0,0,0 22,24A10,10 0,0,0 12,14"/></symbol><symbol id="ai-icon-svg" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2.6l2.3 2.3L12 7.2 9.7 4.9 12 2.6M7.2 12L4.9 9.7 2.6 12l2.3 2.3L7.2 12M12 21.4l-2.3-2.3L12 16.8l2.3 2.3L12 21.4M16.8 12l2.3 2.3 2.3-2.3-2.3-2.3L16.8 12M12 12l-2-2-4 4 4 4 2-2 2 2 4-4-4-4-2 2z"/></symbol><symbol id="send-icon-svg" viewBox="0 0 24 24"><path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></symbol>
<symbol id="k-icon-svg" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
  <path fill="#0040ff" d="M36 32a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V4a4 4 0 0 1 4-4h28a4 4 0 0 1 4 4v28z"></path>
  <path fill="#FFF" d="M9.925 9.032c0-1.271.93-2.294 2.325-2.294c1.333 0 2.325.868 2.325 2.294v6.697l7.627-8.124c.342-.372.93-.868 1.799-.868c1.178 0 2.295.899 2.295 2.232c0 .806-.496 1.457-1.52 2.48l-5.861 5.767l7.162 7.473c.744.744 1.303 1.426 1.303 2.357c0 1.457-1.146 2.139-2.418 2.139c-.898 0-1.488-.526-2.357-1.457l-8.031-8.682v7.906c0 1.21-.93 2.232-2.325 2.232c-1.333 0-2.325-.867-2.325-2.232V9.032z"></path>
</symbol>
</svg>

<div class="page-container">
    <div class="sidebar"><button class="new-chat-btn" id="new-chat-btn">＋ New Chat</button><div id="history-list"></div></div>
    <div class="chat-area">
        <div class="chat-history" id="chat-history"></div>
        <div class="prompt-form-wrapper">
            <div class="prompt-form-container">
                <span id="file-display"></span>
                <form class="prompt-form" id="prompt-form">
                    <textarea id="prompt-input" placeholder="Talk to KRATTOS Knowledge Agent ..." rows="1"></textarea>
                    <button type="submit" id="submit-button" disabled><svg><use href="#send-icon-svg" /></svg></button>
                    <input type="file" id="file-input" style="display:none;">
                    <button type="button" id="attach-btn" disabled title=""></button>
                </form>
            </div>
        </div>
    </div>
</div>

<script>
    let chatSessions = [];
    let activeSessionId = null;
    const form = document.getElementById('prompt-form');
    const input = document.getElementById('prompt-input');
    const historyContainer = document.getElementById('chat-history');
    const submitButton = document.getElementById('submit-button');
    const historyList = document.getElementById('history-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const attachBtn = document.getElementById('attach-btn');
    const fileInput = document.getElementById('file-input');
    const fileDisplay = document.getElementById('file-display');

    function addNewChat() {
        const newSessionId = Date.now();
        chatSessions.push({
            id: newSessionId, name: `New Chat`,
            history: [{ type: 'text', sender: 'ai', content: 'Hello! How can I help you today with HR questions?' }],
            file: null, fileName: ''
        });
        switchTab(newSessionId);
    }

    function switchTab(sessionId) { activeSessionId = sessionId; render(); }
    function getActiveSession() { return chatSessions.find(s => s.id === activeSessionId); }

    function render() {
        const session = getActiveSession();
        if (!session) return;
        historyList.innerHTML = '';
        chatSessions.forEach(s => {
            const historyEl = document.createElement('div');
            historyEl.className = 'history-item';
            historyEl.textContent = s.name;
            if (s.id === activeSessionId) historyEl.classList.add('active');
            historyEl.onclick = () => switchTab(s.id);
            historyList.appendChild(historyEl);
        });
        historyContainer.innerHTML = '';
        session.history.forEach(msg => {
            if (msg.type === 'chart') addChartToDOM(msg.content);
            else addMessageToDOM(msg.content, msg.sender);
        });

        if (session.fileName) {
            fileDisplay.textContent = `📎 ${session.fileName}`;
            fileDisplay.style.display = 'inline-block';
        } else {
            fileDisplay.style.display = 'none';
        }
        historyContainer.scrollTop = historyContainer.scrollHeight;
    }

    function createMessageWrapper(sender) { const w = document.createElement('div'); w.className = 'message-wrapper'; if (sender === 'ai') w.classList.add('ai-message'); const i = document.createElement('div'); i.className = 'message-icon'; const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); const u = document.createElementNS("http://www.w3.org/2000/svg", "use"); if (sender === 'user') { i.classList.add('user-icon'); u.setAttributeNS("http://www.w3.org/1999/xlink", "href", "#user-icon-svg"); } else { i.classList.add('ai-icon'); u.setAttributeNS("http://www.w3.org/1999/xlink", "href", "#k-icon-svg"); } s.appendChild(u); i.appendChild(s); w.appendChild(i); historyContainer.appendChild(w); return w; }

    // --- MODIFIED: This function now converts markdown to HTML ---
    function addMessageToDOM(text, sender) {
        const wrapper = createMessageWrapper(sender);
        const content = document.createElement('div');
        content.className = 'message-content';
        // Use marked.parse() to convert markdown to safe HTML before display
        content.innerHTML = marked.parse(text || '');
        wrapper.appendChild(content);
        historyContainer.scrollTop = historyContainer.scrollHeight;
    }

    function addChartToDOM(chartData) { const w = createMessageWrapper('ai'); const c = document.createElement('div'); c.className = 'chart-message'; const canvas = document.createElement('canvas'); c.appendChild(canvas); w.appendChild(c); new Chart(canvas, chartData); historyContainer.scrollTop = historyContainer.scrollHeight; }

    newChatBtn.onclick = addNewChat;
    attachBtn.onclick = () => fileInput.click();
    fileInput.addEventListener('change', () => {
        const session = getActiveSession();
        if (fileInput.files.length > 0 && session) {
            session.file = fileInput.files[0];
            session.fileName = session.file.name;
            fileInput.value = '';
            render();
        }
    });

    input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = (input.scrollHeight) + 'px'; submitButton.disabled = input.value.trim().length === 0; });
    input.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });

    // --- MODIFIED: The submit handler now also uses marked.parse() ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userPrompt = input.value.trim();
        const session = getActiveSession();
        if (!userPrompt || !session) return;
        submitButton.disabled = true; input.value = ''; input.style.height = 'auto';

        session.history.push({ type: 'text', sender: 'user', content: userPrompt });
        if (session.name === 'New Chat') session.name = userPrompt.substring(0, 30);

        // Add a placeholder and render immediately
        const placeholder = { type: 'text', sender: 'ai', content: '...' };
        session.history.push(placeholder);
        render();

        const formData = new FormData();
        formData.append('prompt', userPrompt);
        if (session.file) {
            formData.append('file', session.file);
        }

        try {
            const response = await fetch('/generate', { method: 'POST', body: formData });
            const data = await response.json();

            // Remove the placeholder
            session.history.pop();

            if (data.error) {
                session.history.push({ type: 'text', sender: 'ai', content: `Error: ${data.error}` });
            } else if (data.response_type === 'analysis_and_chart') {
                session.history.push({ type: 'text', sender: 'ai', content: data.content.analysis });
                session.history.push({ type: 'chart', sender: 'ai', content: data.content.chart });
            } else {
                session.history.push({ type: 'text', sender: 'ai', content: data.response || data.content });
            }
        } catch (error) {
            session.history.pop();
            session.history.push({ type: 'text', sender: 'ai', content: 'Failed to connect to the server.' });
        } finally {
            submitButton.disabled = false;
            render(); // Re-render the final state
        }
    });

    addNewChat();
</script>
</body>
</html>
"""
# <button type="button" id="attach-btn" title="Attach file">📎</button

# --- Flask Routes ---
@app.route('/')
def index():
    """Renders the main web page from the HTML string."""
    return HTML_TEMPLATE

@app.route('/generate', methods=['POST'])
def generate():
    """Handles the request to the Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({'error': 'CRITICAL: The GEMINI_API_KEY environment variable is not set.'}), 500
    prompt = request.form.get('prompt')
    if not prompt:
        return jsonify({'error': 'No prompt was provided.'}), 400
    full_prompt = f"{SYSTEM_INSTRUCTION}\\n\\nUser prompt: {prompt}"
    parts = [{"text": full_prompt}]

    user_uploaded_file = request.files.get('file')

    if user_uploaded_file:
        file_bytes = user_uploaded_file.read()
        file_mime_type = user_uploaded_file.content_type
        parts.append({
            "inline_data": {"mime_type": file_mime_type, "data": base64.b64encode(file_bytes).decode('utf-8')}
        })
    elif os.path.exists(PRELOADED_FILE_PATH):
        print(f"No user file. Using preloaded file: {PRELOADED_FILE_PATH}")
        with open(PRELOADED_FILE_PATH, "rb") as f:
            file_bytes = f.read()
        # --- MODIFIED: Use the mimetypes library for accurate detection ---
        file_mime_type, _ = mimetypes.guess_type(PRELOADED_FILE_PATH)
        if file_mime_type is None:
            file_mime_type = 'application/octet-stream'  # Fallback if detection fails
        parts.append({
            "inline_data": {"mime_type": file_mime_type, "data": base64.b64encode(file_bytes).decode('utf-8')}
        })

    data = {"contents": [{"parts": parts}]}
    headers = {'X-goog-api-key': api_key, 'Content-Type': 'application/json'}

    # The rest of the function remains the same
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        gemini_response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_text = gemini_response_text.strip().removeprefix("```json").removeprefix("```").removesuffix(
            "```").strip()
        try:
            parsed_json = json.loads(cleaned_text)
            if 'analysis' in parsed_json and 'chart' in parsed_json:
                return jsonify({'response_type': 'analysis_and_chart', 'content': parsed_json})
            elif 'type' in parsed_json and 'data' in parsed_json:
                return jsonify({'response_type': 'chart', 'content': parsed_json})
            else:
                return jsonify({'response_type': 'text', 'content': cleaned_text})
        except json.JSONDecodeError:
            return jsonify({'response_type': 'text', 'content': gemini_response_text})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"API request failed: {e}",
                        'details': response.text if 'response' in locals() else 'No response'}), 500
    except (KeyError, IndexError) as e:
        return jsonify({'error': 'Failed to parse the API response.', 'details': response.json()}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
