import streamlit as st
import datetime
import requests
import json
import google.generativeai as genai
import re # Para expressões regulares na análise de texto

# --- Configurações Iniciais ---
st.set_page_config(page_title="Crystal - Sua Assistente Pessoal", layout="centered")

# URL da imagem da Crystal
# Substitua pela sua imagem real, por exemplo: "https://i.imgur.com/your_crystal_image.png"
CRYSTAL_IMAGE_URL = "crystal_avatar.png"

# --- Carregar Chaves de API de st.secrets ---
try:
    OPENWEATHER_API_KEY = st.secrets["OPENWEATHER_API_KEY"]
    # LINHA CORRIGIDA AQUI: nome da variável não pode ter espaço
    Google Search_API_KEY = st.secrets["Google Search_API_KEY"] 
    GOOGLE_CSE_ID = st.secrets["GOOGLE_CSE_ID"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError as e:
    st.error(f"Erro: Chave de API não encontrada em .streamlit/secrets.toml: {e}. "
             "Por favor, configure suas chaves conforme as instruções.")
    st.stop() # Interrompe a execução se as chaves não estiverem configuradas

# Configurar o modelo Gemini
genai.configure(api_key=GEMINI_API_KEY)
# 'gemini-1.5-flash' é rápido e bom para chat. 'gemini-pro' é outra boa opção.
GEMINI_MODEL = genai.GenerativeModel('gemini-1.5-flash')

# --- Funções de API ---

def get_gemini_response(prompt_text, chat_history):
    """Obtém uma resposta do modelo Gemini, mantendo o histórico da conversa."""
    try:
        chat = GEMINI_MODEL.start_chat(history=chat_history)
        response = chat.send_message(prompt_text)
        return response.text
    except Exception as e:
        st.error(f"Erro ao comunicar com o Gemini API: {e}")
        return "Desculpe, tive um problema ao processar sua solicitação com a IA. Por favor, tente novamente."

def get_weather(city):
    """Busca informações meteorológicas para uma cidade usando a API OpenWeatherMap."""
    if not OPENWEATHER_API_KEY: return "Desculpe, a chave da API do OpenWeatherMap não está configurada."
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}appid={OPENWEATHER_API_KEY}&q={city}&units=metric&lang=pt_br"
    try:
        response = requests.get(complete_url)
        response.raise_for_status()
        data = response.json()
        
        if data["cod"] == 200:
            main = data["main"]
            weather = data["weather"][0]
            temperature = main["temp"]
            description = weather["description"]
            return f"O tempo em {city.capitalize()} é de {temperature:.1f}°C com {description.capitalize()}."
        elif data["cod"] == "404": return "Não consegui encontrar informações de tempo para essa cidade. Verifique o nome e tente novamente."
        else: return f"Erro ao buscar o tempo: {data.get('message', 'Erro desconhecido')}"
    except requests.exceptions.RequestException as e: return f"Erro de conexão ao buscar o tempo: {e}. Verifique sua conexão com a internet."
    except json.JSONDecodeError: return "Erro ao processar a resposta do serviço de tempo."

def Google Search(query):
    """Realiza uma busca na internet usando a Google Custom Search API."""
    if not Google Search_API_KEY or not GOOGLE_CSE_ID: return "Desculpe, as chaves da API de busca do Google (ou o CSE ID) não estão configuradas."
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": Google Search_API_KEY, "cx": GOOGLE_CSE_ID, "q": query}
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json()
        if "items" in results:
            return results["items"] # Retorna a lista completa de itens para processamento
        else: return None
    except requests.exceptions.RequestException as e: return f"Erro de conexão ao realizar a busca: {e}"
    except json.JSONDecodeError: return "Erro ao processar a resposta do serviço de busca."

# --- Funções para Novas Funcionalidades ---

