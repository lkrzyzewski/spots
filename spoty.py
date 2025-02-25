import os
import streamlit as st
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
#from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict
import functools
import operator
from pprint import pprint
from agents import Agents_prompts
import yaml
from yaml.loader import SafeLoader
import random

os.environ["GROQ_API_KEY"] = st.secrets["Groq_key"]
os.environ["OPENAI_API_KEY"] = st.secrets["OpenAI_key"]
os.environ["GOOGLE_API_KEY"]  = st.secrets["Gemini_key"]


st_auth_file = "auth.yaml"
afirmacje_file = "afirmacje.txt"


info_text ="""
***Llama3***  

***GPT4***  
Dobry model od OpenAI  

***Gemini***  
Dobry model od Google  

"""

class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    czas: str
    base_info: str
    sugestje: str
    marketing: str
    koncepcja: str
    scenariusz: str
    krytyka: str
    finalcopy: str
    
def create_agent(llm, system_prompt: str, task_prompt: str):
# Each worker node will be given a name and some tools.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt,
            ),
            (
                "human",
                task_prompt
            ),
        ]
    )
    agent = prompt | llm | StrOutputParser()
    return agent 

if 'clicked' not in st.session_state:
    st.session_state.clicked = False

def set_clicked():
    st.session_state.clicked = True

st.set_page_config(page_title="Spoty AI",page_icon="🤖", layout="wide")

with open(st_auth_file) as file:
    authconf = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    authconf['credentials'],
    authconf['cookie']['name'],
    authconf['cookie']['key'],
    authconf['cookie']['expiry_days']
)
username = authenticator.login('main')
if st.session_state["authentication_status"]:
    with st.sidebar:
        st.divider()
        #st.radio("Wybierz model językowy", ["Llama3", "GPT4", "Gemini"], key="model")
        st.radio("Wybierz model językowy", ["Llama3", "GPT4", "Gemini"], key="model")
        st.divider()
        st.markdown(info_text)
        st.divider()
        authenticator.logout()
    
    st.header(f'*Witaj*', divider='blue')
    with st.form("dane_form"):
        czas_pl="czas trwania spotu 20 sekund, tempo 1 słowo na sekundę"
        sugestje_pl="np. spot ma być w formie dilogu\nzawierac informacje o produkcie ..."
        dane_pl = "Radio Fama\nZielonka ul Wileńska 44\n\nRadio Fama jest radiem lokalnym..."
        st.text_input("Czas twania spotu", placeholder=czas_pl, key='czas_txt')
        st.text_area("Sugestje", placeholder=sugestje_pl,key='sugestie_txt', height=100)
        st.text_area("Dane, powiny zawierać nazwę firmy i dane kontaktowe.",placeholder=dane_pl ,key='dane_txt', height=250)
        st.form_submit_button('Wygeneruj spot', on_click=set_clicked)
        if st.session_state.clicked:
            if st.session_state["model"] == "Llama3":
                llm = ChatGroq(temperature=0.9,model_name="Llama3-70b-8192")
            elif st.session_state["model"] == "GPT4":
                llm = ChatOpenAI(temperature=0.9,model_name="gpt-4o")
            elif st.session_state["model"] == "Gemini":
                llm = ChatGoogleGenerativeAI(model="gemini2-flash", transport="grpc")
                #llm = ChatGoogleGenerativeAI(model="gemini-1.0-pro", transport="grpc")
        
            czas = st.session_state.czas_txt
            sugestje = st.session_state.sugestie_txt 
            base_info = st.session_state.dane_txt

            Agents_prompts = Agents_prompts()

            marketing_agent = create_agent(llm, Agents_prompts.marketing_system, Agents_prompts.marketing_task)
            koncept_agent = create_agent(llm, Agents_prompts.koncept_system, Agents_prompts.koncept_task)
            copy_agent = create_agent(llm, Agents_prompts.copy_system, Agents_prompts.copy_task)
            krytyk_agent = create_agent(llm, Agents_prompts.krytyk_system, Agents_prompts.krytyk_task)
            finalcopy_agent = create_agent(llm, Agents_prompts.copy_system, Agents_prompts.finalcopy_task)


            def marketing_node(state):
                czas = state['czas']
                base_info = state['base_info']
                sugestje = state['sugestje']
                marketing = marketing_agent.invoke({"czas": czas, "base_info": base_info, "sugestje": sugestje})
                return {"marketing": marketing}

            def koncept_node(state):
                czas = state['czas']
                sugestje = state['sugestje']
                marketing = state['marketing']
                koncepcja = koncept_agent.invoke({"czas": czas, "sugestje": sugestje, "marketing": marketing})
                return {"koncepcja": koncepcja}

            def copy_node(state):
                czas = state['czas']
                sugestje = state['sugestje']
                koncepcja = state['koncepcja']
                scenariusz = copy_agent.invoke({"czas": czas,  "koncepcja": koncepcja, "sugestje": sugestje,})
                return {"scenariusz": scenariusz}

            def krytyka_node(state):
                czas = state['czas']
                sugestje = state['sugestje']
                scenariusz = state['scenariusz']
                krytyka = krytyk_agent.invoke({"czas": czas, "sugestje": sugestje, "scenariusz": scenariusz})
                return {"krytyka": krytyka}

            def finalcopy_node(state):
                czas = state['czas']
                sugestje = state['sugestje']
                krytyka = state['krytyka']
                scenariusz = state['scenariusz']
                finalcopy = finalcopy_agent.invoke({"czas": czas, "sugestje": sugestje, "scenariusz": scenariusz, "krytyka": krytyka})
                return {"finalcopy": finalcopy}

            workflow = StateGraph(AgentState)
            workflow.add_node("marketing_node", marketing_node)
            workflow.add_node("koncept_node", koncept_node)
            workflow.add_node("copy_node", copy_node)
            workflow.add_node("krytyka_node", krytyka_node)
            workflow.add_node("finalcopy_node", finalcopy_node)

            workflow.add_edge("marketing_node", "koncept_node")
            workflow.add_edge("koncept_node", "copy_node")
            workflow.add_edge("copy_node", "krytyka_node")
            workflow.add_edge("krytyka_node", "finalcopy_node")
            workflow.add_edge("finalcopy_node", END)

            workflow.set_entry_point("marketing_node")

            graph = workflow.compile()
            inputs = {"czas": czas, "base_info": base_info, "sugestje": sugestje}
            
            with st.status("🤖 **AI is working...**", state="running", expanded=True) as status:
                with st.container(height=500, border=True):
                    for output in graph.stream(inputs):
                        for key, value in output.items():
                            keys = value.keys()
                            values = value.values()
                            for k in keys:
                                st.markdown(f"***:red[{k.upper()}:]***")
                            for v in values:
                                st.markdown(v)
            status.update(label="✅ Propozycja spotu gotowa", state="complete", expanded=True)
            st.session_state.clicked = False