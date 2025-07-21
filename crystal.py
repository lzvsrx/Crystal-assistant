import streamlit as st
import datetime
import requests
import json
import google.generativeai as genai
import re
import os # Para verificar a existência de arquivos

# --- Configurações Iniciais ---
st.set_page_config(page_title="Crystal - Sua Assistente Pessoal", layout="centered")

# URL da imagem da Crystal
CRYSTAL_IMAGE_URL = "https://via.placeholder.com/150"

# --- Carregar Chaves de API de st.secrets com Tratamento de Erros ---
OPENWEATHER_API_KEY = None
Google_Search_API_KEY = None
GOOGLE_CSE_ID = None
GEMINI_API_KEY = None

secrets_file_path = "secrets.toml"

if not os.path.exists(secrets_file_path):
    st.error(f"Erro: O arquivo de segredos '{secrets_file_path}' não foi encontrado. "
             "Por favor, crie-o conforme as instruções e adicione suas chaves de API.")
    st.stop() # Interrompe a execução se o arquivo não existe

try:
    OPENWEATHER_API_KEY = st.secrets["OPENWEATHER_API_KEY"]
    Google_Search_API_KEY = st.secrets["Google Search_API_KEY"]
    GOOGLE_CSE_ID = st.secrets["GOOGLE_CSE_ID"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError as e:
    st.error(f"Erro: Chave de API '{e}' não encontrada em '{secrets_file_path}'. "
             "Verifique se o nome da chave está correto e se ela foi adicionada ao arquivo.")
    st.stop()
except Exception as e:
    st.error(f"Ocorreu um erro inesperado ao carregar as chaves de API: {e}")
    st.stop()


# Configurar o modelo Gemini com tratamento de erro
try:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Erro ao configurar o modelo Gemini: {e}. Verifique sua GEMINI_API_KEY.")
    st.stop()

# --- Funções de API com Tratamento de Erros ---

def get_gemini_response(prompt_text, chat_history):
    """Obtém uma resposta do modelo Gemini, mantendo o histórico da conversa."""
    if not GEMINI_API_KEY:
        return "Desculpe, a chave da API do Gemini não está configurada corretamente. Não posso responder no momento."
    try:
        chat = GEMINI_MODEL.start_chat(history=chat_history)
        response = chat.send_message(prompt_text)
        return response.text
    except genai.types.BlockedPromptException:
        return "Sua solicitação foi bloqueada devido a políticas de segurança. Por favor, tente algo diferente."
    except genai.types.APIError as e:
        st.error(f"Erro na API do Gemini: {e}")
        return "Desculpe, tive um problema ao me comunicar com a IA. Pode tentar novamente?"
    except Exception as e:
        st.error(f"Erro inesperado ao obter resposta do Gemini: {e}")
        return "Desculpe, algo deu errado enquanto eu pensava. Tente novamente mais tarde."

def get_weather(city):
    """Busca informações meteorológicas para uma cidade usando a API OpenWeatherMap."""
    if not OPENWEATHER_API_KEY:
        return "Desculpe, a chave da API do OpenWeatherMap não está configurada."
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}appid={OPENWEATHER_API_KEY}&q={city}&units=metric&lang=pt_br"
    try:
        response = requests.get(complete_url)
        response.raise_for_status() # Lança HTTPError para códigos de status 4xx/5xx
        data = response.json()
        
        if data.get("cod") == 200:
            main = data["main"]
            weather = data["weather"][0]
            temperature = main["temp"]
            description = weather["description"]
            return f"O tempo em {city.capitalize()} é de {temperature:.1f}°C com {description.capitalize()}."
        elif data.get("cod") == "404":
            return "Não consegui encontrar informações de tempo para essa cidade. Verifique o nome e tente novamente."
        else:
            return f"Erro ao buscar o tempo: {data.get('message', 'Erro desconhecido')}. Código: {data.get('cod', 'N/A')}"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "Erro de autenticação na API do tempo. Verifique sua OPENWEATHER_API_KEY."
        elif e.response.status_code == 404:
            return "Não consegui encontrar informações de tempo para essa cidade. Verifique o nome e tente novamente."
        return f"Erro HTTP ao buscar o tempo: {e.response.status_code} - {e.response.reason}"
    except requests.exceptions.ConnectionError:
        return "Não foi possível conectar ao serviço de tempo. Verifique sua conexão com a internet."
    except requests.exceptions.Timeout:
        return "A requisição de tempo demorou muito e expirou. Tente novamente."
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão geral ao buscar o tempo: {e}")
        return "Erro de conexão ao buscar o tempo. Verifique sua internet ou tente mais tarde."
    except json.JSONDecodeError:
        return "Erro ao processar a resposta do serviço de tempo. O formato dos dados está inválido."
    except Exception as e:
        st.error(f"Erro inesperado em get_weather: {e}")
        return "Ocorreu um erro inesperado ao buscar o tempo. Tente novamente."