def create_or_add_list_item(user_input):
    """
    Simula a criação de listas ou adição de itens.
    Para uma implementação real, você precisaria de um sistema de persistência (ex: SQLite).
    """
    user_input_lower = user_input.lower()
    
    # Criar lista
    match_create = re.search(r"criar lista de (tarefas|compras|(.+?)) com (.+)", user_input_lower)
    if match_create:
        list_name_raw = match_create.group(1) if match_create.group(1) else match_create.group(2)
        list_name = list_name_raw.strip()
        items_str = match_create.group(3)
        items = [item.strip() for item in items_str.split(' e ') if item.strip()]
        return f"Criei a lista '{list_name.capitalize()}' com os itens: {', '.join(items)}. (Simulado)"

    # Adicionar item a lista existente (requer lógica para gerenciar listas persistentes)
    match_add = re.search(r"adicionar (.+?) à lista de (tarefas|compras|(.+))", user_input_lower)
    if match_add:
        item_to_add = match_add.group(1).strip()
        list_name_raw = match_add.group(2) if match_add.group(2) else match_add.group(3)
        list_name = list_name_raw.strip()
        return f"Adicionei '{item_to_add}' à sua lista de '{list_name.capitalize()}'. (Simulado)"
        
    return None # Não correspondeu a um comando de lista conhecido

def create_reminder_or_appointment(user_input):
    """
    Simula a criação de lembretes ou agendamentos.
    Para uma implementação real, precisaria de persistência e um mecanismo de notificação.
    """
    user_input_lower = user_input.lower()
    # Usamos a data e hora do contexto para garantir que os lembretes são para o futuro
    # Obtém a data e hora atual do sistema
    current_datetime = datetime.datetime.now()
    today = current_datetime.date()
    
    # Regex para "me lembre de [título] [quando] [hora]"
    match = re.search(r"(?:me lembre de|agendar|criar lembrete para) (.+?) (amanhã|hoje|quarta-feira|terça-feira|quinta-feira|sexta-feira|sábado|domingo|dia \d{1,2}/\d{1,2}(?:/\d{4})?) *(?:às|as)? *(\d{1,2}(?:h|\:\d{2})?) *(da manhã|da tarde|da noite|pm|am)?", user_input_lower)
    
    if match:
        title = match.group(1).strip()
        when_str = match.group(2).strip()
        # Corrigido: Usar 'match.group(3)' para a hora
        time_str = match.group(3) 
        am_pm_str = match.group(4)
        
        start_date = today
        time_of_day = None
        am_pm_or_unknown = "UNKNOWN"

        # Parsing da data
        if "amanhã" in when_str: start_date += datetime.timedelta(days=1)
        elif "hoje" in when_str: start_date = today
        elif "dia" in when_str:
            try:
                date_parts = re.search(r"dia (\d{1,2}/\d{1,2}(?:/\d{4})?)", when_str)
                if date_parts:
                    date_val = date_parts.group(1)
                    if len(date_val.split('/')) == 2: date_val += f"/{today.year}"
                    parsed_date = datetime.datetime.strptime(date_val, "%d/%m/%Y").date()
                    # Ajuste para o ano se a data já passou no ano atual
                    if parsed_date < today: parsed_date = parsed_date.replace(year=today.year + 1)
                    start_date = parsed_date
            except ValueError: pass
        else: # Dias da semana
            weekdays = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
            day_map = {d: i for i, d in enumerate(weekdays)}
            if when_str in day_map:
                current_weekday = today.weekday()
                target_weekday = day_map[when_str]
                days_diff = (target_weekday - current_weekday + 7) % 7
                if days_diff == 0 and time_str:
                    current_time_obj = current_datetime.time()
                    try:
                        parsed_time = datetime.datetime.strptime(time_str.replace('h', ':00'), "%H:%M").time()
                        if parsed_time <= current_time_obj: days_diff += 7
                    except ValueError: pass
                start_date += datetime.timedelta(days=days_diff)

        # Parsing do tempo
        if time_str:
            time_str = time_str.replace('h', ':00')
            if ':' not in time_str: time_str += ':00'

            try:
                hour = int(time_str.split(':')[0])
                if am_pm_str:
                    if "pm" in am_pm_str and hour < 12: hour += 12; am_pm_or_unknown = "PM"
                    elif "am" in am_pm_str and hour == 12: hour = 0; am_pm_or_unknown = "AM"
                    else: am_pm_or_unknown = am_pm_str.upper()
                
                # Se não especificado AM/PM, e a hora for no passado (do dia atual), tenta adicionar 12h
                if not am_pm_str and start_date == today:
                    now_hour = current_datetime.hour
                    if hour < now_hour:
                        if hour <= 12: hour += 12; am_pm_or_unknown = "PM"

                time_of_day = f"{hour:02d}:{time_str.split(':')[1]}:00"
                
                combined_dt_str = f"{start_date} {time_of_day}"
                combined_dt = datetime.datetime.strptime(combined_dt_str, "%Y-%m-%d %H:%M:%S")
                if combined_dt < current_datetime: # Usa a hora atual do contexto
                    return "Desculpe, não consigo criar lembretes para o passado. Por favor, especifique uma data e/ou hora futura."

            except ValueError: time_of_day = None
        
        date_display = start_date.strftime("%d/%m/%Y")
        time_display = time_of_day if time_of_day else "em algum momento do dia"
        am_pm_display = f" ({am_pm_or_unknown})" if am_pm_or_unknown != "UNKNOWN" and time_of_day else ""

        return f"Lembrete criado: '{title.capitalize()}' para {date_display} às {time_display}{am_pm_display}. (Simulado)"
    
    return None

