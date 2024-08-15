import streamlit as st
import openai
import fitz  # PyMuPDF
from pptx import Presentation
from openpyxl import load_workbook
from docx import Document
from io import BytesIO
from openai import OpenAI
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from langchain.prompts import PromptTemplate
import langdetect

# Configuration
st.set_page_config(layout="wide")

# Constants
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
MISTRAL_API_KEY = st.secrets["MISTRAL_API_KEY"]
PASSWORD = st.secrets["MDM_PASSWORD"]

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

# Utility functions
def read_pdf(file):
    text = ''
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

def detect_language(text):
    try:
        return langdetect.detect(text)
    except:
        return "Unable to detect language"

# Model-specific functions
def run_openai_model(messages, temp_choice):
    try:
        response = openai_client.chat.completions.create(
            model='gpt-4',
            messages=messages,
            temperature=temp_choice
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred with OpenAI: {e}"

def run_mistral_model(messages, temp_choice):
    try:
        chat_response = mistral_client.chat(
            model="mistral-large-latest",
            messages=messages,
            temperature=temp_choice
        )
        return chat_response.choices[0].message.content
    except Exception as e:
        return f"An error occurred with Mistral: {e}"

def run_model(messages, temp_choice, select_model):
    if select_model == 'MISTRAL large':
        return run_mistral_model(messages, temp_choice)
    else:
        return run_openai_model(messages, temp_choice)

# Translation process functions
def analyze_source_text(text, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["source_text"],
        template="""
        You are a skilled linguistic analyst. Analyze the given text and provide insights for translation. Focus on:
        1. Idioms, colloquialisms, or culturally specific references
        2. Tone and register of the text
        3. Ambiguous phrases or words with multiple meanings
        4. Specialized terminology or jargon

        Source text: {source_text}

        Please provide your analysis:
        """
    )
    return run_model([{"role": "user", "content": prompt.format(source_text=text)}], temp_choice, select_model)

def translate_text(text, analysis, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["source_text", "analysis", "target_language"],
        template="""
        You are an expert translator. Translate the given text to {target_language}. Use the provided analysis to inform your translation. Pay attention to:
        1. Maintaining the original meaning and intent
        2. Preserving the tone and register
        3. Adapting idioms and cultural references appropriately
        4. Ensuring clarity and naturalness in the target language

        Source text: {source_text}

        Analysis: {analysis}

        Target language: {target_language}

        Please provide your translation:
        """
    )
    return run_model([{"role": "user", "content": prompt.format(source_text=text, analysis=analysis, target_language=target_language)}], temp_choice, select_model)

def edit_translation(translated_text, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["translated_text", "target_language"],
        template="""
        You are a skilled editor specializing in {target_language}. Refine and improve the given translation. Focus on:
        1. Ensuring grammatical correctness and idiomatic usage
        2. Improving fluency and naturalness of expression
        3. Maintaining consistency in terminology and style
        4. Adapting the text to be culturally appropriate for the target audience

        Translated text: {translated_text}

        Target language: {target_language}

        Please provide your edited version:
        """
    )
    return run_model([{"role": "user", "content": prompt.format(translated_text=translated_text, target_language=target_language)}], temp_choice, select_model)

def process_feedback(translated_text, human_feedback, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["translated_text", "human_feedback", "target_language"],
        template="""
        You are a skilled editor and translator specializing in {target_language}. Refine the translation based on human feedback. 

        Current translation: {translated_text}

        Human feedback: {human_feedback}

        Please provide:
        1. Your revised translation
        2. A brief explanation of the changes you made (2-3 sentences)
        3. A confidence score (1-10) for your revised translation, where 1 is least confident and 10 is most confident

        Format your response as follows:
        Revised Translation: [Your revised translation here]
        Explanation: [Your explanation here]
        Confidence: [Your confidence score here]
        """
    )
    return run_model([{"role": "user", "content": prompt.format(translated_text=translated_text, human_feedback=human_feedback, target_language=target_language)}], temp_choice, select_model)

def parse_feedback_response(response):
    lines = response.split('\n')
    revised_translation = lines[0].replace('Revised Translation:', '').strip()
    explanation = lines[1].replace('Explanation:', '').strip()
    confidence = int(lines[2].replace('Confidence:', '').strip())
    return revised_translation, explanation, confidence

# UI functions
def display_file_uploader():
    uploaded_file = st.file_uploader("Upload file (PDF, PPTX, XLSX, DOCX)", type=['pdf', 'pptx', 'xlsx', 'docx'])
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            return read_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            return read_pptx(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return read_excel(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return read_docx(uploaded_file)
    return ""

def display_text_input():
    return st.text_area('Or enter text to translate', height=150)

def display_language_selection(key_suffix):
    return st.selectbox('To Language', ['Dutch', 'French', 'English'], index=1, key=f'to_lang_{key_suffix}')

def display_temperature_slider(key_suffix):
    return st.slider('Select a Temperature', min_value=0.1, max_value=1.0, step=0.1, key=f'temp_{key_suffix}')

# Main app logic
def main():
    st.sidebar.title("Translation App")
    pass_word = st.sidebar.text_input('Enter the password:', type="password")
    if not pass_word:
        st.stop()
    if pass_word != PASSWORD:
        st.error('The password you entered is incorrect.')
        st.stop()

    select_model = st.sidebar.radio('**Select your MODEL**', ['GPT 4.0', 'MISTRAL large'])
    tool_choice = st.sidebar.radio("**Choose your tool:**", ['Translate with enhancement', 'Multiagent translation with feedback'])

    if tool_choice == 'Translate with enhancement':
        translate_with_enhancement(select_model)
    elif tool_choice == 'Multiagent translation with feedback':
        multiagent_translation(select_model)

    manage_central_file()

def translate_with_enhancement(select_model):
    st.subheader('Translate and upgrade your text')
    
    to_language = display_language_selection('enhance')
    temp_choice = display_temperature_slider('enhance')

    file_text = display_file_uploader()
    manual_text = display_text_input()
    
    combined_text = file_text + "\n" + manual_text if file_text or manual_text else None

    if st.button('Translate'):
        if combined_text:
            source_lang = detect_language(combined_text)
            st.write(f"Detected language: {source_lang}")
            translated_text = translate_text(combined_text, "", to_language, temp_choice, select_model)
            st.session_state.last_text = f"{select_model}, Temp {temp_choice}, 'translated':\n\n{translated_text}"
            st.write(translated_text)
        else:
            st.error('Please upload or paste a text to translate.')

    if 'last_text' in st.session_state and st.session_state.last_text:
        st.write('**Enhance text (translation or latest in memory)**')
        objectif = st.text_input("Describe the purpose of the text and/or add guidelines for enhancement.")
        public_cible = st.text_input("Describe target audience")
        
        if st.button('Enhance'):
            enhanced_text = edit_translation(st.session_state.last_text, to_language, temp_choice, select_model)
            st.session_state.last_text = f"{select_model}, Temp {temp_choice}, enhanced:\n\n{enhanced_text}"
            st.write(st.session_state.last_text)

def multiagent_translation(select_model):
    st.subheader('Multiagent Translation with Human Feedback')

    to_language = display_language_selection('multi')
    temp_choice = display_temperature_slider('multi')

    file_text = display_file_uploader()
    manual_text = display_text_input()
    
    combined_text = file_text + "\n" + manual_text if file_text or manual_text else None

    if 'multiagent_translation' not in st.session_state:
        st.session_state.multiagent_translation = ""
        st.session_state.feedback_round = 0

    if st.button('Start Multiagent Translation'):
        if combined_text:
            source_lang = detect_language(combined_text)
            st.write(f"Detected language: {source_lang}")
            
            analysis = analyze_source_text(combined_text, temp_choice, select_model)
            translation = translate_text(combined_text, analysis, to_language, temp_choice, select_model)
            edited_translation = edit_translation(translation, to_language, temp_choice, select_model)
            
            st.session_state.multiagent_translation = edited_translation
            st.session_state.feedback_round = 0
        else:
            st.error('Please upload or paste a text to translate.')

    if st.session_state.multiagent_translation:
        st.write("Current translation:")
        st.write(st.session_state.multiagent_translation)

        human_feedback = st.text_area("Provide feedback for improvement (or leave empty if satisfied):", key=f"feedback_{st.session_state.feedback_round}")
        
        if st.button("Submit Feedback", key=f"submit_{st.session_state.feedback_round}"):
            if human_feedback.strip():
                feedback_response = process_feedback(st.session_state.multiagent_translation, human_feedback, to_language, temp_choice, select_model)
                revised_translation, explanation, confidence = parse_feedback_response(feedback_response)
                st.write(f"Revised translation: {revised_translation}")
                st.write(f"Explanation: {explanation}")
                st.write(f"Confidence score: {confidence}")
                st.session_state.multiagent_translation = revised_translation
                st.session_state.feedback_round += 1
                st.experimental_rerun()
            else:
                st.success("Translation process completed!")
                st.session_state.last_text = f"{select_model}, Temp {temp_choice}, multiagent translated:\n\n{st.session_state.multiagent_translation}"

    if st.session_state.multiagent_translation:
        if st.button('Add to FILE'):
            if 'central_file' not in st.session_state:
                st.session_state.central_file = []
            st.session_state.central_file.append(st.session_state.last_text)
            st.success('Text added to central file!')

def manage_central_file():
    st.sidebar.write("\n\n")
    if 'central_file' in st.session_state and st.session_state.central_file:
        st.sidebar.write('**Manage central file**')
        if st.sidebar.button('DISPLAY'):
            st.write("Contents of the translations file:", st.session_state.central_file)
        
        translations_str = '\n'.join(st.session_state.central_file)
        st.sidebar.download_button(label="DOWNLOAD",
                       data=translations_str,
                       file_name="central_file.txt",
                       mime="text/plain")
        
        if st.sidebar.button('RESET'):
            st.session_state.central_file = []
            st.success('Translations file has been reset.')

if __name__ == "__main__":
    main()









# import streamlit as st
# import openai
# import fitz  # PyMuPDF
# from pptx import Presentation
# from openpyxl import load_workbook
# from docx import Document
# import io
# import os
# from io import BytesIO
# from openai import OpenAI
# from mistralai.client import MistralClient
# from mistralai.models.chat_completion import ChatMessage
# from langchain.prompts import PromptTemplate

# st.set_page_config(layout="wide")

# openai.api_key = st.secrets["OPENAI_API_KEY"]
# mistral_api_key = st.secrets["MISTRAL_API_KEY"]

# def read_pdf(file):
#     text = ''
#     # Convert Streamlit's UploadedFile to a bytes stream compatible with fitz
#     bytes_stream = BytesIO(file.read())
#     with fitz.open(stream=bytes_stream, filetype="pdf") as doc:
#         for page in doc:
#             text += page.get_text()
#     return text

# def read_pptx(file):
#     text = ''
#     prs = Presentation(file)
#     for slide in prs.slides:
#         for shape in slide.shapes:
#             if hasattr(shape, "text"):
#                 text += shape.text + ' '
#     return text

# def read_excel(file):
#     text = ''
#     wb = load_workbook(filename=file)
#     for sheet in wb:
#         for row in sheet.iter_rows(values_only=True):
#             for cell in row:
#                 text += str(cell) + ' '
#     return text

# def read_docx(file):
#     doc = Document(file)
#     return ' '.join([paragraph.text for paragraph in doc.paragraphs])


# def run_model(messages, temp_choice, select_model):
     
#     if select_model == 'MISTRAL large':        
#         try:

#             mistral_model = "mistral-large-latest"
            
#             client_mistral = MistralClient(api_key=mistral_api_key)
                      
#             # No streaming
#             chat_response = client_mistral.chat(
#                 model=mistral_model,
#                 messages=messages,
#                 temperature=temp_choice
#             )
            
#             return chat_response.choices[0].message.content
            
#         except Exception as e:
#             return f"An error occurred: {e}"

#     else: 
#         llm_model = 'gpt-4o'
        
#         try:
#             client = OpenAI()
#             response = openai.chat.completions.create(
#                 model=llm_model,
#                 messages=messages,
#                 temperature=temp_choice
#             )
#             return response.choices[0].message.content
            
#         except Exception as e:
#             return f"An error occurred: {e}"

    

# def translate_text(text, messages, from_language, to_language, temp_choice, select_model):
#     """
#     Translates text from one language to another with a specified style using OpenAI's API.
#     """ 
#     return run_model(messages, temp_choice, select_model)

# def enhance_text(text, objectif, public_cible, temp_choice, select_model):

#     return run_model(messages, temp_choice, select_model)


# def refine_text(text, temp_choice, select_model, briefing, prompt):

#     messages = [
#         {"role":"system", "content":briefing},
#         {"role":"user", "content":prompt}  
#     ]

#     return run_model(messages, temp_choice, select_model)


# def main():
#     openai.api_key = st.secrets["OPENAI_API_KEY"]
#     mistral_api_key = st.secrets["MISTRAL_API_KEY"]
    
#     PASSWORD = st.secrets["MDM_PASSWORD"]
    
#     client = OpenAI()
    
#     pass_word = st.sidebar.text_input('Enter the password:')
#     if not pass_word:
#         st.stop()
#     if pass_word != PASSWORD:
#         st.error('The password you entered is incorrect.')
#         st.stop()

#     select_model = st.sidebar.radio('**Select your MODEL**', ['GPT 4.0', 'MISTRAL large' ])
#     tool_choice = st.sidebar.radio("**Choose your tool:**", ['Translate your text with enhancement button', 'Translate your text with multiagent pipeline and human feedback'])
    
                    
#     if tool_choice == 'Translate your text with enhancement button':
        
#         st.subheader('Translate and upgrade your text')
               
#         # User input for translations
#         col1, col2 = st.columns(2)
#         with col1:
#             from_language = st.selectbox('From Language', ['French', 'Dutch', 'English'], index=1)
#         with col2:
#             to_language = st.selectbox('To Language', ['Dutch', 'French', 'English'], index=1)
        
#         temp_choice = st.slider('Select a Temperature', min_value=0.1, max_value=1.0, step=0.1, key='temp1')
    
#         st.write("**Lower Temperature (~0.1 to 0.5):** Recommended for more secure translations.")
#         st.write("**Higher Temperature (~0.6 to 1.0):** Encourages more creative translations.")

#         # File upload
#         uploaded_file = st.file_uploader("Upload file (PDF, PPTX, XLSX, DOCX)", type=['pdf', 'pptx', 'xlsx', 'docx'])
#         text = ""
                  
#         if uploaded_file:
#             if uploaded_file.type == "application/pdf":
#                 text = read_pdf(uploaded_file)
#             elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
#                 text = read_pptx(uploaded_file)
#             elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
#                 text = read_excel(uploaded_file)
#             elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
#                 text = read_docx(uploaded_file)
#             st.text_area("Extracted Text", value=text, height=150, disabled=True, key="extracted_enhancement")
        
#         # Manual text input as an alternative to file upload
#         text_input = st.text_area('Or enter text to translate', height=150, key="trans1_enhance")
    
#         # Combine file text and manual text input if both are provided
#         if text or text_input: 
#             combined_text = text + "\n" + text_input     
#         else: 
#             combined_text = None
            
#         translated_text = None
        
#         if 'central_file' not in st.session_state:
#             st.session_state.central_file = []
        
#         if 'last_text' not in st.session_state:
#             st.session_state['last_text'] = None
        
#         st.write("**Click to translate (uploaded or in box)**")
#         if st.button('Translate'):
            
#             if combined_text == None :
#                 st.error('Please upload or paste a text to translate.')
                
#             else:
#                 if to_language == 'French':

#                     message_translate = [
#                         {"role": "system", "content": f"Vous êtes un traducteur professionnel expert en {from_language} et français, spécialisé dans les secteurs des grandes ONG médicales et des droits humains. Votre maîtrise des nuances culturelles et terminologiques est excellente."},
#                         {"role": "user", "content": f"""
#                         **Objectif:** 
#                         - Traduisez le texte ci-dessous en français de manière à ce qu'il paraisse clair, convaincant et authentique pour un locuteur natif.
                        
#                         **Directives:**
#                         1. **Fidélité et Adaptabilité**: Le texte doit fidèlement refléter le sens original, tout en s'adaptant pour respecter les nuances de la langue cible.
#                         2. **Terminologie**: Utilisez une terminologie spécifique et cohérente, en consultant des glossaires au besoin.
#                         3. **Adaptation Culturelle**: Ajustez les références culturelles pour qu'elles résonnent naturellement avec le public cible.
#                         4. **Fluidité et clarté**: Aspirez à une traduction fluide, comme si le texte avait été rédigé en français à l'origine. Le message doit être exprimé de manière claire et persuasive. 
#                         5. **Conventions Linguistiques**: Respectez les règles grammaticales, orthographiques, et les conventions de formatage spécifiques au français.
                        
#                         **Texte à traduire:**
#                         {combined_text}
                        
#                         Suivez ces directives pour assurer une traduction de haute qualité et bien structurée. Contentez-vous de présenter la traduction dans votre réponse, sans commentaires ni remarques introductives, explicatives ou autres."""}
#                     ]

#                 elif to_language == 'Dutch':
                    
#                     message_translate = [
#                         {"role":"system", "content": f""" Je bent een expert in het feilloos vertalen van teksten voor de sector van medische NGO's en mensenrechten. Uw beheersing van culturele en terminologische nuances is uitstekend. """},
#                         {"role":"user", "content": f"""
#                         **Doel:**
#                         - Vertaal onderstaande tekst naar het Nederlands, waarbij de vertaling helder, overtuigend en authentiek moet klinken voor een Vlaming.

#                         **Richtlijnen:**
#                         1. **Trouw en Vrijheid**: Blijf trouw aan betekenis, stijl en toon, maar pas aan voor een betere aansluiting bij de doeltaal.
#                         2. **Terminologie**: Gebruik specifieke vakterminologie consistent. Raadpleeg zo nodig glossaria.
#                         3. **Culturele Aanpassing**: Pas culturele en idiomatische uitdrukkingen aan voor natuurlijk begrip.
#                         4. **Vloeiendheid en helderheid**: Zorg voor een vloeiende, natuurlijke tekst alsof origineel in het Frans geschreven. De boodschap wordt helder en overtuigend geformuleerd. 
#                         5. **Conventies:** Respecteer grammatica, spelling, interpunctie, en formatteer datums en valuta volgens de Franse normen.
                        
#                         **Te Vertalen Tekst:** 
#                         {combined_text}
                        
#                         Volg deze instructies voor een optimale vertaling en geef in uw antwoord enkel de vertaling weer, zonder commentaren."""}  
#                     ]

#                 else: 

#                     message_translate = [
#                         {"role": "system", "content": f"""You are a professional translator expert in {from_language} and English, specializing in the sectors of large medical NGOs and human rights. Your mastery of cultural and terminological nuances is excellent."""},
#                         {"role": "user", "content": f"""
#                         Objective: Translate the following text into English in a way that it appears clear, convincing and authentic to a native speaker.
                    
#                         Guidelines:
#                         1. **Fidelity and Adaptability**: The text must faithfully reflect the original meaning, while adapting to respect the nuances of the target language.
#                         2. **Terminology**: Use specific and consistent terminology, consulting glossaries as needed.
#                         3. **Cultural Adaptation**: Adjust cultural references to resonate naturally with the target audience.
#                         4. **Fluidity**: Aim for a translation that is fluid and clear, as if the text were originally written in English.
#                         5. **Linguistic Conventions**: Adhere to grammatical, spelling, and formatting conventions specific to English.
                        
#                         Text to translate:
#                         {combined_text}
                        
#                         Follow these guidelines to ensure a high-quality translation and present only the translation when answering."""}
#                     ]
                

#                 translated_text = run_model(message_translate, temp_choice, select_model)
           
#                 st.session_state.last_text = f"{select_model}, Temp {temp_choice}, 'translated':\n\n{translated_text}"
#                 st.write(translated_text)
    
       
#         # This check ensures we only attempt to use 'last_text' if it's been defined
#         if 'last_text' in st.session_state and st.session_state.last_text:
            
#             if st.session_state.last_text is not None:
                
#                 st.write('**Enhance text (translation or latest in memory)**')
#                 objectif = st.text_input("Describe clearly and concisely the purpose of the text, and/or add concrete guidelines for enhancement process.")
#                 public_cible = st.text_input("Describe target audience")
#                 text = st.session_state.last_text
                
#                 if st.button('Enhance'):
                        
#                     if to_language == 'French':
                    
#                         message_enhance = [
#                             {"role":"system", "content": """
                            
#                             **Mission** : Assister l'expert en rédaction pour évaluer et améliorer le texte fourni, en se concentrant sur:
#                             - l'optimisation de la fluidité 
#                             - l'augmentation de l'impact."""},
                            
#                             {"role":"user", "content": f"""
                            
#                             **Objectif du texte, ou directives pour le processus d'amélioration:**
#                             {objectif}
                    
#                             **Public-cible du texte:** 
#                             {public_cible}
                            
#                             **Processus d'amélioration:**
                          
#                             1. **Évaluation Initiale**  
#                                 - Identifiez les forces et les faiblesses du texte en termes de clarté, de cohérence et d'impact en adéquation avec les objectifs et le public-cible. 
#                             2. **Amélioration**  
#                                 Sur la base de l'évaluation initiale: 
#                                - Éliminez toute marque de traduction apparente.
#                                - Adapter si besoin les expressions et les références culturelles.
#                                - Surtout, renforcez la fluidité et l'authenticité du texte.
#                                - Ajuster la structure, le contenu, le style, le ton et le vocabulaire pour mieux correspondre aux objectifs, aux directives supplémentaires et au public cible du texte.
                               
                        
#                             Texte à évaluer et à améliorer :
#                             {text}

#                             Dans la réponse, vous incorporez uniquement le texte amélioré, sans l'évaluation initiale ou tout autre commentaire. 
#                             """}  
#                         ]


#                     elif to_language == 'Dutch':
                    
#                         message_enhance = [
            
#                             {"role": "system", "content": """
                            
#                             **Missie**: Assisteer de redactie-expert bij het evalueren en verbeteren van de aangeleverde tekst, met focus op :
#                             - Het optimaliseren van de vloeiendheid
#                             - Het vergroten van de impact"""},
                            
#                             {"role": "user", "content": f"""
                            
#                             **Doel van de tekst, of bijkomende richtlijnen voor de verbetering:**
#                             {objectif}
                        
#                             **Doelgroep van de tekst:** 
#                             {public_cible}
                            
#                             **Verbeteringsproces:**
                        
#                             1. **Initiële Evaluatie**
#                                 - Identificeer de sterke en zwakke punten van de tekst qua duidelijkheid, consistentie, en doeltreffendheid in lijn met de doelstellingen, bijkomende richtlijnen en doelgroep.
#                             2. **Verbetering**
#                                 Op basis van de initiële evaluatie:
#                                - Verwijder elke duidelijke vertaalindicatoren. 
#                                - Pas eventueel culturele uitdrukkingen en referenties aan.
#                                - Versterk vooral de vloeiendheid en authenticiteit van de tekst.
#                                - Pas de structuur, inhoud, stijl, toon, en vocabulaire aan om beter aan te sluiten bij de doelstellingen en doelgroep van de tekst.
                              
#                             Tekst om te evalueren en te verbeteren:
#                             {text}

#                             In het antwoord neemt u enkel de verbeterde tekst op, zonder de initiële evaluatie of ander commentaar.
#                             """}  
#                         ]

#                     else:

#                         message_enhance = [
#                             {"role": "system", "content": """
                            
#                             **Mission**: Assist the editorial expert in evaluating and improving the provided text, focusing on:
                            
#                             - Optimizing fluency
#                             - Increasing impact"""},
                            
#                             {"role": "user", "content": f"""
                            
#                             **Purpose of the text, or additional guidelines:**
#                             {objectif}
                            
#                             **Target audience of the text:** 
#                             {public_cible}
                            
#                             **Improvement process:**
                            
#                             1. **Initial Evaluation**
#                                 - Identify the strengths and weaknesses of the text in terms of clarity, consistency, and effectiveness in line with the objectives, guidelines en target audience.
#                             2. **Improvement**
#                                 Based on the initial evaluation:
#                                - Remove clear translation indicators.
#                                - Adapt further if necessary cultural expressions and references.
#                                - Above all, strengthen the fluency and authenticity of the text.
#                                - Adjust the structure, content, style, tone, and vocabulary to better align with the objectives, guidelines and target audience of the text.
                              
#                             Text to evaluate and improve:
#                             {text}

#                             The answer only contains the improved text version, and not the results of the initial evaluation or other comments. 
#                             """}  
#                         ]

#                     enhanced_text = run_model(message_enhance, temp_choice, select_model)
#                     st.session_state.last_text = f"{select_model}, Temp {temp_choice}, enhanced:\n\n{enhanced_text}"
#                     st.write(st.session_state.last_text)
                    
#                 else:
#                     st.write("")
                
            
#             st.write('**Add text in memory to central file**')
#             if st.button('Add to FILE'):
#                 st.session_state.central_file.append(st.session_state.last_text)
#                 st.success('Text added to central file!')

#         # st.sidebar.markdown("---")
#         st.sidebar.write("\n\n")
#         if 'central_file' in st.session_state and st.session_state.central_file:
#             st.sidebar.write('**Manage central file**')
#             if st.sidebar.button('DISPLAY'):
#                 st.write("Contents of the translations file:", st.session_state.central_file)
            
            
#             translations_str = '\n'.join(st.session_state.central_file)  # Join list items into a string
#             st.sidebar.download_button(label="DOWNLOAD",
#                            data=translations_str,  
#                            file_name="central_file.txt",
#                            mime="text/plain")
            
#             if st.sidebar.button('RESET'):
#                 st.session_state.central_file = []
#                 st.success('Translations file has been reset.')
        
#         if 'last_text' in st.session_state:
#             if st.session_state['last_text'] is not None:
#                 colon_index = st.session_state['last_text'].find(':')      
#                 st.sidebar.write("\n\n")
#                 st.sidebar.write('**Text in memory**')
#                 st.sidebar.write(st.session_state['last_text'][:colon_index])
#                 st.sidebar.write(f'Text in {to_language}')
            
#             else:
#                 st.write("...")   
    
    
#     if tool_choice == 'Translate your text with multiagent pipeline and human feedback':
        
#         st.subheader('Multiagent Translation with Human Feedback')
    
#         # User input for translations
#         col1, col2 = st.columns(2)
#         with col1:
#             from_language = st.selectbox('From Language', ['French', 'Dutch', 'English'], index=1, key='multi_from')
#         with col2:
#             to_language = st.selectbox('To Language', ['Dutch', 'French', 'English'], index=1, key='multi_to')
    
#         temp_choice = st.slider('Select a Temperature', min_value=0.1, max_value=1.0, step=0.1, key='multi_temp')
    
#         # File upload and text input (similar to the previous section)
#         uploaded_file = st.file_uploader("Upload file (PDF, PPTX, XLSX, DOCX)", type=['pdf', 'pptx', 'xlsx', 'docx'], key='multi_upload')
#         text = ""
#         if uploaded_file:
#             # (File reading logic remains the same)
#             st.text_area("Extracted Text", value=text, height=150, disabled=True, key="extract_multiagent")
        
#         text_input = st.text_area('Or enter text to translate', height=150, key='multi_text_input')
        
#         if text or text_input:
#             combined_text = text + "\n" + text_input
#         else:
#             combined_text = None
    
#         if st.button('Start Multiagent Translation'):
#             if combined_text is None:
#                 st.error('Please upload or paste a text to translate.')
#             else:
#                 # Step 1: Source Language Analyzer
#                 st.write("Step 1: Analyzing source text...")
#                 source_analyzer_prompt = PromptTemplate(
#                     input_variables=["source_text"],
#                     template="""
#                     You are a skilled linguistic analyst. Analyze the given text and provide insights for translation. Focus on:
#                     1. Idioms, colloquialisms, or culturally specific references
#                     2. Tone and register of the text
#                     3. Ambiguous phrases or words with multiple meanings
#                     4. Specialized terminology or jargon
    
#                     Source text: {source_text}
    
#                     Please provide your analysis:
#                     """
#                 )
#                 source_analysis = run_model([{"role": "user", "content": source_analyzer_prompt.format(source_text=combined_text)}], temp_choice, select_model)
#                 st.write(source_analysis)
    
#                 # Step 2: Translator
#                 st.write("Step 2: Translating...")
#                 translator_prompt = PromptTemplate(
#                     input_variables=["source_text", "analysis", "target_language"],
#                     template="""
#                     You are an expert translator. Translate the given text from its source language to {target_language}. Use the provided analysis to inform your translation. Pay attention to:
#                     1. Maintaining the original meaning and intent
#                     2. Preserving the tone and register
#                     3. Adapting idioms and cultural references appropriately
#                     4. Ensuring clarity and naturalness in the target language
    
#                     Source text: {source_text}
    
#                     Analysis: {analysis}
    
#                     Target language: {target_language}
    
#                     Please provide your translation:
#                     """
#                 )
#                 translation = run_model([{"role": "user", "content": translator_prompt.format(source_text=combined_text, analysis=source_analysis, target_language=to_language)}], temp_choice, select_model)
#                 st.write(translation)
    
#                 # Step 3: Target Language Editor
#                 st.write("Step 3: Editing translation...")
#                 editor_prompt = PromptTemplate(
#                     input_variables=["translated_text", "target_language"],
#                     template="""
#                     You are a skilled editor specializing in {target_language}. Refine and improve the given translation. Focus on:
#                     1. Ensuring grammatical correctness and idiomatic usage
#                     2. Improving fluency and naturalness of expression
#                     3. Maintaining consistency in terminology and style
#                     4. Adapting the text to be culturally appropriate for the target audience
    
#                     Translated text: {translated_text}
    
#                     Target language: {target_language}
    
#                     Please provide your edited version:
#                     """
#                 )
#                 edited_translation = run_model([{"role": "user", "content": editor_prompt.format(translated_text=translation, target_language=to_language)}], temp_choice, select_model)
#                 st.write(edited_translation)
    
#                 # Human Feedback Loop
#                 counter = 0
#                 while True:
#                     human_feedback = st.text_area("Provide feedback for further improvement (or type 'done' if satisfied):", key=f"human_fb_{counter}")
#                     counter += 1
#                     if human_feedback.lower() == 'done':
#                         break
                    
#                     if human_feedback.strip():
#                         feedback_prompt = PromptTemplate(
#                             input_variables=["translated_text", "human_feedback", "target_language"],
#                             template="""
#                             You are a skilled editor and translator specializing in {target_language}. Refine the translation based on human feedback. 
    
#                             Current translation: {translated_text}
    
#                             Human feedback: {human_feedback}
    
#                             Please provide:
#                             1. Your revised translation
#                             2. A brief explanation of the changes you made (2-3 sentences)
#                             3. A confidence score (1-10) for your revised translation, where 1 is least confident and 10 is most confident
    
#                             Format your response as follows:
#                             Revised Translation: [Your revised translation here]
#                             Explanation: [Your explanation here]
#                             Confidence: [Your confidence score here]
#                             """
#                         )
                        
#                         feedback_response = run_model([{"role": "user", "content": feedback_prompt.format(translated_text=edited_translation, human_feedback=human_feedback, target_language=to_language)}], temp_choice, select_model)
#                         revised_translation, explanation, confidence = parse_feedback_response(feedback_response)
#                         st.write(f"Revised translation: {revised_translation}")
#                         st.write(f"Explanation: {explanation}")
#                         st.write(f"Confidence score: {confidence}")
#                         edited_translation = revised_translation
    
#                 st.success("Translation process completed!")
#                 st.session_state.last_text = f"{select_model}, Temp {temp_choice}, multiagent translated:\n\n{edited_translation}"

# if __name__ == "__main__":
#     main()