def Google_Search(query):
    """Realiza uma busca na internet usando a Google Custom Search API."""
    if not Google_Search_API_KEY or not GOOGLE_CSE_ID:
        return "Desculpe, as chaves da API de busca do Google (ou o CSE ID) não estão configuradas."
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": Google_Search_API_KEY, "cx": GOOGLE_CSE_ID, "q": query}
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status() # Lança HTTPError para códigos de status 4xx/5xx
        results = response.json()
        if "items" in results:
            return results["items"]
        elif "error" in results:
            error_message = results["error"].get("message", "Erro desconhecido da API de busca.")
            error_code = results["error"].get("code", "N/A")
            if error_code == 403:
                return "Erro de acesso à API de busca. Verifique se sua Google Search_API_KEY e GOOGLE_CSE_ID estão corretos e se você habilitou a API Custom Search no Google Cloud."
            return f"Erro da API de busca: {error_message} (Código: {error_code})"
        else:
            return None # Não há itens, mas também não há erro explícito
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            return "Requisição de busca inválida. O parâmetro 'q' (query) pode estar faltando ou incorreto."
        elif e.response.status_code == 403:
             return "Erro de acesso à API de busca. Verifique se sua Google Search_API_KEY e GOOGLE_CSE_ID estão corretos e se você habilitou a API Custom Search no Google Cloud."
        return f"Erro HTTP ao realizar a busca: {e.response.status_code} - {e.response.reason}"
    except requests.exceptions.ConnectionError:
        return "Não foi possível conectar ao serviço de busca. Verifique sua conexão com a internet."
    except requests.exceptions.Timeout:
        return "A requisição de busca demorou muito e expirou. Tente novamente."
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão geral ao realizar a busca: {e}")
        return "Erro de conexão ao realizar a busca. Verifique sua internet ou tente mais tarde."
    except json.JSONDecodeError:
        return "Erro ao processar a resposta do serviço de busca. O formato dos dados está inválido."
    except Exception as e:
        st.error(f"Erro inesperado em Google Search: {e}")
        return "Ocorreu um erro inesperado ao realizar a busca. Tente novamente."


# --- Funções para Novas Funcionalidades (Simuladas) ---

def create_or_add_list_item(user_input):
    user_input_lower = user_input.lower()
    
    match_create = re.search(r"criar lista de (tarefas|compras|(.+?)) com (.+)", user_input_lower)
    if match_create:
        list_name_raw = match_create.group(1) if match_create.group(1) else match_create.group(2)
        list_name = list_name_raw.strip()
        items_str = match_create.group(3)
        items = [item.strip() for item in items_str.split(' e ') if item.strip()]
        if not list_name or not items:
            return "Não entendi o nome da lista ou os itens. Tente 'criar lista de compras com leite e pão'."
        return f"Criei a lista '{list_name.capitalize()}' com os itens: {', '.join(items)}. (Simulado)"

    match_add = re.search(r"adicionar (.+?) à lista de (tarefas|compras|(.+))", user_input_lower)
    if match_add:
        item_to_add = match_add.group(1).strip()
        list_name_raw = match_add.group(2) if match_add.group(2) else match_add.group(3)
        list_name = list_name_raw.strip()
        if not item_to_add or not list_name:
            return "Não entendi o item a adicionar ou o nome da lista. Tente 'adicionar ovos à lista de compras'."
        return f"Adicionei '{item_to_add}' à sua lista de '{list_name.capitalize()}'. (Simulado)"
        
    return None