def get_news_summary(query):
    """
    Busca notícias/artigos e simula o resumo do conteúdo.
    Para resumo real, precisaria de uma biblioteca de web scraping (ex: BeautifulSoup)
    e um LLM para resumir o texto extraído.
    """
    search_results = Google Search(query)
    if not search_results:
        return f"Não encontrei notícias ou artigos sobre '{query}'. Tente um termo diferente."
    
    first_link = None
    for item in search_results:
        if item.get('link') and item.get('mime') and 'text/html' in item['mime']:
            first_link = item['link']
            break
    
    if first_link:
        # **AQUI SERIA A PARTE PARA FAZER O WEB SCRAPING E OBTER O CONTEÚDO**
        # content_to_summarize = Browse(url=first_link, query="conteúdo principal do artigo")
        # Se você tivesse o conteúdo:
        # summary_prompt = f"Resuma o seguinte artigo em português em no máximo 3-5 frases. Mantenha o foco nos pontos principais:\n\n{content_to_summarize[:3000]}..."
        # return f"Encontrei este artigo ([Link]({first_link})):\n\n{get_gemini_response(summary_prompt, [])}"

        return f"Encontrei notícias sobre '{query}'. O primeiro resultado é: '{search_results[0].get('title', 'Sem título')}' ([Link]({first_link})). " \
               "Se eu pudesse acessar o conteúdo, faria um resumo para você! (Simulado)"
    else:
        return "Não consegui encontrar um link de artigo HTML válido para resumir."

# --- Função de Placeholder para Banco de Dados RAG (Retrieval Augmented Generation) ---
def search_rag_database(query):
    """
    Esta função é um placeholder para a funcionalidade de Banco de Dados RAG.
    Para implementá-la de verdade, você precisaria de:
    1. Seus documentos (texto, PDFs, etc.).
    2. Uma biblioteca como `langchain` ou `llama_index` para processar e gerar embeddings.
    3. Um banco de dados vetorial (como ChromaDB, Pinecone, FAISS) para armazenar os embeddings.
    4. Uma lógica para recuperar os documentos mais relevantes e passá-los para o Gemini.
    """
    return "Desculpe, a funcionalidade de banco de dados RAG ainda não está totalmente implementada. Mas estou aprendendo a usar meus próprios dados!"


# --- Lógica Principal da Crystal para Responder ---

