import streamlit as st
import requests
import re
from anthropic import Anthropic

# API KEY 
ANTHROPIC_API_KEY = "API KEY"

# --- AGENT LOCAL
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

# --- AGENT NÚVOL
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
            # Extracció robusta saltant els blocs de pensament
            for block in message.content:
                if getattr(block, 'type', '') == 'text':
                    return block.text
            return str(message.content)
        except Exception as e:
            return f"Anthropic Error: {str(e)}"
    
    def evaluate_score(self, content, topic):
        """Avaluació autònoma del resultat (Agent Evaluator)"""
        rubric = """
        RÚBRICA D'AVALUACIÓ (1-5):
        5 - Excel·lent: Informació exacta, estructura en bullet points clara, cobreix aspectes rellevants, format impecable.
        4 - Bo: Informació majoritàriament exacta, estructura clara, complet amb petites omissions, format adequat.
        3 - Acceptable: Informació generalment correcta però amb errors menors, moderadament rellevant.
        2 - Deficient: Errors evidents, estructura confusa, omissions importants.
        1 - Pobre: Incorrecta, sense estructura, irrellevant.
        
        Respon EXACTAMENT amb aquest format al final de la teva reflexió:
        SCORE: [número]
        JUSTIFICACIÓ: [1 o 2 frases curtes]
        """
        
        prompt = f"Tema: {topic}\n\nContingut a avaluar:\n{content}\n\n{rubric}"
        try:
            response = self.request(prompt, "Ets un avaluador objectiu i rigorós. Segueix la rúbrica estrictament.")
            # Regex blindat contra negretes o espais extres (ex: **SCORE:** 4)
            match = re.search(r'SCORE[\s:\*]*(\d)', response, re.IGNORECASE)
            if match:
                return int(match.group(1)), response
            return 0, response
        except Exception as e:
            return 0, f"Error en avaluació: {str(e)}"

# --- EINA DE CERCA
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

# --- ORQUESTRADOR
class NotebookOrchestrator:
    def __init__(self, local_client, cloud_client):
        self.local_client = local_client
        self.cloud_client = cloud_client
        self.models = {"fast": "llama3.2:3b", "smart": "qwen2.5:7b"}
        self.max_iterations = 3
        self.score_threshold = 4

    def run_workflow(self, topic):
        best_attempt = None
        best_score = 0
        attempts_history = []
        
        for iteration in range(1, self.max_iterations + 1):
            yield "status", f"`[Iteració {iteration}/{self.max_iterations}] Generant esborrany...`"
            
            
            context = ""
            if attempts_history:
                last_feedback = attempts_history[-1].get('critique', '')
                context = f"\n\n[ATENCIÓ] En un intent previ hi havia aquests errors: {last_feedback}\nCorregeix-los en aquesta nova explicació."
            
            draft = self.local_client.request(
                self.models["fast"], 
                f"Explica breument: {topic}{context}", 
                "Ets un expert tècnic."
            )
            yield "draft", draft, iteration

            
            yield "status", f"`[Iteració {iteration}/{self.max_iterations}] Avaluant qualitat...`"
            critique = self.cloud_client.request(f"Critica aquest text:\n{draft}", "Ets un auditor estricte. Identifica errors i àrees de millora.")
            yield "critique", critique, iteration

            
            yield "status", f"`[Iteració {iteration}/{self.max_iterations}] Refinant contingut...`"
            final_prompt = f"Millora això usant la crítica:\n{draft}\n\nCrítica: {critique}"
            system_prompt = "Ets un editor en cap. Output obligatori com a llista de bullet points clara i sintètica. Sense blocs de codi per al text normal."
            final = self.cloud_client.request(final_prompt, system_prompt)
            
            
            yield "status", f"`[Iteració {iteration}/{self.max_iterations}] Puntuant segons rúbrica...`"
            score, evaluation_text = self.cloud_client.evaluate_score(final, topic)
            
            attempts_history.append({
                'iteration': iteration,
                'content': final,
                'score': score,
                'critique': critique,
                'evaluation': evaluation_text
            })
            
            yield "score", score, evaluation_text, iteration
            
            # Guardar el millor intent a la memòria
            if score > best_score:
                best_score = score
                best_attempt = final
            
            # Comprovar 
            if score >= self.score_threshold:
                yield "success", final, score, iteration
                break # Sortim del bucle: Èxit assolit
            
            # reintentar
            if iteration < self.max_iterations:
                yield "status", f"`[Iteració {iteration}/{self.max_iterations}] Score {score}/5 insuficient. Reintentant...`"
        
        else:
            # S'executa només si el bucle for acaba sense un 'break' (esgotem intents)
            yield "warning", best_attempt, best_score, self.max_iterations

