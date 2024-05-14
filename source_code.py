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

openai.api_key = st.secrets["OPENAI_API_KEY"]
mistral_api_key = st.secrets["MISTRAL_API_KEY"]

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

            mistral_model = "mistral-large-latest"
            
            client_mistral = MistralClient(api_key=mistral_api_key)
                      
            # No streaming
            chat_response = client_mistral.chat(
                model=mistral_model,
                messages=messages,
                temperature=temp_choice
            )
            
            return chat_response.choices[0].message.content
            
        except Exception as e:
            return f"An error occurred: {e}"

    else: 
        llm_model = 'gpt-4-turbo-2024-04-09'
        
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

    

def translate_text(text, messages, from_language, to_language, temp_choice, select_model):
    """
    Translates text from one language to another with a specified style using OpenAI's API.
    """ 
    return run_model(messages, temp_choice, select_model)

def enhance_text(text, objectif, public_cible, temp_choice, select_model):

    return run_model(messages, temp_choice, select_model)


def refine_text(text, temp_choice, select_model, briefing, prompt):

    messages = [
        {"role":"system", "content":briefing},
        {"role":"user", "content":prompt}  
    ]

    return run_model(messages, temp_choice, select_model)

def reply_to_email(email, done_action_points, extra_info, llm_model):

    llm = ChatOpenAI(temperature=0.1, model=llm_model)
    
    template_language_detection = """
    Detect the language in which the text between triple backticks was written:
    '''
    {e_mail}
    '''
    """
    
    prompt_language_detection = ChatPromptTemplate.from_template(template_language_detection)
    
    chain_language_detection = LLMChain(
        llm=llm, 
        prompt=prompt_language_detection, 
        output_key="Email_language"
    )
    
    template_translate_email = """
    Translate the {e_mail} to French if {Email_language} is Dutch and to Dutch if {Email_language} is French :
    '''
    {e_mail}
    '''
    If {Email_language} is neither French nor Dutch, translate it to French and Dutch.
    """
    
    prompt_translate_email = ChatPromptTemplate.from_template(template_translate_email)
    
    chain_translate_email = LLMChain(
        llm=llm, 
        prompt=prompt_translate_email, 
        output_key="Email_translation"
    )
    
    template_extract_action_points = """
    Look at the email and extract all action points from it: 
    '''
    {e_mail}
    '''
    Consider that the mail is sent by a donor to an NGO. The action points to be listed are only those for the NGO to take care of. 
    List the action points and add a translation in French if {Email_language} is Dutch and in Dutch if {Email_language} is French. 
    
    The list should have the format as in the following example:
    
    Example:
    '''
    1. Mettre fin au mandat dans les 24 heures / het mandaat stopzetten binnen de 24 uur
    2. Confirmer par mail quand c'est fait / Per mail bevestigen wanneer het is stopgezet
    '''
    """
    
    prompt_extract_action_points = ChatPromptTemplate.from_template(template_extract_action_points)
    
    chain_extract_action_points = LLMChain(
        llm=llm, 
        prompt=prompt_extract_action_points, 
        output_key="Email_action_points"
    )
    
    template_propose_answer = """
    Your task is to propose an answer in {Email_language} to the following email between backticks:
    '''
    {e_mail}
    '''
    Consider the {Email_action_points} and mention that the following action points between backticks have been taken care of:
    '''
    {done_action_points}
    '''
    Consider also the following info between backticks:
    '''
    {extra_info}
    '''
    Your answer should always be engaging, constructive, helpful and respectful. Consider not only the content but also the tone and sentiment of the message to determine the most suitable answer. 
    Avoid any kind of controversy, ambiguities, or politically oriented answers.
    If appropriate, while avoiding being too pushy or inpolite, mention the possibility to become a (regular) donor (again) by surfing to our website www.medecinsdumonde.be or www.doktersvandewereld.be (according to {Email_language}). 
    Try to end by a positive note and/or a thank you.
    """
    
    prompt_propose_answer = ChatPromptTemplate.from_template(template_propose_answer)
    
    chain_propose_answer = LLMChain(
        llm=llm, 
        prompt=prompt_propose_answer, 
        output_key="Email_answer"
    )
    
    template_translate_answer = """
    Translate the {Email_answer} to French if {Email_language} is Dutch and to Dutch if {Email_language} is French :
    '''
    {Email_answer}
    '''
    If {Email_language} is neither French nor Dutch, translate it to French and Dutch.
    """
    
    prompt_translate_answer = ChatPromptTemplate.from_template(template_translate_answer)
    
    chain_translate_answer = LLMChain(
        llm=llm, 
        prompt=prompt_translate_answer, 
        output_key="Email_answer_translation"
    )
    
    overall_chain = SequentialChain(
        chains=[chain_language_detection, chain_translate_email, chain_extract_action_points, chain_propose_answer, chain_translate_answer],
        input_variables=['e_mail', 'done_action_points', 'extra_info'],
        output_variables=["Email_language", "Email_translation", "Email_action_points", "Email_answer", "Email_answer_translation"],
        verbose=False
    )
    
    # Invoke the overall chain
    result = overall_chain({
        'e_mail': e_mail,
        'done_action_points': done_action_points,
        'extra_info': extra_info
    })

    return result