def crystal_respond(user_input, chat_history_for_gemini):
    """
    Determina a intenção do usuário e chama a função apropriada.
    """
    user_input_lower = user_input.lower()

    # Prioridade para comandos específicos:
    # 1. Comandos de Listas (Tarefas/Compras)
    if "criar lista de" in user_input_lower or "adicionar" in user_input_lower and "à lista de" in user_input_lower:
        response = create_or_add_list_item(user_input)
        if response: return response

    # 2. Comandos de Lembretes/Agendamentos
    if "me lembre de" in user_input_lower or "agendar" in user_input_lower or "criar lembrete para" in user_input_lower:
        response = create_reminder_or_appointment(user_input)
        if response: return response

    # 3. Comandos de Notícias/Resumos
    if "notícias sobre" in user_input_lower or "resumo de artigo sobre" in user_input_lower or "resumir artigo" in user_input_lower:
        query = user_input_lower.replace("notícias sobre", "").replace("resumo de artigo sobre", "").replace("resumir artigo", "").strip()
        if query: return get_news_summary(query)
        else: return "Por favor, especifique sobre o que você quer notícias ou qual artigo resumir."

    # 4. Comandos de Tempo e Data
    if "tempo em" in user_input_lower:
        city = user_input_lower.split("tempo em")[-1].strip()
        return get_weather(city)
    elif "que dia é hoje" in user_input_lower or "data de hoje" in user_input_lower:
        today = datetime.date.today().strftime("%d/%m/%Y")
        return f"Hoje é {today}."
    elif "que horas são" in user_input_lower:
        now = datetime.datetime.now().strftime("%H:%M")
        return f"São {now}."
    elif "pesquisar por" in user_input_lower or "pesquise por" in user_input_lower or "procure por" in user_input_lower:
        search_query = user_input_lower.replace("pesquisar por", "").replace("pesquise por", "").replace("procure por", "").strip()
        if search_query:
            results = Google Search_query # Chamada correta da função Google Search
            if results:
                top_result = results[0]
                title = top_result.get('title', 'Sem título')
                snippet = top_result.get('snippet', 'Sem descrição')
                link = top_result.get('link', 'Sem link')
                return f"Encontrei: **{title}** - {snippet} ([Link]({link}))"
            else:
                return "Não encontrei resultados para sua busca na internet. Tente reformular a pergunta."
        else:
            return "Por favor, especifique o que você gostaria de pesquisar na internet."
            
    # 5. Resposta Padrão do LLM (se nenhum comando específico for detectado)
    return get_gemini_response(user_input, chat_history_for_gemini)


# --- Interface Streamlit ---

# --- Injeção de CSS Personalizado para Design Moderno ---
st.markdown("""
<style>
    /* Estilos gerais do corpo da página */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f8f8ff; /* Fundo branco-lavanda suave */
        color: #333333;
    }

    /* Estilos para a barra lateral */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6; /* Uma cor de fundo mais suave */
        color: #333333;
        border-right: 1px solid #e0e0e0;
        box-shadow: 2px 0 5px rgba(0,0,0,0.05); /* Sombra sutil na barra lateral */
    }

    /* Estilos para o cabeçalho do app */
    h1 {
        color: #6a0dad; /* Roxo vibrante */
        text-align: center;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin-bottom: 30px;
        font-size: 2.5em;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1); /* Sombra no título */
    }

    /* Estilos para a entrada de chat */
    .stTextInput > div > div > input {
        border-radius: 20px;
        border: 1px solid #6a0dad;
        padding: 10px 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        font-size: 1.1em;
        outline: none; /* Remove o contorno de foco padrão */
    }
    .stTextInput > div > div > input:focus {
        border-color: #9b59b6; /* Cor da borda ao focar */
        box-shadow: 2px 2px 8px rgba(106, 13, 173, 0.3); /* Sombra mais intensa ao focar */
    }
    .stTextInput > label {
        display: none;
    }

    /* Estilos para as mensagens do chat */
    [data-testid="chat-message-container"] {
        border-radius: 15px;
        padding: 15px 20px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        font-size: 1.05em;
    }
    [data-testid="chat-message-user"] {
        background-color: #e6e6fa; /* Lavanda suave para o usuário */
        text-align: right;
    }
    [data-testid="chat-message-assistant"] {
        background-color: #f8f8ff; /* Branco quase-lavanda para a assistente */
        text-align: left;
    }
    [data-testid="stVerticalBlock"] > div:nth-child(2) > div > div > div {
        max-width: 800px; /* Limita a largura do conteúdo principal para melhor leitura */
        margin: auto; /* Centraliza */
    }

    /* Imagem da Crystal - ajuste de margem e arredondamento */
    img {
        border-radius: 50%; /* Torna a imagem circular */
        border: 3px solid #6a0dad;
        display: block;
        margin: 0 auto 20px auto; /* Centraliza e adiciona margem inferior */
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); /* Sombra para a imagem */
    }

    /* Spinner de carregamento */
    .stSpinner {
        color: #6a0dad;
        font-size: 1.2em;
        text-align: center;
    }

    /* Ajuste para o chat_input em celulares (mantém fixo na parte inferior) */
    div.st-emotion-cache-1c7y2kl { /* Esta classe pode mudar, verificar com F12 */
        padding-bottom: 70px;
    }

    /* Estilo para links nas mensagens */
    a {
        color: #8a2be2; /* Um roxo mais vibrante para links */
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }

</style>
""", unsafe_allow_html=True)


st.title("Crystal: Sua Assistente Pessoal 🔮")
st.image(CRYSTAL_IMAGE_URL, width=150)