# --- INTERFÍCIE
def main():
    st.set_page_config(page_title="Colab-Style AI Assistant", layout="wide", initial_sidebar_state="expanded")
    
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
            .streamlit-expanderContent { background-color: #1e1e1e; border: 1px solid #333; border-top: none; padding: 10px; }
            .console-text { font-family: 'Consolas', monospace; color: #4EC9B0; }
            .warning-box { background-color: #3d2817; border-left: 4px solid #ff9800; padding: 10px; margin: 10px 0; }
            .score-box { background-color: #252526; padding: 8px 12px; border-radius: 4px; margin: 5px 0; font-family: 'Consolas', monospace; border-left: 3px solid #333; }
            .iteration-5 { color: #4EC9B0; font-weight: bold; }
            .iteration-4 { color: #9cdcfe; font-weight: bold; }
            .iteration-3 { color: #ce9178; font-weight: bold; }
            .iteration-2 { color: #d16969; font-weight: bold; }
            .iteration-1 { color: #f44747; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.title("ENV")
    server_ip = st.sidebar.text_input("Local Inference Node", "100.86.250.7")
    searx_ip = st.sidebar.text_input("Search Node", "100.126.29.86:8080")
    
    st.markdown("<h1>Colab_Assistant.ipynb</h1>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<h3 class='console-text'>[1] Input Cell</h3>", unsafe_allow_html=True)
    st.markdown("<span style='color:#808080; font-family:Consolas;'># Threshold de qualitat: 4/5 | Màxim intents: 3</span>", unsafe_allow_html=True)
    user_input = st.text_area("Enter your prompt:", placeholder="Ex: Explica la Mecànica Quàntica", height=100)

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
                iterations_data = []
                final_content = None
                final_score = 0
                warning_flag = False
                
                for event_type, *data in orch.run_workflow(user_input):
                    if event_type == "status":
                        status.info(data[0])
                    
                    elif event_type == "draft":
                        iterations_data.append({"iter": data[1], "draft": data[0]})
                    
                    elif event_type == "critique":
                        iterations_data[-1]["critique"] = data[0]
                    
                    elif event_type == "score":
                        score, eval_text, iteration = data
                        iterations_data[-1]["score"] = score
                        iterations_data[-1]["evaluation"] = eval_text
                        
                        # Mostrar puntuació en temps real a la UI
                        color_class = f"iteration-{score}" if score > 0 else "iteration-1"
                        
                        # Extraure només la justificació si existeix, si no, un tros de l'avaluació
                        justificacio = eval_text.split("JUSTIFICACIÓ:")[-1].strip() if "JUSTIFICACIÓ:" in eval_text else eval_text[:100]
                        
                        st.markdown(
                            f'<div class="score-box">'
                            f'<span class="{color_class}">● Iteració {iteration}: {score}/5</span> '
                            f'<span style="color:#808080; font-size:0.9em;">- {justificacio}</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                    
                    elif event_type == "success":
                        content, score, iteration = data
                        final_content = content
                        final_score = score
                        status.success(f"`✓ ExitCode 0: Qualitat assolida ({score}/5) a l'intent {iteration}`")
                    
                    elif event_type == "warning":
                        content, score, max_iter = data
                        final_content = content
                        final_score = score
                        warning_flag = True
                        status.warning(f"`⚠ Warning: Qualitat màxima {score}/5 assolida després de {max_iter} intents`")
                
                # Renderitzat de l'Output Final
                st.markdown("### Synthesis Result:")
                
                if warning_flag:
                    st.markdown(
                        f'<div class="warning-box">'
                        f'<strong>waRNING:</strong> Agent failed to reach quality threshold (4/5) after 3 attempts.<br>'
                        f'<span style="font-size:0.9em;">Fallback to best attempt score: {final_score}/5</span>'
                        f'</div>', 
                        unsafe_allow_html=True
                    )
                
                # Format
                st.markdown(final_content)
                
                # for logs
                with st.expander("Show Audit Logs & Iteration History"):
                    for iter_data in iterations_data:
                        it_num = iter_data['iter']
                        it_score = iter_data.get('score', 'N/A')
                        st.markdown(f"**Iteració {it_num}** - Score: {it_score}/5")
                        st.markdown(f'<div style="color:#d16969; font-size:0.85em; margin-left:10px;"><b>Critique:</b> {iter_data.get("critique", "N/A")[:300]}...</div>', unsafe_allow_html=True)
                        st.markdown("---")
            
            # --- Part Visua
            with col_visual:
                if final_content:
                    st.markdown("### Concept Hierarchy:")
                    tree = local_client.request(
                        orch.models["smart"], 
                        f"Crea un arbre ASCII (només l'arbre) sobre els conceptes clau d'aquest text:\n{final_content}", 
                        "Crea una jerarquia visual usant només | i +--"
                    )
                    st.code(tree, language="text")
                    
                    # Generació d'imatge
                    keywords = local_client.request(
                        orch.models["fast"], 
                        f"Dona'm 3 paraules clau en anglès per cercar una foto professional que il·lustri: {user_input}", 
                        "Respon NOMÉS amb les 3 paraules clau en anglès separades per comes. Sense explicacions."
                    )
                    
                    url_img = buscar_imagen_real(keywords, f"http://{searx_ip}/search")
                    if url_img:
                        st.markdown("### Reference Asset:")
                        st.image(url_img, caption=f"Keywords used: {keywords}")
                    else:
                        st.warning(f"`ResourceNotFoundException: No image located for '{keywords}'.`")
                        
        else:
            st.error("`SyntaxError: Input cell cannot be empty.`")

if __name__ == "__main__":
    main()
