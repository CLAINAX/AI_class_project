goal?
create a service that used at least one agent and it could help on our daily life

how did we make it?
we hosted the code.py on a node server that was accesible from the clients. The AI where from an claude API key and a self-hosted AI.

what have we used? 
streamlit as st
requests
urllib.parse
re
Anthropic
qwen 7.2b
llama 3.2
tailscale
reverse dns


# 🤖 AI Agent Service
This service is a chatbot that answears on an analytical way as well as providing an imatge and a small mind map to complement the textual explenation with visuals.

## 🚀 Arquitectre
Little explenation ablut it's procces
* **Frontend/Interfície:** Developed with Streamlit.
* **AI Models:** This is a hibrid agent that comvines both local and external LLM (Anthropic,**Llama 3.2** / **Qwen 7.2B**) Thanks to **Ollama**.
* **Network:** Even if http, all data is encrypted due to Tailscale and it's easy to acces acording to a reverse DNS with its propper rewrites.

## 🛠️ Requirements and instalation
How can you acces the code?
1. Clone repository
2. Install repositorys: `pip install -r requirements.txt`
3. Run the app (you need to be inside the Tailscale network to acces the AI's ports: `streamlit run code.py`