def create_reminder_or_appointment(user_input):
    user_input_lower = user_input.lower()
    current_datetime = datetime.datetime.now()
    today = current_datetime.date()
    
    match = re.search(r"(?:me lembre de|agendar|criar lembrete para) (.+?) (amanhã|hoje|quarta-feira|terça-feira|quinta-feira|sexta-feira|sábado|domingo|dia \d{1,2}/\d{1,2}(?:/\d{4})?) *(?:às|as)? *(\d{1,2}(?:h|\:\d{2})?) *(da manhã|da tarde|da noite|pm|am)?", user_input_lower)
    
    if match:
        title = match.group(1).strip()
        when_str = match.group(2).strip()
        time_str = match.group(3) 
        am_pm_str = match.group(4)
        
        start_date = today
        time_of_day = None
        am_pm_or_unknown = "UNKNOWN"

        try:
            # Parsing da data
            if "amanhã" in when_str: start_date += datetime.timedelta(days=1)
            elif "hoje" in when_str: start_date = today
            elif "dia" in when_str:
                date_parts_match = re.search(r"dia (\d{1,2}/\d{1,2}(?:/\d{4})?)", when_str)
                if date_parts_match:
                    date_val = date_parts_match.group(1)
                    if len(date_val.split('/')) == 2: date_val += f"/{today.year}"
                    parsed_date = datetime.datetime.strptime(date_val, "%d/%m/%Y").date()
                    if parsed_date < today: parsed_date = parsed_date.replace(year=today.year + 1)
                    start_date = parsed_date
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
                        except ValueError: pass # Ignora se o tempo não puder ser parseado aqui
                    start_date += datetime.timedelta(days=days_diff)

            # Parsing do tempo
            if time_str:
                time_str = time_str.replace('h', ':00')
                if ':' not in time_str: time_str += ':00'

                hour = int(time_str.split(':')[0])
                minute = int(time_str.split(':')[1]) if ':' in time_str else 0

                if am_pm_str:
                    if "pm" in am_pm_str and hour < 12: hour += 12; am_pm_or_unknown = "PM"
                    elif "am" in am_pm_str and hour == 12: hour = 0; am_pm_or_unknown = "AM"
                    else: am_pm_or_unknown = am_pm_str.upper()
                
                if not am_pm_str and start_date == today:
                    now_hour = current_datetime.hour
                    if hour < now_hour:
                        if hour <= 12: hour += 12; am_pm_or_unknown = "PM"

                time_of_day = f"{hour:02d}:{minute:02d}:00"
                
                combined_dt = datetime.datetime(start_date.year, start_date.month, start_date.day, hour, minute, 0)
                if combined_dt < current_datetime:
                    return "Desculpe, não consigo criar lembretes para o passado. Por favor, especifique uma data e/ou hora futura."

            date_display = start_date.strftime("%d/%m/%Y")
            time_display = time_of_day if time_of_day else "em algum momento do dia"
            am_pm_display = f" ({am_pm_or_unknown})" if am_pm_or_unknown != "UNKNOWN" and time_of_day else ""

            return f"Lembrete criado: '{title.capitalize()}' para {date_display} às {time_display}{am_pm_display}. (Simulado)"
        except ValueError:
            return "Não entendi a data ou hora do lembrete. Por favor, especifique de forma mais clara (ex: 'amanhã às 10h', 'dia 25/12 às 14:30')."
        except Exception as e:
            st.error(f"Erro ao processar lembrete: {e}")
            return "Desculpe, houve um erro ao tentar criar o lembrete. Tente novamente."
    
    return None

def get_news_summary(query):
    search_results = Google Search(query)
    if not search_results or isinstance(search_results, str): # Verifica se é uma string de erro
        return search_results if isinstance(search_results, str) else f"Não encontrei notícias ou artigos sobre '{query}'. Tente um termo diferente."
    
    first_link = None
    for item in search_results:
        if item.get('link') and item.get('mime') and 'text/html' in item['mime']:
            first_link = item['link']
            break
    
    if first_link:
        # Placeholder for web scraping and summarization
        return f"Encontrei notícias sobre '{query}'. O primeiro resultado é: '{search_results[0].get('title', 'Sem título')}' ([Link]({first_link})). " \
               "Se eu pudesse acessar o conteúdo, faria um resumo para você! (Simulado)"
    else:
        return "Não consegui encontrar um link de artigo HTML válido para resumir."

# --- Função de Placeholder para Banco de Dados RAG ---
def search_rag_database(query):
    return "Desculpe, a funcionalidade de banco de dados RAG ainda não está totalmente implementada. Mas estou aprendendo a usar meus próprios dados!"


# --- Lógica Principal da Crystal para Responder com Tratamento de Erros ---

