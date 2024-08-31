import streamlit as st
import openai
import fitz  # PyMuPDF
from pptx import Presentation
from openpyxl import load_workbook
from docx import Document
from io import BytesIO
from openai import OpenAI
from mistralai.client import MistralClient
from langchain.prompts import PromptTemplate
from langdetect import detect
# from mistralai.models.chat_completion import ChatMessage
from functools import partial
import json
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
def run_openai_model(messages, temp_choice, model):
    try:
        response = openai_client.chat.completions.create(
            model=model,
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
        return run_openai_model(messages, temp_choice, select_model)

# Translation process functions
def analyze_source_text(text, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["source_text"],
        template="""
        You are an expert in comparative linguistics. Analyze the given text and provide insights for translation. Focus on:
        1. Idioms, colloquialisms, or culturally specific references
        2. Tone and register of the text
        3. Ambiguous phrases or words with multiple meanings
        4. Specialized terminology or jargon
        5. Any other difficulty in the text
        
        Additionally, analyze the broader context of the text to clearly understand its references and how the words should be interpreted.        
        
        Source text: {source_text}

        Please provide your analysis:
        """
    )
    return run_model([{"role": "user", "content": prompt.format(source_text=text)}], temp_choice, select_model)

def translate_text(text, analysis, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["source_text", "analysis", "target_language"],
        template="""
        You are an expert translator with deep knowledge of both the source and target languages, as well as their cultural contexts. Your task is to translate the following text into {target_language}, using the provided analysis to guide your work.

        Source text: {source_text}

        Analysis: {analysis}

        Target language: {target_language}

        Guidelines for translation:
        1. Meaning and Intent: Preserve the original message and intention.
        2. Tone and Register: Match the style, formality level, and emotional tone of the original text.
        3. Cultural Adaptation: 
           - Adapt idioms, metaphors, and cultural references to resonate with the target audience.
           - If a direct equivalent doesn't exist, provide a culturally appropriate alternative that conveys the same meaning.
        4. Clarity and Fluency: Ensure the translation reads naturally and fluently in the target language.
        5. Terminology: Use field-specific terminology accurately if present in the text.
        6. Context: Consider the broader context and purpose of the text in your translation choices.
        7. Ambiguity: If you encounter ambiguous phrases, translate to preserve the ambiguity if possible, or choose the most likely interpretation based on context.

        Additional instructions:
        - If you encounter any untranslatable elements, keep them in the original language and add a brief explanation in parentheses.
        - For proper nouns, use the conventional spelling in the target language if one exists, otherwise keep the original.
        - Maintain any formatting present in the source text (e.g., bullet points, paragraph breaks).

        Please provide your translation below, without adding any comment. 

        Translation:
        """
    )
    
    return run_model([{"role": "user", "content": prompt.format(source_text=text, analysis=analysis, target_language=target_language)}], temp_choice, select_model)

def edit_translation(translated_text, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["translated_text", "target_language"],
        template="""
        You are a highly skilled editor and writer, native in {target_language}, with a deep understanding of its nuances, idioms, and cultural context. Your task is to refine and elevate the given translation, making it indistinguishable from text originally written in {target_language}.

        Focus areas:
        1. Fluency and Natural Expression: Ensure the text flows naturally, as if originally conceived in {target_language}. Pay special attention to sentence structures, sentence lengths and expressions that are characteristic of native {target_language} writing.
        2. Coherence and Text Flow: Improve the logical progression of ideas. Ensure sentences and paragraphs transition smoothly, creating a seamless narrative.
        3. Idiomatic Usage: Incorporate idiomatic expressions where appropriate to enhance the text's authenticity in {target_language}.
        4. Cultural Adaptation: Adjust any remaining cultural references or concepts to resonate more deeply with a {target_language} audience.
        5. Consistency in Style and Tone: Maintain a consistent voice throughout the text that feels very authentic to {target_language} writing conventions.
        6. Precision and Clarity: While maintaining fluency, ensure that the key messages of the text are communicated with immediate clarity. 

        Translated text: {translated_text}

        Please provide your refined version, without any comments:
        """
    )
    return run_model([{"role": "user", "content": prompt.format(translated_text=translated_text, target_language=target_language)}], temp_choice, select_model)

def polish_text(edited_text, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["edited_text", "target_language"],
        template="""
        You are a master wordsmith and literary expert in {target_language}, known for your ability to craft prose that captivates and flows effortlessly. you are highly specialized in the sector of large medical and human rights NGO's.  
        Your task is to take the following text and elevate it to the highest level of fluency and coherence in {target_language}.

        Guidelines:
        1. Seamless Flow: Ensure each sentence flows naturally into the next, creating a rhythm that feels deeply inherent to {target_language}.
        2. Conceptual Coherence: Refine the progression of ideas so that the entire text feels like a single, cohesive thought conceived in {target_language}.
        3. Linguistic Authenticity: Use turns of phrase, transitional expressions, and structural elements that are quintessentially {target_language}, making the text feel deeply rooted in the language.
        4. Elegance and Precision: While maintaining elegance, aim at conveying the key messages with extreme precision and clarity.
        5. Emotional Resonance: Adjust the tone and word choice to evoke the appropriate emotional response in a native {target_language} reader.
        6. Rhythm and Cadence: Pay attention to the rhythm of the language, ensuring it aligns with the natural cadence of {target_language} prose.
        
        Your goal is to make this text indistinguishable from one originally conceived and masterfully written in {target_language}.
        While you can profoundly rephrase the text in line with the guidelines, you must not add new information. Maintain the original meaning and content without hallucinating or expanding beyond the given text. 
       
        Text to polish:
        {edited_text}

        Please provide your polished version, without adding any comment:
        """
    )
    return run_model([{"role": "user", "content": prompt.format(edited_text=edited_text, target_language=target_language)}], temp_choice, select_model)

def process_feedback(polished_text, human_feedback, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["polished_text", "human_feedback", "target_language"],
        template="""
        You are an expert linguist and editor specializing in {target_language}. Your task is to refine the translation below, incorporating the provided human feedback to ensure accuracy, clarity, and fluency.

        Original Translation: {polished_text}

        Human Feedback: {human_feedback}

        Please provide your revised translation directly, without any additional explanations or comments:
        """
    )
    return run_model([{"role": "user", "content": prompt.format(polished_text=polished_text, human_feedback=human_feedback, target_language=target_language)}], temp_choice, select_model)

def translate_enhancetool(text, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["text", "target_language"],
        template="""
        You are a professional translator with expertise in {target_language}, specializing in the sectors of large medical NGOs and human rights. 
        Your task is to translate the following text into {target_language} so that it is clear, convincing, and authentic to a native speaker.

        Guidelines:
        1. **Accuracy and Adaptability**: Faithfully reflect the original meaning, adapting where necessary to maintain the nuances of {target_language}. Avoid adding new information or content not present in the original text.
        2. **Terminology**: Use precise and consistent terminology. Refer to [insert preferred glossary/resource if available] as needed.
        3. **Cultural Sensitivity**: Adjust cultural references to resonate with the target audience. For ambiguous or culture-specific terms, choose the most appropriate translation and add a brief explanation in parentheses if absolutely necessary.
        4. **Fluidity and Naturalness**: Ensure the translation reads smoothly and naturally, as if originally written in {target_language}.
        5. **Language Conventions**: Adhere to grammatical, spelling, and formatting conventions specific to {target_language}.
        6. **Professional Tone**: Maintain a formal tone suitable for medical and human rights contexts, unless the original text suggests a different style.
        7. **Clarity and Effectiveness**: Prioritize clarity and ensure the translation effectively conveys the intended message. Avoid ambiguity and make sure the translation is easy to read and understand.

         Text to translate: {text}
         
         Please review your translation against the previous guidelines to ensure it meets the highest standards before submitting. The submitted text must be of the highest quality on all aspects.

         Provide only the finally approved translation, without any additional comments or explanations."""
    )
    return run_model([{"role": "user", "content": prompt.format(text=text, target_language=target_language)}], temp_choice, select_model)

def enhancetool(text, guidelines, target_language, temp_choice, select_model):
    prompt = PromptTemplate(
        input_variables=["text", "target_language", "guidelines"],
        template="""
        You are an expert writer and editor in {target_language}. 
        Your task is to improve significantly the following text, with a major focus on optimizing natural fluency, clarity and effectiveness.

        You must also follow the guidelines provided by the human feedback:
        {guidelines}
                                
        The improvement process must be deployed in two steps:
        
        1. **Initial Evaluation**
            - Identify the strengths and weaknesses of the text in terms of fluency, clarity and effectiveness.
            - Develop ideas and suggestion to adapt the text in line with the guidelines
        2. **Improvement**
            Based on the initial evaluation, adjust the structure, content, style, tone, and vocabulary to fully align with the peovided task and guidelines.
          
        Text to evaluate and improve:
        {text}

        The answer only contains the improved text version, and not the results of the initial evaluation or other comments. 
        """ 
    )
    return run_model([{"role": "user", "content": prompt.format(text=text, guidelines=guidelines, target_language=target_language)}], temp_choice, select_model)

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
    # List of predefined language options
    languages = ["Dutch", "French", "English", "Other"]
    
    # Selectbox for choosing the language
    language_choice = st.selectbox("Choose target language:", languages, index=1, key=f'to_lang_{key_suffix}')
    
    # Conditional display of text input when "Other" is selected
    if language_choice == "Other":
        language_choice = st.text_input("Please specify target language:")
        st.write(f"You have selected: {language_choice}")
    else:
        st.write(f"You have selected: {language_choice}")
    return language_choice
    
def display_temperature_slider(key_suffix):
    return st.slider('**Select a Temperature**', min_value=0.1, max_value=1.0, step=0.1, key=f'temp_{key_suffix}')

def refinement_factory_translation(select_model):
    st.subheader('Refinement Factory Translation')

    to_language = display_language_selection('refinement')
    temp_choice = display_temperature_slider('refinement')

    file_text = display_file_uploader()
    manual_text = display_text_input()
    
    combined_text = file_text + "\n" + manual_text if file_text or manual_text else None

    if 'refinement_factory' not in st.session_state:
        st.session_state.refinement_factory = {
            'original_text': '',
            'enhanced_translation': '',
            'swot_analysis': '',
            'editor_versions': {},
            'critique': {},
            'judgement_versions': [],
            'final_versions': {}
        }

    start_button = st.button('Start Refinement Factory Translation')

    if start_button and combined_text:
        source_lang = detect_language(combined_text)
        st.write(f"Detected language: {source_lang}")
        
        perform_refinement_factory(combined_text, to_language, temp_choice, select_model)
    elif start_button and not combined_text:
        st.error('Please upload or paste a text to translate.')

    display_refinement_results()

    st.sidebar.write("**Save final translations to file:**")    
    if st.sidebar.button('Save'):
        save_refinement_to_file(select_model, temp_choice)

def perform_refinement_factory(original_text, to_language, temp_choice, select_model):
    # Step 1: Initial translation and enhancement
    enhanced_translation = translate_and_enhance(original_text, to_language, temp_choice, select_model)
    st.session_state.refinement_factory['enhanced_translation'] = enhanced_translation
    
    # Step 2: SWOT analysis
    swot_analysis = perform_swot_analysis(enhanced_translation, to_language, temp_choice, "gpt-4o-mini")
    st.session_state.refinement_factory['swot_analysis'] = swot_analysis
    
    # Step 3: Specialized editors
    editors = [
        ('Medical/Scientific', 'arguments first, credibility minded'),
        ('Fundraiser/Marketeer', 'emotion first, engagement minded'),
        ('Activist/Lobbyist', 'message first, impact minded'),
        ('Journalist/writer', 'quality first, clarity minded'),
        ('Lawyer/philosopher', 'persuasiveness first, logic minded')
    ]
    
    for editor, focus in editors:
        edited_version = editor_refinement(enhanced_translation, swot_analysis, editor, focus, to_language, temp_choice, select_model)
        st.session_state.refinement_factory['editor_versions'][editor] = edited_version
    
    # Step 4: Critique
    critique = critique_versions(st.session_state.refinement_factory['editor_versions'], to_language, temp_choice, select_model)
    st.session_state.refinement_factory['critique'] = critique
    
    # Step 5: Judgement
    judgement_versions = judge_versions(st.session_state.refinement_factory['editor_versions'], critique, to_language, temp_choice, select_model)
    st.session_state.refinement_factory['judgement_versions'] = judgement_versions
    
    # Step 6: Editor in Chief
    final_versions = editor_in_chief(judgement_versions, to_language, temp_choice, select_model)
    st.session_state.refinement_factory['final_versions'] = final_versions

def translate_and_enhance(text, target_language, temp_choice, select_model):
    translate_prompt = f"""
    You are a professional translator with expertise in {target_language}, specializing in the sectors of large medical NGOs and human rights. 
    Perform the translation in two steps:
    **Step 1**: Translate the following text into {target_language} so that it is cristal clear, extremely fluent and perfectly authentic to a native speaker.
    **Step2**: After translation, improve the text to meet the highest standards in terms of coherence, impact and fluency.

    Text to translate and enhance: {text}

    Provide only the final translation, after step 2, without any additional comments or explanations.
    """
    return run_model([{"role": "user", "content": translate_prompt}], temp_choice, select_model)

def perform_swot_analysis(text, target_language, temp_choice, select_model):
    swot_prompt = f"""
    As an expert analytical linguist specializing in {target_language}, conduct a comprehensive SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis of the following text. Your analysis should cover:
    
    **Linguistic elements:**
    - Vocabulary choice and appropriateness
    - Grammar and syntax
    - Idiomatic expressions and language authenticity
    
    **Structural components:**
    - Overall organization and flow of ideas
    - Paragraph structure and transitions
    - Clarity and coherence of arguments
        
    **Stylistic features:**
    - Tone and register
    - Rhetorical devices and their effectiveness
    - Adherence to genre conventions (if applicable)
        
    **Content and messaging:**
    - Clarity and accuracy of information
    - Persuasiveness of arguments
    - Relevance to the target audience
    
    **Cultural considerations:**
    - Cultural sensitivity and appropriateness
    - Localization effectiveness (if applicable)
        
    **Potential impact:**
    - Likely emotional and intellectual response of the target audience
    - Potential for achieving the text's apparent goals
    - Possible unintended interpretations or consequences
      
    Text to analyze: {text}
    
    Provide a concise yet thorough SWOT analysis, clearly delineating Strengths, Weaknesses, Opportunities, and Threats. 
    For each category, list 3 key points, ensuring a balanced and insightful evaluation. Conclude with a brief overall assessment of the text's effectiveness in achieving its apparent purpose. Copy
    """
    return run_model([{"role": "user", "content": swot_prompt}], temp_choice, select_model)

def editor_refinement(text, swot_analysis, editor_type, focus, target_language, temp_choice, select_model):
    editor_prompt = f"""
    As a {editor_type} Editor ({focus}) in {target_language}, refine the following text based on the provided SWOT analysis. 
    Focus on your specific area of expertise while improving the overall quality of the text.
    You should not make a new SWOT analysis of the refined version.

    Original text: {text}

    SWOT Analysis: {swot_analysis}

    Provide your refined version of the text without any further comment. 
    """
    return run_model([{"role": "user", "content": editor_prompt}], temp_choice, select_model)

def critique_versions(editor_versions, target_language, temp_choice, select_model):
    critique_prompt = f"""
    As a Critique Agent, compare and analyze the following 5 versions of a text in {target_language}. 
    For each version, provide a comprehensive critique and a summary of its strengths and weaknesses.

    Versions to analyze:
    {json.dumps(editor_versions, indent=2)}

    Provide a critique for each version, followed by a concise summary of strengths and weaknesses.
    """
    return run_model([{"role": "user", "content": critique_prompt}], temp_choice, select_model)

def judge_versions(editor_versions, critique, target_language, temp_choice, select_model):
    judge_prompt = f"""
    As a Judgement Agent, create three new versions of the text in {target_language} based on the following edited versions and their critique. 
    Combine the strongest parts of all inputs to create texts that excel on all levels with seamless flow and strong structure.

    Edited versions:
    {json.dumps(editor_versions, indent=2)}

    Critique:
    {critique}

    Provide three new versions of the text, each embodying the best elements from the inputs while maintaining coherence and flow.
    Label each version as "Version 1:", "Version 2:", and "Version 3:" respectively.
    """
    response = run_model([{"role": "user", "content": judge_prompt}], temp_choice, select_model)
    return parse_versions(response)

def editor_in_chief(judgement_versions, target_language, temp_choice, select_model):
    # Construct the prompt for the model
    chief_editor_prompt = f"""
    As the Editor-in-Chief, review the following three versions of the text in {target_language}. 
    Your task is to create one "Recommended Version" and one "Alternative Version." You may make further edits as needed.

    Judgement versions:
    {json.dumps(judgement_versions, indent=2)}
    
    Please use your editorial judgment to assess these versions.

    Provide two final versions: 
    1) Label the absolutely recommended text as "Recommended Version:"
    2) Label the alternative version as "Alternative Version:"
    """

    # Run the model with the constructed prompt
    response = run_model([{"role": "user", "content": chief_editor_prompt}], temp_choice, select_model)

    # Parse the response to extract the two versions
    return parse_versions(response, keys=["Recommended Version:", "Alternative Version:"])

def parse_versions(text, keys=None):
    if keys is None:
        keys = ["Version 1:", "Version 2:", "Version 3:"]
    result = {}
    current_key = None
    current_text = []
    
    for line in text.split('\n'):
        if any(key in line for key in keys):
            if current_key:
                result[current_key] = '\n'.join(current_text).strip()
                current_text = []
            current_key = next(key for key in keys if key in line)
        elif current_key:
            current_text.append(line)
    
    if current_key:
        result[current_key] = '\n'.join(current_text).strip()
    
    return result

def display_refinement_results():
    if 'refinement_factory' in st.session_state and st.session_state.refinement_factory['final_versions']:
        st.write("Refinement process completed.")
        
        with st.expander("Initial Enhanced Translation"):
            st.write(st.session_state.refinement_factory['enhanced_translation'])
        
        with st.expander("SWOT Analysis"):
            st.write(st.session_state.refinement_factory['swot_analysis'])
        
        with st.expander("Specialized Editor Versions"):
            for editor, version in st.session_state.refinement_factory['editor_versions'].items():
                st.write(f"{editor} Editor's Version:")
                st.write(version)
                st.write("---")
        
        with st.expander("Critique"):
            st.write(st.session_state.refinement_factory['critique'])
        
        with st.expander("Judgement Versions"):
            judgement_versions = st.session_state.refinement_factory['judgement_versions']
            if isinstance(judgement_versions, dict):
                for key, version in judgement_versions.items():
                    st.write(f"{key}")
                    st.write(version)
                    st.write("---")
            else:
                st.write(judgement_versions)
        
        st.write("Final Versions:")
        final_versions = st.session_state.refinement_factory['final_versions']
        if isinstance(final_versions, dict):
            st.write("Absolutely Recommended Version:")
            st.write(final_versions.get('Recommended Version:', 'Not available'))
            st.write("Alternative Version:")
            st.write(final_versions.get('Alternative Version:', 'Not available'))
        else:
            st.write(final_versions)

def save_refinement_to_file(select_model, temp_choice):
    if 'refinement_factory' in st.session_state and st.session_state.refinement_factory['final_versions']:
        final_versions = st.session_state.refinement_factory['final_versions']
        
        content = f"{select_model}, Temp {temp_choice}:\n\n"
        if isinstance(final_versions, dict):
            content += f"Recommended Version:\n{final_versions.get('Recommended Version:', 'Not available')}\n\n"
            content += f"Alternative Version:\n{final_versions.get('Alternative Version:', 'Not available')}"
        else:
            content += f"Final Versions:\n{final_versions}"
        
        st.session_state.last_text = content
        if 'central_file' not in st.session_state:
            st.session_state.central_file = []
        st.session_state.central_file.append(st.session_state.last_text)
        st.success('Final versions added to central file!')
    else:
        st.error('No refined translations to save.')

def content_generation():
    
    from SimplerLLM.tools.generic_loader import load_content
    from SimplerLLM.language.llm import LLM, LLMProvider
    from resources import text_to_x_thread, text_to_summary, text_to_newsletter, format_to_json
    
    llm_instance = LLM.create(provider=LLMProvider.OPENAI, model_name="gpt-4o")
    
    st.title("Content Generation With A Single Click")
    
    input_text = st.text_input("Enter your text here:")
    
    if st.button("Generate Content"):
        if input_text:
            try:
                file = load_content(url)
    
                x_prompt = text_to_x_thread.format(input=input_text.content)
                newsletter_prompt = text_to_newsletter.format(input=input_text.content)
                summary_prompt = text_to_summary.format(input=input_text.content)
    
                x_thread = llm_instance.generate_response(prompt=x_prompt, max_tokens=1000)
                newsletter_section = llm_instance.generate_response(prompt=newsletter_prompt, max_tokens=1000)
                bullet_point_summary = llm_instance.generate_response(prompt=summary_prompt, max_tokens=1000)
    
                st.subheader("Generated Twitter Thread")
                st.write(x_thread)
                st.markdown("---")
    
                st.subheader("Generated Newsletter Section")
                st.write(newsletter_section)
                st.markdown("---")
    
                st.subheader("Generated Bullet Point Summary")
                st.write(bullet_point_summary)
                st.markdown("---")
    
                final_prompt = format_to_json.format(
                    input_1=x_thread, 
                    input_2=newsletter_section, 
                    input_3=bullet_point_summary
                )
                response = llm_instance.generate_response(prompt=final_prompt, max_tokens=3000)
                
                try:
                    json_data = json.loads(response)
                    st.markdown("### __Generated JSON Result__")
                    st.json(json_data)
                    st.download_button(
                        label="Download JSON Result",
                        data=json.dumps(json_data, ensure_ascii=False, indent=4),
                        file_name="Json_Result.json",
                        mime="application/json"
                    )
                except json.JSONDecodeError as e:
                    st.error(f"Error in JSON format: {e}")
                    st.write(response)
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter a text.")




# Main app logic
def main():
    st.sidebar.title("Translation App")
    pass_word = st.sidebar.text_input('Enter the password:', type="password")
    if not pass_word:
        st.stop()
    if pass_word != PASSWORD:
        st.error('The password you entered is incorrect.')
        st.stop()

    select_model = st.sidebar.radio('**Select your MODEL**', ['gpt-4o', 'MISTRAL large'])
    tool_choice = st.sidebar.radio("**Choose your tool:**", ['Single Agent', 'Multi-Agent', 'Refinement Factory', 'Content Generator'])
    st.sidebar.write("*The multi-agent system is likely to produce better results, albeit with a higher footprint and longer runtime.*")
    st.sidebar.write("*Making smart use of the feedback mechanisms can yield great results. Give it a try.*")
    st.sidebar.write("*The third tool is under construction.*")
    
    
    if tool_choice == 'Single Agent':
        translate_with_enhancement(select_model)
    elif tool_choice == 'Multi-Agent':
        multiagent_translation(select_model)
    elif tool_choice == 'Refinement Factory':
        st.title("***under construction***")
        refinement_factory_translation(select_model)    
    elif tool_choice == 'Content Generator':
        content_generation(
    manage_central_file()

def translate_with_enhancement(select_model):
    
    st.subheader('Translate and upgrade your text')
    
    to_language = display_language_selection('enhance')
    temp_choice = display_temperature_slider('enhance')
    st.write("Lower Temperature (~0.1 to 0.5): Recommended for more secure translations.")
    st.write("Higher Temperature (~0.6 to 1.0): Encourages more creative translations.")

    file_text = display_file_uploader()
    manual_text = display_text_input()
    
    combined_text = file_text + "\n" + manual_text if file_text or manual_text else None

    if 'translation_with_enhance' not in st.session_state:
        st.session_state.translation_with_enhance = ""

    translated_text = ""
    
    if st.button('Translate'):
        if combined_text:
            source_lang = detect_language(combined_text)
            st.write(f"Detected language: {source_lang}")
            translated_text = translate_enhancetool(combined_text, to_language, temp_choice, select_model)
            st.session_state.translation_with_enhance = f"{select_model}, Temp {temp_choice}, 'translated':\n\n{translated_text}"
            st.write("Current translation:")
            st.write(translated_text)
        else:
            st.error('Please upload or paste a text to translate.')

    if translated_text or ('translation_with_enhance' in st.session_state and st.session_state.translation_with_enhance):
        st.write('**Enhance text (latest in memory)**')
        guidelines = st.text_input("Provide extra details, clear guidelines and/or specific feedback to effectively guide the AI through the enhancement process.")
            
        if st.button('Enhance'):
            # If translated_text is empty, use the stored translation
            text_to_enhance = translated_text or st.session_state.translation_with_enhance.split('\n\n', 1)[1]
            enhanced_text = enhancetool(text_to_enhance, guidelines, to_language, temp_choice, select_model)
            st.session_state.translation_with_enhance = f"{select_model}, Temp {temp_choice}, enhanced:\n\n{enhanced_text}"
            st.write("Enhanced translation:")
            st.write(enhanced_text)
            st.write("Translation before enhancement")
            st.write(text_to_enhance)
            
    st.sidebar.write("**Save last translation to file:**")
    if st.sidebar.button('Save'):
        st.session_state.last_text = f"{select_model}, Temp {temp_choice}:\n\n{st.session_state.translation_with_enhance}"
        if 'central_file' not in st.session_state:
            st.session_state.central_file = []
        st.session_state.central_file.append(st.session_state.last_text)
        st.success('Text added to central file!')


def multiagent_translation(select_model):
    st.subheader('Multiagent Translation with Human Feedback')

    to_language = display_language_selection('multi')
    temp_choice = display_temperature_slider('multi')
    st.write("Lower Temperature (~0.1 to 0.5): Recommended for more secure translations.")
    st.write("Higher Temperature (~0.6 to 1.0): Encourages more creative translations.")

    file_text = display_file_uploader()
    manual_text = display_text_input()
    
    combined_text = file_text + "\n" + manual_text if file_text or manual_text else None

    if 'multiagent_translation' not in st.session_state:
        st.session_state.multiagent_translation = ""
        st.session_state.feedback_round = 0
        st.session_state.translation_complete = False

    start_button = st.button('Start Multiagent Translation')

    if start_button or st.session_state.multiagent_translation:
        if combined_text and start_button:
            source_lang = detect_language(combined_text)
            st.write(f"Detected language: {source_lang}")
            
            analysis = analyze_source_text(combined_text, temp_choice, select_model)
            translation = translate_text(combined_text, analysis, to_language, temp_choice, select_model)
            edited_translation = edit_translation(translation, to_language, temp_choice, select_model)
            polished_translation = polish_text(edited_translation, to_language, temp_choice, select_model)
            
            st.session_state.multiagent_translation = polished_translation
            st.session_state.feedback_round = 0
            st.session_state.translation_complete = False
        elif not combined_text and start_button:
            st.error('Please upload or paste a text to translate.')
            return

        st.write("Current translation:")
        st.write(st.session_state.multiagent_translation)

        
        human_feedback = st.text_area("**Provide feedback for improvement if needed:**", key="feedback_input")
        submit_feedback = st.button("Submit Feedback", key="submit_feedback")

        if submit_feedback:
            feedback_response = process_feedback(st.session_state.multiagent_translation, human_feedback, to_language, temp_choice, select_model)
            # revised_translation, explanation, confidence = parse_feedback_response(feedback_response)
            st.write("Revised translation:")
            st.write(feedback_response)
            # st.write(f"Explanation: {explanation}")
            # st.write(f"Confidence score: {confidence}")
            st.session_state.multiagent_translation = feedback_response
            st.session_state.feedback_round += 1
            # st.rerun()
            
        st.sidebar.write("**Save last translation to file:**")    
        if st.sidebar.button('Save'):
            st.session_state.last_text = f"{select_model}, Temp {temp_choice}:\n\n{st.session_state.multiagent_translation}"
            if 'central_file' not in st.session_state:
                st.session_state.central_file = []
            st.session_state.central_file.append(st.session_state.last_text)
            st.success('Text added to central file!')

def manage_central_file():
    st.sidebar.write("\n\n")
    if 'central_file' in st.session_state and st.session_state.central_file:
        st.sidebar.write('**Manage saved translations file:**')
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


