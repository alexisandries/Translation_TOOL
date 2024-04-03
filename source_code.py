import streamlit as st
import openai
import fitz  # PyMuPDF
from pptx import Presentation
from openpyxl import load_workbook
from docx import Document
import io
import os
from io import BytesIO
from openai import OpenAI
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

st.set_page_config(layout="wide")

openai_api_key  = st.secrets["OPENAI_API_KEY"]
mistral_api_key = st.secrets["MISTRAL_API_KEY"]
PASSWORD = st.secrets["MDM_PASSWORD"]

def read_pdf(file):
    text = ''
    # Convert Streamlit's UploadedFile to a bytes stream compatible with fitz
    bytes_stream = BytesIO(file.read())
    with fitz.open(stream=bytes_stream, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def read_pptx(file):
    text = ''
    prs = Presentation(file)
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + ' '
    return text

def read_excel(file):
    text = ''
    wb = load_workbook(filename=file)
    for sheet in wb:
        for row in sheet.iter_rows(values_only=True):
            for cell in row:
                text += str(cell) + ' '
    return text

def read_docx(file):
    doc = Document(file)
    return ' '.join([paragraph.text for paragraph in doc.paragraphs])


def run_model(messages, temp_choice, select_model):
     
    if select_model == 'MISTRAL large':        
        try:

            model = "mistral-large-latest"
            
            client_mistral = MistralClient(api_key=mistral_api_key)
                      
            # No streaming
            chat_response = client_mistral.chat(
                model=model,
                messages=messages,
                temperature=temp_choice
            )
            
            return chat_response.choices[0].message.content
            
        except Exception as e:
            return f"An error occurred: {e}"

    else: 
        if select_model == 'GPT 3.5':
            llm_model = 'gpt-3.5-turbo-0125'
        if select_model == 'GPT 4.0':
            llm_model = 'gpt-4-0125-preview'
        
        try:
            client = OpenAI()
            response = openai.chat.completions.create(
                model=llm_model,
                messages=messages,
                temperature=temp_choice
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"An error occurred: {e}"

    

def translate_to_français(text, from_language, temp_choice, select_model):
    """
    Translates text from one language to another with a specified style using OpenAI's API.
    """

    messages = [
        {"role":"system", "content": f""" Vous êtes un traducteur professionnel hautement qualifié, spécialisé dans le secteur des grandes ONG médicales, des droits humains et de la communication à haut impact. Vous avez une parfaite maîtrise de la langue source {from_language} et du français, avec une connaissance approfondie des nuances culturelles et terminologiques de ces langues."""},
        {"role":"user", "content": f"""
        Objectif : Traduire le texte suivant vers le français, en respectant les plus hauts standards de fiabilité, de fluidité, et d'adaptation culturelle. La traduction doit être fidèle au sens du texte source tout en étant naturellement compréhensible pour un locuteur natif de la langue cible.
        
        Directives spécifiques :
        1. **Fidélité et fiabilité** : Assurez-vous que la traduction reflète fidèlement le contenu, le sens et le ton du texte source. Évitez les omissions ou les ajouts non justifiés. Il est autorisé de s'écarter du texte source pour mieux s'accorder aux directives 2 à 5.  
        2. **Cohérence terminologique** : Utilisez la terminologie spécifique au domaine du texte, et assurez-vous que son usage est cohérent tout au long de la traduction. Consultez des glossaires spécialisés si nécessaire.
        3. **Adaptation culturelle** : Adaptez les références culturelles, les idiomes et les expressions spécifiques de manière à ce qu'elles soient pertinentes et compréhensibles dans la langue cible.
        4. **Lisibilité et naturel** : La traduction doit être extrêmement fluide et naturelle, comme si le texte avait été initialement écrit dans la langue cible. Prêtez attention à la syntaxe, au style et au rythme du texte pour garantir une lecture souple et convaincante.
        5. **Respect des conventions** : Suivez les conventions grammaticales, orthographiques et de ponctuation de la langue cible. Adaptez les formats de date, de monnaie et d'autres éléments spécifiques selon les normes en vigueur dans la culture cible.
        
        Texte à traduire :
        {text}
        
        Veuillez procéder à la traduction en tenant compte de toutes ces directives pour produire un texte qui réponde aux exigences d'une traduction professionnelle de haute qualité."""}  
    ]
    
    return run_model(messages, temp_choice, select_model)

def enhance_to_français(text, objectif, public_cible, temp_choice, select_model):

    messages = [
        {"role":"system", "content": """Assister l'expert en rédaction pour évaluer et améliorer le texte fourni. L'expert doit se concentrer sur l'élimination des indices de traduction, l'enrichissement du contenu, l'optimisation de la fluidité et l'authenticité linguistique, tout en ajustant le texte pour qu'il résonne profondément avec le public cible. Le processus comprend deux phases principales : une évaluation initiale suivie d'une amélioration basée sur cette évaluation."""},
        {"role":"user", "content": f"""
        
        L'objectif du texte est comme suit:
        {objectif}

        Le public cible est le suivant: 
        {public_cible}
        
        Veuillez suivre les étapes ci-dessous pour améliorer le texte :
        
        1. **Évaluation Initiale** : Identifiez les forces et les faiblesses du texte. Focus sur la clarté, la cohérence, les redondances et l'efficacité en adéquation avec les objectifs et publics-cible. 
        2. **Amélioration** : Sur la base de votre évaluation, procédez aux améliorations nécessaires. Assurez-vous de :
           - Éliminer les marques de traduction.
           - Améliorer la fluidité et l'authenticité.
           - Ajuster la structure, le contenu, le style, le ton et le choix des mots aux objectifs et public cible.
           - Adapter si nécessaire les expressions et les références culturelles.
    
        Texte à évaluer et à améliorer :
        {text}
        """}  
    ]
    
    return run_model(messages, temp_choice, select_model)


def refine_text(text, temp_choice, select_model, briefing, prompt):

    messages = [
        {"role":"system", "content":briefing},
        {"role":"user", "content":prompt}  
    ]

    return run_model(messages, temp_choice, select_model)


def main():
    
    select_model = st.sidebar.radio('**Select your MODEL**', ['GPT 3.5', 'GPT 4.0', 'MISTRAL large' ])
    
    if select_model != 'GPT 3.5':
        
        pass_word = st.sidebar.text_input('Enter the password:')
    
        if not pass_word:
            st.stop()
            
        elif pass_word != PASSWORD:
            st.error('The password you entered is incorrect.')
            st.stop()
    
        if pass_word == PASSWORD:
            pass
            
    tool_choice = st.sidebar.radio("**Choose your tool:**", ['Chat with LLM', 'Craft, Refine and Translate your text'])

    
    
    if tool_choice =='Chat with LLM':

       
        st.title("Chatbot")

        temp_choice = st.slider('Select a Temperature', min_value=0.0, max_value=1.0, step=0.1, key='llm_bot')

        if select_model == 'GPT 3.5':
            llm_model = 'gpt-3.5-turbo-0125'
            client = OpenAI()
        elif select_model == 'GPT 4.0':
            llm_model = 'gpt-4-0125-preview'
            client = OpenAI()
        else: 
            st.write('Please select an OpenAI model, we are working to get acces to Mistral')
            st.stop()

        st.write("**Selected model**:", select_model)       

        if "llm_model" not in st.session_state:
            st.session_state["llm_model"] = llm_model
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input():
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
        
            with st.chat_message("assistant"):
                stream = client.chat.completions.create(
                    model=st.session_state["llm_model"],
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    stream=True,
                )
                response = st.write_stream(stream)

            st.session_state.messages.append({"role": "assistant", "content": response})
        
        
        st.sidebar.markdown("---")       
        if st.session_state.messages:
            st.sidebar.write('**Manage Chat Session**')           
            
            chat_messages = '\n'.join(
                m['content'] for m in st.session_state.messages if 'content' in m and isinstance(m['content'], str)
            )

            st.sidebar.download_button(label="Download Session",
                           data=chat_messages,  
                           file_name="chat_messages.txt",
                           mime="text/plain")
            
            if st.sidebar.button('Restart session'):
                st.session_state.messages = []
                st.sidebar.success('Chat has been reset.')
                st.rerun()
        
    if tool_choice == 'Craft, Refine and Translate your text':
        
        st.subheader('Translate, Refine or Craft your text')
        tab1, tab2, tab3 = st.tabs(['TRANSLATE', 'REFINE', 'CRAFT'])
        
        with tab1: 
        
            # User input for translations
            col1, col2 = st.columns(2)
            with col1:
                from_language = st.selectbox('From Language', ['French', 'Dutch', 'English'], index=1)
            with col2:
                to_language = st.selectbox('To Language', ['Dutch', 'French', 'English'], index=1)
            
            temp_choice = st.slider('Select a Temperature', min_value=0.1, max_value=0.9, step=0.1, key='temp1')
        
            st.write("**Lower Temperature (~0.1 to 0.4):** Recommended for more secure translations.")
            st.write("**Higher Temperature (~0.6 to 0.9):** Encourages more creative translations.")
    
            # File upload
            uploaded_file = st.file_uploader("Upload file (PDF, PPTX, XLSX, DOCX)", type=['pdf', 'pptx', 'xlsx', 'docx'])
            text = ""
            
            if uploaded_file:
                if uploaded_file.type == "application/pdf":
                    text = read_pdf(uploaded_file)
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                    text = read_pptx(uploaded_file)
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    text = read_excel(uploaded_file)
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    text = read_docx(uploaded_file)
                st.text_area("Extracted Text", value=text, height=150, disabled=True)
            
            # Manual text input as an alternative to file upload
            text_input = st.text_area('Or enter text to translate', height=150)
        
            # Combine file text and manual text input if both are provided
            combined_text = text + "\n" + text_input     
            
            translated_text = None
            
            if 'central_file' not in st.session_state:
                st.session_state.central_file = []
            
            if 'last_text' not in st.session_state:
                st.session_state.last_text = None
            
            st.write("**Click to translate (uploaded or in box)**")
            if st.button('Translate'):
                
                if combined_text:
                    if to_language == 'French':
                        translated_text = translate_to_français(combined_text, from_language, temp_choice, select_model)
                   
                        st.session_state.last_text = f"{select_model}, Temp {temp_choice}, 'translated':\n\n{translated_text}"
                        st.write(translated_text)
                               
                else:
                    st.error('Please upload or paste a text to translate.')
                
           
            # This check ensures we only attempt to use 'last_text' if it's been defined
            if 'last_text' in st.session_state and st.session_state.last_text:
                
                st.write('**Enhance text (translation or latest in memory)**')
                objectif = st.text_input("Describe clearly and concisely the goal or objective of text (use language of target audience)")
                public_cible = st.text_input("Describe target audience")
                if st.button('Enhance'):
                    enhanced_text = enhance_to_français(st.session_state.last_text, objectif, public_cible, temp_choice, select_model)
                    st.session_state.last_text = f"{select_model}, Temp {temp_choice}, enhanced:\n\n{enhanced_text}"
                    st.write(st.session_state.last_text)
                    
    
                
                st.write('**Add text in memory to central file**')
                if st.button('Add to FILE'):
                    st.session_state.central_file.append(st.session_state.last_text)
                    st.success('Text added to central file!')
    
            # st.sidebar.markdown("---")
            st.sidebar.write("\n\n")
            if 'central_file' in st.session_state and st.session_state.central_file:
                st.sidebar.write('**Manage central file**')
                if st.sidebar.button('DISPLAY'):
                    st.write("Contents of the translations file:", st.session_state.central_file)
                
                
                translations_str = '\n'.join(st.session_state.central_file)  # Join list items into a string
                st.sidebar.download_button(label="DOWNLOAD",
                               data=translations_str,  
                               file_name="central_file.txt",
                               mime="text/plain")
                
                if st.sidebar.button('RESET'):
                    st.session_state.central_file = []
                    st.success('Translations file has been reset.')
    
                if 'last_text' in st.session_state:
                    # Find the index of the first colon
                    colon_index = st.session_state.last_text.find(':')
                    st.sidebar.write("\n\n")
                    st.sidebar.write('**Text in memory**') 
                    st.sidebar.write(st.session_state.last_text[:colon_index])
                     
    

        with tab2:
            st.subheader('Refine')

            st.write('#### Under construction')


        with tab3:
            st.subheader('Craft')

            st.write('#### Under construction')
            

if __name__ == "__main__":
    main()