def main():
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    mistral_api_key = st.secrets["MISTRAL_API_KEY"]
    
    PASSWORD = st.secrets["MDM_PASSWORD"]
    
    client = OpenAI()
    
    pass_word = st.sidebar.text_input('Enter the password:')
    if not pass_word:
        st.stop()
    if pass_word != PASSWORD:
        st.error('The password you entered is incorrect.')
        st.stop()

    select_model = st.sidebar.radio('**Select your MODEL**', ['gpt-4-turbo', 'gpt-4o' ])
    tool_choice = st.sidebar.radio('**Choose your tool:**', ['Reply to emails', 'Translate your text'])
        
    if tool_choice == 'Reply to emails':
        st.subheader("DONORSBOX ANSWERING TOOL")
        e_mail = ""
        action_points = ""
        extra_info = ""
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("Paste here the email you want ChatGPT provide you with an answer. Don't forget to fill in the other text boxes also.")
            st.write("**Please remove all personal information from the email.**")
            e_mail = st.text_area('Paste email', height=150)
        with col2: 
            st.write("Paste here the action points you have or will have completed by the time you will answer the mail.")
            action_points = st.text_area('Mention action points', height=150)
        with col3: 
            st.write("Paste additional information you want to see mentionned in the answer, and which is not an action point.")
            extra_info = st.text_area('Add extra info', height=150)

        result = reply_to_email(e_mail, done_action_points, extra_info, select_model)

        if st.button("Click here to translate the original email"):
            st.write(result['Email_translation'])

        if st.button("Click here to generate draft answer"):
            st.write('*Proposed answer to the mail*')
            st.write(result['Email_answer'])
            st.write('*Translation of answer*')
            st.write(result['Email_answer_translation']




    # if tool_choice == "Chat with LLM":
                
    #     st.title("Chatbot")
    #     temp_choice = st.slider('Select a Temperature', min_value=0.0, max_value=1.0, step=0.1, key='llm_bot')

    #     st.write("**Selected model**:", select_model)       
      
    #     st.session_state.api_key = openai.api_key
        
    #     if "messages" not in st.session_state:
    #         st.session_state.messages = []
        
    #     for message in st.session_state.messages:
    #         with st.chat_message(message["role"]):
    #             st.markdown(message["content"])

    #     if prompt := st.chat_input():
    #         st.session_state.messages.append({"role": "user", "content": prompt})
    #         with st.chat_message("user"):
    #             st.markdown(prompt)
        
    #         with st.chat_message("assistant"):
    #             completion = client.chat.completions.create(
    #                 model= select_model,
    #                 messages=[
    #                     {"role": m["role"], "content": m["content"]}
    #                     for m in st.session_state.messages
    #                 ],
    #                 stream=True,
    #             )
    #             response = st.write_stream(completion)
               
    #         st.session_state.messages.append({"role": "assistant", "content": response})
        
    #     st.sidebar.markdown("---")       
    #     if st.session_state.messages:
    #         st.sidebar.write('**Manage Chat Session**')           
            
    #         chat_messages = '\n'.join(
    #             m['content'] for m in st.session_state.messages if 'content' in m and isinstance(m['content'], str)
    #         )

    #         st.sidebar.download_button(label="Download Session",
    #                        data=chat_messages,  
    #                        file_name="chat_messages.txt",
    #                        mime="text/plain")
            
    #         if st.sidebar.button('Restart session'):
    #             st.session_state.messages = []
    #             st.sidebar.success('Chat has been reset.')
    #             st.cache_resource.clear()
    #             st.cache_data.clear()
    #             st.success('Cache had been cleared.')
    #             st.rerun()
                     
    if tool_choice == 'Translate your text': 
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
            if text or text_input: 
                combined_text = text + "\n" + text_input     
            else: 
                combined_text = None
                
            translated_text = None
            
            if 'central_file' not in st.session_state:
                st.session_state.central_file = []
            
            if 'last_text' not in st.session_state:
                st.session_state['last_text'] = None
            
            st.write("**Click to translate (uploaded or in box)**")
            if st.button('Translate'):
                
                if combined_text == None :
                    st.error('Please upload or paste a text to translate.')
                    
                else:
                    if to_language == 'French':

                        message_translate = [
                            {"role": "system", "content": f"Vous êtes un traducteur professionnel expert en {from_language} et français, spécialisé dans les secteurs des grandes ONG médicales, des droits humains et de la communication publique. Votre maîtrise des nuances culturelles et terminologiques est essentielle."},
                            {"role": "user", "content": f"""
                            **Objectif:** 
                            - Traduisez le texte ci-dessous en français de manière à ce qu'il paraisse naturel et authentique pour un locuteur natif.
                            
                            **Directives:**
                            1. **Fidélité et Adaptabilité**: Le texte doit fidèlement refléter le sens original, tout en s'adaptant pour respecter les nuances de la langue cible.
                            2. **Terminologie**: Utilisez une terminologie spécifique et cohérente, en consultant des glossaires au besoin.
                            3. **Adaptation Culturelle**: Ajustez les références culturelles pour qu'elles résonnent naturellement avec le public cible.
                            4. **Fluidité et clarté**: Aspirez à une traduction fluide, comme si le texte avait été rédigé en français à l'origine. Le message doit être exprimé de manière claire et persuasive. 
                            5. **Conventions Linguistiques**: Respectez les règles grammaticales, orthographiques, et les conventions de formatage spécifiques au français.
                            
                            **Texte à traduire:**
                            {combined_text}
                            
                            Suivez ces directives pour assurer une traduction de haute qualité et contentez-vous de présenter la traduction dans votre réponse, sans commentaires ni remarques introductives, explicatives ou autres."""}
                        ]

                    elif to_language == 'Dutch':
                        
                        message_translate = [
                            {"role":"system", "content": f""" Je bent een expert in het vertalen voor medische NGO's, mensenrechten, en publieke communicatie. Je spreekt {from_language} en het Nederlands vloeiend, met grondige kennis van beide culturen en terminologieën."""},
                            {"role":"user", "content": f"""
                            **Doel:**
                            - Vertaal onderstaande tekst naar het Nederlands, waarbij de vertaling natuurlijk en authentiek moet klinken voor Vlamingen.

                            **Richtlijnen:**
                            1. **Trouw en Vrijheid**: Blijf trouw aan betekenis, stijl en toon, maar pas aan voor een betere aansluiting bij de doeltaal.
                            2. **Terminologie**: Gebruik specifieke vakterminologie consistent. Raadpleeg zo nodig glossaria.
                            3. **Culturele Aanpassing**: Pas culturele en idiomatische uitdrukkingen aan voor natuurlijk begrip.
                            4. **Vloeiendheid en helderheid**: Zorg voor een vloeiende, natuurlijke tekst alsof origineel in het Frans geschreven. De boodschap wordt helder en overtuigend geformuleerd. 
                            5. **Conventies:** Respecteer grammatica, spelling, interpunctie, en formatteer datums en valuta volgens de Franse normen.
                            
                            **Te Vertalen Tekst:** 
                            {combined_text}
                            
                            Volg deze instructies voor een optimale vertaling en geef in uw antwoord enkel de vertaling weer, zonder commentaren."""}  
                        ]

                    else: 

                        message_translate = [
                            {"role": "system", "content": f"""You are a professional translator expert in {from_language} and English, specializing in the sectors of large medical NGOs, human rights, and public communication. Your mastery of cultural and terminological nuances is essential."""},
                            {"role": "user", "content": f"""
                            Objective: Translate the following text into English in a way that it appears natural and authentic to a native speaker.
                        
                            Guidelines:
                            1. **Fidelity and Adaptability**: The text must faithfully reflect the original meaning, while adapting to respect the nuances of the target language.
                            2. **Terminology**: Use specific and consistent terminology, consulting glossaries as needed.
                            3. **Cultural Adaptation**: Adjust cultural references to resonate naturally with the target audience.
                            4. **Fluidity**: Aim for a translation that is fluid and clear, as if the text were originally written in English.
                            5. **Linguistic Conventions**: Adhere to grammatical, spelling, and formatting conventions specific to English.
                            
                            Text to translate:
                            {combined_text}
                            
                            Follow these guidelines to ensure a high-quality translation and present only the translation when answering."""}
                        ]
                    

                    translated_text = run_model(message_translate, temp_choice, select_model)
               
                    st.session_state.last_text = f"{select_model}, Temp {temp_choice}, 'translated':\n\n{translated_text}"
                    st.write(translated_text)
        
           
            # This check ensures we only attempt to use 'last_text' if it's been defined
            if 'last_text' in st.session_state and st.session_state.last_text:
                
                if st.session_state.last_text is not None:
                    
                    st.write('**Enhance text (translation or latest in memory)**')
                    objectif = st.text_input("Describe clearly and concisely the goal or objective of text (use language of target audience)")
                    public_cible = st.text_input("Describe target audience")
                    text = st.session_state.last_text
                    
                    if st.button('Enhance'):
                            
                        if to_language == 'French':
                        
                            message_enhance = [
                                {"role":"system", "content": """
                                
                                **Mission** : Assister l'expert en rédaction pour évaluer et améliorer le texte fourni, en se concentrant sur:
                                - l'optimisation de la fluidité 
                                - l'authenticité linguistique 
                                - l'augmentation de l'impact."""},
                                
                                {"role":"user", "content": f"""
                                
                                **Objectif du texte:**
                                {objectif}
                        
                                **Public-cible du texte:** 
                                {public_cible}
                                
                                **Processus d'amélioration:**
                              
                                1. **Évaluation Initiale**  
                                    - Identifiez les forces et les faiblesses du texte en termes de clarté, de cohérence et d'impact en adéquation avec les objectifs/public-cible. 
                                2. **Amélioration**  
                                    Sur la base de l'évaluation initiale: 
                                   - Éliminez les marques de traduction apparentes.
                                   - Adapter les expressions et les références culturelles.
                                   - Renforcez la fluidité et l'authenticité du texte.
                                   - Ajuster la structure, le contenu, le style, le ton et le vocabulaire pour mieux correspondre aux objectifs et au public cible et augmenter son impact.
                                   
                            
                                Texte à évaluer et à améliorer :
                                {text}
    
                                Dans la réponse, vous incorporez uniquement le texte amélioré, sans l'évaluation initiale ou tout autre commentaire. 
                                """}  
                            ]
    
    
                        elif to_language == 'Dutch':
                        
                            message_enhance = [
                
                                {"role": "system", "content": """
                                
                                **Missie**: Assisteer de redactie-expert bij het evalueren en verbeteren van de aangeleverde tekst, met focus op :
                                - Het optimaliseren van de vloeiendheid
                                - De taalkundige authenticiteit
                                - Het vergroten van de impact"""},
                                
                                {"role": "user", "content": f"""
                                
                                **Doel van de tekst:**
                                {objectif}
                            
                                **Doelgroep van de tekst:** 
                                {public_cible}
                                
                                **Verbeteringsproces:**
                            
                                1. **Initiële Evaluatie**
                                    - Identificeer de sterke en zwakke punten van de tekst qua duidelijkheid, consistentie, en doeltreffendheid in lijn met de doelstellingen/doelgroep.
                                2. **Verbetering**
                                    Op basis van de initiële evaluatie:
                                   - Verwijder duidelijke vertaalindicatoren. 
                                   - Pas culturele uitdrukkingen en referenties aan.
                                   - Versterk de vloeiendheid en authenticiteit van de tekst.
                                   - Pas de structuur, inhoud, stijl, toon, en vocabulaire aan om beter aan te sluiten bij de doelstellingen en doelgroep en om de impact te vergroten.
                                  
                                Tekst om te evalueren en te verbeteren:
                                {text}
    
                                In het antwoord neemt u enkel de verbeterde tekst op, zonder de initiële evaluatie of ander commentaar.
                                """}  
                            ]
    
                        else:
    
                            message_enhance = [
                                {"role": "system", "content": """
                                
                                **Mission**: Assist the editorial expert in evaluating and improving the provided text, focusing on:
                                
                                - Optimizing fluency
                                - Linguistic authenticity
                                - Increasing impact"""},
                                
                                {"role": "user", "content": f"""
                                
                                **Purpose of the text:**
                                {objectif}
                                
                                **Target audience of the text:** 
                                {public_cible}
                                
                                **Improvement process:**
                                
                                1. **Initial Evaluation**
                                    - Identify the strengths and weaknesses of the text in terms of clarity, consistency, and effectiveness in line with the objectives/target audience.
                                2. **Improvement**
                                    Based on the initial evaluation:
                                   - Remove clear translation indicators.
                                   - Adapt cultural expressions and references.
                                   - Strengthen the fluency and authenticity of the text.
                                   - Adjust the structure, content, style, tone, and vocabulary to better align with the objectives and target audience and to increase impact.
                                  
                                Text to evaluate and improve:
                                {text}
    
                                The answer only contains the improved text version, and not the results of the initial evaluation or other comments. 
                                """}  
                            ]

                        enhanced_text = run_model(message_enhance, temp_choice, select_model)
                        st.session_state.last_text = f"{select_model}, Temp {temp_choice}, enhanced:\n\n{enhanced_text}"
                        st.write(st.session_state.last_text)
                        
                    else:
                        st.write("")
                    
                
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
                if st.session_state['last_text'] is not None:
                    colon_index = st.session_state['last_text'].find(':')      
                    st.sidebar.write("\n\n")
                    st.sidebar.write('**Text in memory**')
                    st.sidebar.write(st.session_state['last_text'][:colon_index])
                    st.sidebar.write(f'Text in {to_language}')
                
                else:
                    st.write("...")   
        

        with tab2:
            st.subheader('Refine')

            st.write('#### Under construction')


        with tab3:
            st.subheader('Craft')

            st.write('#### Under construction')
            

if __name__ == "__main__":
    main()