# Inicializar o histórico de chat para exibição no Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

# Inicializar o histórico de chat para o Gemini (formato específico do Gemini API)
if "gemini_history" not in st.session_state: 
    st.session_state.gemini_history = []
    # Prompt inicial para definir a persona da Crystal
    # Adicionado data e hora atuais no prompt para melhor contextualização da IA
    current_time = datetime.datetime.now().strftime("%H:%M %p")
    current_date = datetime.date.today().strftime("%d de %B de %Y")
    st.session_state.gemini_history.append({"role": "user", "parts": [f"Você é a Crystal, uma assistente pessoal amigável, prestativa e inteligente. Seu objetivo é ajudar o usuário com informações, pesquisas e tarefas diárias. Responda de forma concisa e útil, mantendo um tom educado e acessível. Quando não souber algo, admita e sugira uma busca na internet. A data atual é {current_date}. A hora atual é {current_time}. Sua localização principal é o Brasil."]})
    st.session_state.gemini_history.append({"role": "model", "parts": ["Olá! Eu sou a Crystal, sua assistente pessoal. Estou aqui para ajudar. Como posso ser útil hoje?"]})
    
    # Adicionar a mensagem inicial da Crystal ao histórico de exibição do Streamlit
    st.session_state.messages.append({"role": "assistant", "content": "Olá! Eu sou a Crystal, sua assistente pessoal. Estou aqui para ajudar. Como posso ser útil hoje?"})


# Exibir mensagens do histórico na interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Entrada de texto do usuário
user_input = st.chat_input("Pergunte algo à Crystal...")

if user_input:
    # Adicionar a mensagem do usuário ao histórico de exibição do Streamlit
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Adicionar a mensagem do usuário ao histórico do Gemini (para manter o contexto)
    st.session_state.gemini_history.append({"role": "user", "parts": [user_input]})

    # Obter resposta da Crystal
    with st.spinner("Crystal está pensando..."):
        crystal_response = crystal_respond(user_input, st.session_state.gemini_history)

    # Adicionar a resposta da Crystal ao histórico de exibição do Streamlit
    st.session_state.messages.append({"role": "assistant", "content": crystal_response})
    with st.chat_message("assistant"):
        st.write(crystal_response)
    
    # Adicionar a resposta da Crystal ao histórico do Gemini (para que o Gemini também se lembre de suas próprias respostas)
    st.session_state.gemini_history.append({"role": "model", "parts": [crystal_response]})


# --- Dicas e Informações na Barra Lateral ---
st.sidebar.markdown("---")
st.sidebar.header("Dicas para Interagir com a Crystal:")
st.sidebar.markdown("- **Tempo:** 'Qual o tempo em São Paulo?'")
st.sidebar.markdown("- **Data:** 'Que dia é hoje?' ou 'Qual a data de hoje?'")
st.sidebar.markdown("- **Hora:** 'Que horas são?'")
st.sidebar.markdown("- **Pesquisa na Internet:** 'Pesquisar por últimas notícias de tecnologia' ou 'Procure por receita de bolo de chocolate'.")
st.sidebar.markdown("- **Criar Lista:** 'Criar lista de compras com leite e pão' ou 'Criar lista de tarefas com arrumar quarto e lavar louça'.")
st.sidebar.markdown("- **Adicionar à Lista:** 'Adicionar ovos à lista de compras'.")
st.sidebar.markdown("- **Lembrete:** 'Me lembre de pegar o pão amanhã às 8 da manhã' ou 'Agendar reunião com João na quarta-feira às 10h'.")
st.sidebar.markdown("- **Notícias/Resumos:** 'Notícias sobre inteligência artificial' ou 'Resumir artigo sobre o espaço'.")
st.sidebar.markdown("- **Perguntas Gerais:** Faça qualquer pergunta, e a Crystal usará a inteligência do Gemini para responder!")

st.sidebar.markdown("---")
st.sidebar.warning("Lembre-se de configurar seu arquivo `.streamlit/secrets.toml` com suas chaves de API e o GOOGLE_CSE_ID!")
st.sidebar.info("As funcionalidades de listas, lembretes e resumo de artigos estão **simuladas** para demonstração das ferramentas. Para uma integração completa e persistente, elas precisariam de sistemas de banco de dados e APIs reais.")
