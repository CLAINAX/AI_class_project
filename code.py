import streamlit as st
import requests
import urllib.parse
import re
from anthropic import Anthropic

# API KEY 
ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"

class OllamaClient:
    def __init__(self, host="http://100.86.250.7:11434"):
        self.endpoint = f"{host}/api/generate"

    def request(self, model, prompt, system=""):
        payload = {
            "model": model, "prompt": prompt, "system": system,
            "stream": False, "options": {"temperature": 0.4}
        }
        try:
            response = requests.post(self.endpoint, json=payload, timeout=90)
            return response.json().get("response", "")
        except Exception as e:
            return f"Ollama Error: {str(e)}"

# Anthropic Client added
class AnthropicClient:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        # Haiku 4.5
        self.model = "claude-haiku-4-5"
    def request(self, prompt, system=""):
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.4,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return f"Anthropic Error: {str(e)}"

# SearXNG
def buscar_imagen_real(query, searx_url="http://100.126.29.86:8080/search"):
    params = {
        'q': query,
        'format': 'json',
        'categories': 'images',
        'safesearch': 1
    }
    try:
        resp = requests.get(searx_url, params=params, timeout=10)
        results = resp.json().get('results', [])
        if results:
            # Devolvemos la primera imagen que parezca válida
            return results[0].get('img_src') or results[0].get('thumbnail')
    except Exception as e:
        print(f"SearXNG Error: {e}")
    return None

class NotebookOrchestrator:
    def __init__(self, local_client, cloud_client):
        self.local_client = local_client
        self.cloud_client = cloud_client
        self.models = {"fast": "llama3.2:3b", "smart": "qwen2.5:7b"}

    def run_workflow(self, topic):
        # 1. sketch
        draft = self.local_client.request(self.models["fast"], f"Briefly explain: {topic}", "You are a technical expert.")
        yield "draft", draft

        # 2. feedback (Cloud API)
        critique = self.cloud_client.request(f"Critique this text:\n{draft}", "You are a strict auditor.")
        yield "critique", critique

        # 3. final (Cloud API)
        final = self.cloud_client.request(f"Improve this using the critique:\n{draft}\n\nCritique: {critique}", "You are a chief editor.")
        yield "final", final

        # 4. ASCII tree (Local GPU)
        tree = self.local_client.request(self.models["smart"], f"Create an ASCII concept tree (only the tree) about:\n{final}", "Create a visual hierarchy using | and +--")
        yield "tree", tree

        # 5. def keywords for search (Local GPU)
        keywords = self.local_client.request(self.models["fast"], f"Give me 3 keywords to search for a professional photo of: {topic}", "Respond only with the keywords in English.")
        yield "keywords", keywords

def main():
    st.set_page_config(page_title="IA NotebookLM Service", layout="wide")
    
    st.sidebar.title("Temporal Infrastructure")
    server_ip = st.sidebar.text_input("Server_2 (Ollama)", "100.86.250.7")
    searx_ip = st.sidebar.text_input("Server_1 (SearXNG)", "100.126.29.86:8080")
    
    st.title("Hello, I am your schematic AI assistant.")
    st.markdown("---")

    user_input = st.text_input("Should we start?", placeholder="e.g.: LLM, Quantum Physics...")

    if st.button("RUN"):
        if user_input:
            local_client = OllamaClient(f"http://{server_ip}:11434")
            cloud_client = AnthropicClient(ANTHROPIC_API_KEY)
            orch = NotebookOrchestrator(local_client, cloud_client)
            
            col1, col2 = st.columns([1, 1.5])
            
            with col1:
                status = st.empty()
                res_draft = ""
                res_critique = ""
                
                for step, content in orch.run_workflow(user_input):
                    if step == "draft":
                        res_draft = content
                        status.info("Analyzing concepts...")
                    elif step == "critique":
                        res_critique = content
                        status.info("Auditing information...")
                    elif step == "final":
                        st.subheader("Output (final)")
                        st.success(content)
                        with st.expander("See process"):
                            st.markdown(f'<div style="color:red">{res_critique}</div>', unsafe_allow_html=True)
                        status.info("Structuring hierarchy...")
                    
                    elif step == "tree":
                        st.subheader("Scheme")
                        st.code(content, language="text")
                        status.info("Searching for reference image...")
                    
                    elif step == "keywords":
                        # call SearXNG
                        url_img = buscar_imagen_real(content, f"http://{searx_ip}/search")
                        if url_img:
                            st.subheader("Concept idea")
                            st.image(url_img, caption=f"Image retrieved via SearXNG for: {user_input}")
                        else:
                            st.warning("No professional image was found on the search server.")
                        
                        status.success("Error number: 0")
        else:
            st.warning("Input not valid")

if __name__ == "__main__":
    main()