def crystal_respond(user_input, chat_history_for_gemini):
    user_input_lower = user_input.lower()

    # Prioridade para comandos específicos:
    # 1. Comandos de Listas (Tarefas/Compras)
    response_list = create_or_add_list_item(user_input)
    if response_list: return response_list

    # 2. Comandos de Lembretes/Agendamentos
    response_reminder = create_reminder_or_appointment(user_input)
    if response_reminder: return response_reminder

    # 3. Comandos de Notícias/Resumos
    if "notícias sobre" in user_input_lower or "resumo de artigo sobre" in user_input_lower or "resumir artigo" in user_input_lower:
        query = user_input_lower.replace("notícias sobre", "").replace("resumo de artigo sobre", "").replace("resumir artigo", "").strip()
        if query: return get_news_summary(query)
        else: return "Por favor, especifique sobre o que você quer notícias ou qual artigo resumir."

    # 4. Comandos de Tempo e Data
    if "tempo em" in user_input_lower:
        city = user_input_lower.split("tempo em")[-1].strip()
        if city: return get_weather(city)
        else: return "Por favor, especifique a cidade para a qual você quer o tempo."
    elif "que dia é hoje" in user_input_lower or "data de hoje" in user_input_lower:
        today = datetime.date.today().strftime("%d/%m/%Y")
        return f"Hoje é {today}."
    elif "que horas são" in user_input_lower:
        now = datetime.datetime.now().strftime("%H:%M")
        return f"São {now}."
    elif "pesquisar por" in user_input_lower or "pesquise por" in user_input_lower or "procure por" in user_input_lower:
        search_query = user_input_lower.replace("pesquisar por", "").replace("pesquise por", "").replace("procure por", "").strip()
        if search_query:
            results = (Google Search_query)
            if results and not isinstance(results, str): # Verifica se há resultados e não é uma mensagem de erro
                top_result = results[0]
                title = top_result.get('title', 'Sem título')
                snippet = top_result.get('snippet', 'Sem descrição')
                link = top_result.get('link', 'Sem link')
                return f"Encontrei: **{title}** - {snippet} ([Link]({link}))"
            elif isinstance(results, str): # Se for uma mensagem de erro da busca
                return results
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
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f8ff; color: #333333; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; color: #333333; border-right: 1px solid #e0e0e0; box-shadow: 2px 0 5px rgba(0,0,0,0.05); }
    h1 { color: #6a0dad; text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin-bottom: 30px; font-size: 2.5em; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
    .stTextInput > div > div > input { border-radius: 20px; border: 1px solid #6a0dad; padding: 10px 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); font-size: 1.1em; outline: none; }
    .stTextInput > div > div > input:focus { border-color: #9b59b6; box-shadow: 2px 2px 8px rgba(106, 13, 173, 0.3); }
    .stTextInput > label { display: none; }
    [data-testid="chat-message-container"] { border-radius: 15px; padding: 15px 20px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); font-size: 1.05em; }
    [data-testid="chat-message-user"] { background-color: #e6e6fa; text-align: right; }
    [data-testid="chat-message-assistant"] { background-color: #f8f8ff; text-align: left; }
    [data-testid="stVerticalBlock"] > div:nth-child(2) > div > div > div { max-width: 800px; margin: auto; }
    img { border-radius: 50%; border: 3px solid #6a0dad; display: block; margin: 0 auto 20px auto; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    .stSpinner { color: #6a0dad; font-size: 1.2em; text-align: center; }
    div.st-emotion-cache-1c7y2kl { padding-bottom: 70px; }
    a { color: #8a2be2; text-decoration: none; }
    a:hover { text-decoration: underline; }
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
    current_time_str = datetime.datetime.now().strftime("%H:%M %p")
    current_date_str = datetime.date.today().strftime("%d de %B de %Y")
    st.session_state.gemini_history.append({"role": "user", "parts": [f"Você é a Crystal, uma assistente pessoal amigável, prestativa e inteligente. Seu objetivo é ajudar o usuário com informações, pesquisas e tarefas diárias. Responda de forma concisa e útil, mantendo um tom educado e acessível. Quando não souber algo, admita e sugira uma busca na internet. A data atual é {current_date_str}. A hora atual é {current_time_str}. Sua localização principal é o Brasil."]})
    
    initial_assistant_message = "Olá! Eu sou a Crystal, sua assistente pessoal. Estou aqui para ajudar. Como posso ser útil hoje?"
    st.session_state.gemini_history.append({"role": "model", "parts": [initial_assistant_message]})
    st.session_state.messages.append({"role": "assistant", "content": initial_assistant_message})

# Exibir mensagens do histórico na interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Entrada de texto do usuário
user_input = st.chat_input("Pergunte algo à Crystal...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    st.session_state.gemini_history.append({"role": "user", "parts": [user_input]})

    with st.spinner("Crystal está pensando..."):
        crystal_response = crystal_respond(user_input, st.session_state.gemini_history)

    st.session_state.messages.append({"role": "assistant", "content": crystal_response})
    with st.chat_message("assistant"):
        st.write(crystal_response)
    
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
