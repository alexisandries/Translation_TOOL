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

openai.api_key  = os.getenv('OPENAI_API_KEY')
mistral_api_key = os.getenv("MISTRAL_API_KEY")
PASSWORD = os.getenv("MDM_PASSWORD")

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

def translate_text(text, from_language, to_language, temp_choice, select_model, briefing, prompt):
    """
    Translates text from one language to another with a specified style using OpenAI's API.
    """

    messages = [
        {"role":"system", "content":briefing},
        {"role":"user", "content":prompt}  
    ]
    
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
                temperature=temp_choice,
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"An error occurred: {e}"

def enhance_text(text, temp_choice_2, select_model, briefing, prompt):
    """
    Translates text from one language to another with a specified style using OpenAI's API.
    """

    messages = [
        {"role":"system", "content":briefing},
        {"role":"user", "content":prompt}  
    ]
    
    if select_model == 'MISTRAL large':
        
        try:

            model = "mistral-large-latest"
            
            client_mistral = MistralClient(api_key=mistral_api_key)
                      
            # No streaming
            chat_response = client_mistral.chat(
                model=model,
                messages=messages,
                temperature=temp_choice_2
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
                temperature=temp_choice_2
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"An error occurred: {e}"

def main():
    
    select_model = st.sidebar.radio('Select your model', ['GPT 3.5', 'GPT 4.0', 'MISTRAL large' ])
    
    if select_model != 'GPT 3.5':
        
        pass_word = st.text_input('Enter the password:')
    
        if not pass_word:
            st.stop()
            
        elif pass_word != PASSWORD:
            st.error('The password you entered is incorrect.')
            st.stop()
    
        if pass_word == PASSWORD:
            pass
            
    st.subheader('Translate, Refine or Craft your text')
    tab1, tab2, tab3 = st.tabs(['TRANSLATE', 'REFINE', 'CRAFT'])
    
    with tab1: 
    
        # User input for translations
        col1, col2 = st.columns(2)
        with col1:
            from_language = st.selectbox('From Language', ['English', 'French', 'Dutch'], index=1)
        with col2:
            to_language = st.selectbox('To Language', ['French', 'Dutch', 'English'], index=2)
        
        temp_choice = st.slider('Select a Temperature', min_value=0.2, max_value=0.8, step=0.1, key='temp1')
    
        st.write("**Lower Temperature (~0.2 to 0.4):** Recommended for more accurate, literal translations.")
        st.write("**Higher Temperature (~0.6 to 0.8):** Encourages more creative and fluid translations.")

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
        text_input = st.text_area('Or enter text to translate', height=200)
    
        # Combine file text and manual text input if both are provided
        combined_text = text + "\n" + text_input
        
        briefing_1 = """
        As TranslationsAI, you embody the pinnacle of translation expertise, seamlessly bridging languages with unparalleled precision and eloquence. Your core languages include French, Dutch, and English. Each translation you produce adheres to the highest standards of reliability, ensuring that the meaning and nuance of the original text are perfectly preserved. Additionally, you imbue every translated piece with native fluency, adapting idioms, cultural references, and stylistic nuances to resonate authentically with the target audience. If necessary, you will seamlessly provide more adaptive translations that recreate the original's intent and style as if it were conceived in the target language. As a consequence, your translations are enriched with the depth and vibrancy characteristic of a skilled writer native to the destination language.
        """
        
        briefing_2="""
        You are TranslationsAI, a highly specialized translation assistant designed to provide accurate and fluent translations between French, Dutch, and English. Your translations should reflect a deep understanding of the source material while maintaining the nuances, tone, and cultural relevance of the original text in the target language. You aim to achieve translations that are indistinguishable from texts originally written in the target language, ensuring both linguistic precision and fluency.
        """
        
        prompt_1= f"""
        Translate the following text from {from_language} to {to_language}, ensuring the translation is both accurate and sounds natural as if originally written in the target language. Consider cultural nuances and idiomatic expressions to enhance fluency and readability.
            
        Text to Translate:
        {combined_text}
        """
        
        prompt_2= f"""
        Please rewrite the following text in {to_language}, making it sound as if it were originally written by a native speaker. The original text is in {from_language}. Adapt expressions, idioms, and cultural references to ensure the translation is fluent and resonates with native speakers, even if it means straying from a literal translation. If sentences are not fluent or sound too much as translated, please rewrite them in orther to keep the original idea, but use phrases that are familiar, rythmic and consistent in the target language.
        
        Text to Translate:
        {combined_text}
        """

        if st.button('Translate'):
            if combined_text:
                translated_text = translate_text(combined_text, from_language, to_language, temp_choice, select_model, briefing_1, prompt_2)
                st.write(translated_text)
                
                col6, col7 = st.columns(2)
                with col6:
                    if st.button('Add to Translations_file'):
                        # Initialize or append to translations_file in session state
                        if 'translations_file' not in st.session_state:
                            st.session_state.translations_file = [f"{select_model}, {temp_choice}:\n\n{translated_text}"]
                            st.success('Text added to the file!')
                        else:
                            st.session_state.translations_file.append(f"{select_model}, {temp_choice}:\n\n{translated_text}")
                            st.success('Text added to the file!')
                    
                with col7:
                    # Creating a download button for the translated text
                    st.download_button(label="Download Current Text", data=translated_text, file_name="translation.txt", mime="text/plain")
                    if 'translations_file' in st.session_state and st.session_state.translations_file:
                        st.download_button(label="Download Translations File", data=st.session_state.translations_file, file_name="translations_file.txt", mime="text/plain")

            else:
                 st.error('Please upload or paste a text to translate.')
                 
        if 'translations_file' in st.session_state: 
            if st.button('Display Translations File'):
                st.write("Contents of the translations file:", st.session_state.translations_file)
            
            # if st.button('Reset Translations File'):
            #     st.session_state.translations_file = []
            #     st.success('Translations file has been reset.')
        else:
            st.write("Add some file to translations_file")
            
    with tab2:
        st.subheader('Refinement tool')
        st.write("Activate agents to rework the translation(s). Choose the agent that you want to activate.")
        st.write("How to use agents? Once you have compiled your unique file with one or more versions, you can ask an agent to review the translation(s) and offer you a new, enhanced text.")
        
        st.write('Update your model choice if necessary')
        temp_choice_2 = st.slider('Select a New Temperature', min_value=0.1, max_value=0.8, step=0.1, key='temp2')
        agent_choice = st.radio('Pick Agent:', ['Expert in Marketing', 'Master in Copywriting', 'Doctor in Factual Communication'])
        unique_text = st.session_state.get('translations_file', [])  
        
        
        if agent_choice == 'Expert in Marketing':
        
            briefing_marketeer = f"""
            Act as a marketing expert, native in the language of {unique_text}, skilled in rewriting texts to make them more engaging. You are responsible for rephrasing entire paragraphs if necessary, applying your expertise in persuasive and compelling communication. Your goal is to enhance the text's appeal to its intended audience, making it more captivating and effective in achieving its purpose. Use your deep understanding of marketing strategies and audience engagement techniques to refine the text, ensuring it resonates well with its readers. Consider tone, style, and key messaging as you craft a version that aligns with best practices in marketing and communication.
            """
        
            prompt_marketeer = f"""
            Given your expertise as a marketing expert specialized in crafting engaging and persuasive content, I seek your assistance in rewriting the following text. The original version feels lackluster and fails to engage the audience effectively. Your task is to inject vibrancy, persuasiveness, and clarity into the message, making it resonate with our target audience. 
            
            Please evaluate any provided versions or translations of the text. Use them as a foundation to identify the strongest elements or combine the best parts of each. Your goal is to produce a single, cohesive version that stands out as the most compelling and persuasive piece, utilizing your deep understanding of marketing strategies, audience engagement, and persuasive communication techniques.
            
            Feel empowered to rephrase whole sections, adjust the tone, and refine the style as needed. We aim for a text that not only captivates and persuades but also clearly communicates our key messages, setting our offering apart in the minds of our audience.
            
            Text to enhance, using the same language, in which you are native:
            {unique_text}
            """
        
            if st.button('Enhance'):
            
                enhanced_marketeer = enhance_text(unique_text, temp_choice_2, select_model, briefing_marketeer, prompt_marketeer)
                st.write(enhanced_marketeer)
                
                # Creating a download button for the translated text
                st.download_button(label="Download Text", data=enhanced_marketeer, file_name="translation_enhanced_marketeer.txt", mime="text/plain")
                
        if agent_choice == 'Master in Copywriting':
            
            briefing_copywriter = f"""
            Act as a master in copywriting, native in the language of {unique_text}, possessing exceptional skills in rewriting and rephrasing texts to achieve unparalleled fluency and naturalness in the target language. Your primary responsibility is to enhance the readability and flow of the text, ensuring it feels native and intuitive to the audience. Utilize your expertise in language and syntax to transform the content into a masterpiece of clarity and engagement. Your objective is to refine the text in a way that speaks directly to the reader's experience, making it effortlessly understandable and highly relatable. Focus on linguistic precision, cultural resonance, and the seamless conveyance of ideas, tailoring the message to fit the natural speech patterns and preferences of the target audience.
            """
        
            prompt_copywriter = f"""
            Given your mastery in copywriting and your ability to craft text that flows naturally and fluently for the native language of our target audience, I request your help in rewriting the text provided below. The current version, while informative, lacks the linguistic finesse and natural tone necessary to truly resonate with our readers. Your mission is to transform this text, enhancing its readability, ensuring it aligns perfectly with the native expressions and cultural nuances of the audience.
            
            Examine any available versions or translations of the text, identifying opportunities to improve its flow, clarity, and engagement. Draw upon your sophisticated understanding of language, style, and syntax to produce a version that stands as an exemplar of copywriting excellence—fluent, natural, and compelling.
            
            Your expertise in creating content that mirrors the conversational and cultural tone of the target audience is crucial. We are looking for a text that not only conveys the intended message but does so in a way that feels completely at home to the reader, as if it were crafted by and for someone from their own community.
            
            Text to enhance, using the same language, in which you are native:
            {unique_text}
            """
        
            if st.button('Enhance'):
            
                enhanced_copywriter = enhance_text(unique_text, temp_choice_2, select_model, briefing_copywriter, prompt_copywriter)
                st.write(enhanced_copywriter)
                
                # Creating a download button for the translated text
                st.download_button(label="Download Text", data=enhanced_copywriter, file_name="translation_enhanced_copywriter.txt", mime="text/plain")
        
        if agent_choice == 'Doctor in Factual Communication':
        
            briefing_doctor = f"""
            Assume the role of a Doctor in factual communication, native in the language of {unique_text}, an expert in articulating clear, evidence-based, and convincing messages. Your expertise lies in grounding communication in solid facts, data, and research to ensure credibility and authority. You are adept at presenting information in a manner that is not only informative but also compelling and result-oriented. Your task involves distilling complex information into digestible, impactful messages that directly address and engage the target audience. Focus on accuracy, clarity, and the strategic use of evidence to bolster arguments, aiming to educate, persuade, and drive action. Your approach should be straightforward, avoiding ambiguity to foster trust and confidence in the message conveyed.
            """
        
            prompt_doctor = f"""
            Given your expertise as a Doctor in factual communication, with a deep understanding of how to craft messages that are both evidence-based and compelling, your assistance is requested in rewriting the text provided below. The existing content needs to be transformed to not only accurately convey the necessary information but to do so in a manner that is engaging, convincing, and direct, ensuring it resonates with an audience seeking reliable and authoritative data.
            
            Please leverage your ability to formulate comprehensive, to-the-point messages and convey clear, concise, and impactful statements. Your revision should amplify the text’s credibility and persuasiveness by highlighting solid facts, statistics, or findings that support the message, presented in a way that is accessible and compelling to the reader. 
            
            Your goal is to produce a version of the text that stands as a benchmark of factual communication—direct, result-oriented, and grounded in undeniable evidence. This text should not only inform but also motivate the reader towards a specific understanding or action, based on the strength and clarity of the information presented.
            
            Text to enhance, using the same language, in which you are native:
            {unique_text}
            """
        
            if st.button('Enhance'):
            
                enhanced_doctor = enhance_text(unique_text, temp_choice_2, select_model, briefing_doctor, prompt_doctor)
                st.write(enhanced_doctor)
                
                # Creating a download button for the translated text
                st.download_button(label="Download Text", data=enhanced_doctor, file_name="translation_enhanced_doctor.txt", mime="text/plain")


if __name__ == "__main__":
    main()
