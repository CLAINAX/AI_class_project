import streamlit as st
import requests
from anthropic import Anthropic

# API KEY 
ANTHROPIC_API_KEY = "KEY"

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

# Anthropic Client (Thinking)
class AnthropicClient:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-opus-4-6"
        
    def request(self, prompt, system=""):
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=5000,
                system=system,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}]
            )
            
            for block in message.content:
                if getattr(block, 'type', '') == 'text':
                    return block.text
            return str(message.content) 
        except Exception as e:
            return f"Anthropic Error: {str(e)}"

# SearXNG
def buscar_imagen_real(query, searx_url="http://100.126.29.86:8080/search"):
    params = {'q': query, 'format': 'json', 'categories': 'images', 'safesearch': 1}
    try:
        resp = requests.get(searx_url, params=params, timeout=10)
        results = resp.json().get('results', [])
        if results:
            return results[0].get('img_src') or results[0].get('thumbnail')
    except Exception as e:
        pass
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

        # 2. feedback
        critique = self.cloud_client.request(f"Critique this text:\n{draft}", "You are a strict auditor.")
        yield "critique", critique

        # 3. final (Formato limpio por puntos)
        final_prompt = f"Improve this using the critique:\n{draft}\n\nCritique: {critique}"
        system_prompt = "You are a chief editor. Output the final result as a clear, easy-to-read list of bullet points. Do not use code blocks for normal text."
        final = self.cloud_client.request(final_prompt, system_prompt)
        yield "final", final

        # 4. ASCII tree
        tree = self.local_client.request(self.models["smart"], f"Create an ASCII concept tree (only the tree) about:\n{final}", "Create a visual hierarchy using | and +--")
        yield "tree", tree

        # 5. def keywords
        keywords = self.local_client.request(self.models["fast"], f"Give me 3 keywords to search for a professional photo of: {topic}", "Respond only with the keywords in English, separated by commas.")
        yield "keywords", keywords

def main():
    # --- UI Configuration (Diseño Coherente) ---
    st.set_page_config(page_title="Colab-Style AI Assistant", layout="wide", initial_sidebar_state="expanded")
    
    # CSS Ajustado: Fuente legible para textos, fuente 'hacker' para interfaz
    st.markdown("""
        <style>
            .stApp { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Segoe UI', sans-serif; }
            [data-testid="stSidebar"] { background-color: #252526; border-right: 1px solid #333; }
            h1, h2, h3 { color: #569cd6; font-weight: normal; font-family: 'Consolas', monospace; }
            .stTextInput > div > div > input, .stTextArea > div > div > textarea {
                background-color: #1e1e1e !important; color: #d4d4d4 !important; border: 1px solid #333 !important; font-family: 'Consolas', monospace;
            }
            .stButton > button { background-color: #0e639c; color: white; border: none; border-radius: 2px; padding: 4px 12px; font-family: 'Consolas', monospace; }
            .stButton > button:hover { background-color: #1177bb; }
            code { background-color: #1e1e1e !important; color: #ce9178 !important; }
            pre { background-color: #1e1e1e !important; border: 1px solid #333; border-radius: 4px; }
            .streamlit-expanderHeader { color: #c586c0; background-color: #252526; font-family: 'Consolas', monospace; }
            .streamlit-expanderContent { background-color: #1e1e1e; border: 1px solid #333; border-top: none; }
            .console-text { font-family: 'Consolas', monospace; color: #4EC9B0; }
        </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.title("ENV")
    server_ip = st.sidebar.text_input("Local Inference Node", "100.86.250.7")
    searx_ip = st.sidebar.text_input("Search Node", "100.126.29.86:8080")
    
    st.markdown("<h1>EnHuEr</h1>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<h3 class='console-text'>[1] Input Cell</h3>", unsafe_allow_html=True)
    user_input = st.text_area("Enter your prompt:", placeholder="Ej: ¿Qué es un LLM?", height=100)

    col_run, col_spacer = st.columns([1, 10])
    with col_run:
        run_clicked = st.button("▶ Run Cell")

    if run_clicked:
        if user_input:
            local_client = OllamaClient(f"http://{server_ip}:11434")
            cloud_client = AnthropicClient(ANTHROPIC_API_KEY)
            orch = NotebookOrchestrator(local_client, cloud_client)
            
            st.markdown("---")
            st.markdown("<h3 class='console-text'>[2] Execution Output</h3>", unsafe_allow_html=True)
            
            col_text, col_visual = st.columns([1.5, 1])
            
            with col_text:
                status = st.empty()
                res_critique = ""
                
                for step, content in orch.run_workflow(user_input):
                    if step == "draft":
                        status.info("`[Local GPU] Drafting base concepts...`")
                    elif step == "critique":
                        res_critique = content
                        status.info("`[Cloud API] Auditing information...`")
                    elif step == "final":
                        st.markdown("### Synthesis Result:")
              #si
                        st.markdown(content)
                        with st.expander("Show Audit Logs"):
                            st.markdown(f'<div style="color:#d16969; font-family:monospace; font-size:0.9em;">{res_critique}</div>', unsafe_allow_html=True)
                        status.info("`[Local GPU] Structuring hierarchy...`")
                    elif step == "tree":
                        with col_visual:
                            st.markdown("### Concept Hierarchy:")
                            st.code(content, language="text")
                        status.info("`[Local Server] Fetching external assets...`")
                    elif step == "keywords":
                        url_img = buscar_imagen_real(content, f"http://{searx_ip}/search")
                        with col_visual:
                            if url_img:
                                st.markdown("### Reference Asset:")
                                st.image(url_img, caption=f"Asset linked to: {user_input}")
                            else:
                                st.warning("`ResourceNotFoundException: No image located.`")
                        status.success("`Execution finished with exit code 0.`")
        else:
            st.error("`SyntaxError: Input cell cannot be empty.`")

if __name__ == "__main__":
    main()
