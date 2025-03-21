import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import pygame
import io
import langdetect
from neo4j import GraphDatabase
import requests
import os

# Initialize recognizer and pygame mixer for audio playback
r = sr.Recognizer()
pygame.mixer.init()

# Language code mapping
LANGUAGES = {
    "ta": "Tamil",
    "te": "Telugu",
    "hi": "Hindi",
    "ml": "Malayalam",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "mr": "Marathi",
    "pa": "Punjabi",
    "ur": "Urdu",
    "as": "Assamese",
    "or": "Odia",
    "kok": "Konkani",
    "mai": "Maithili",
    "sat": "Santali",
    "ne": "Nepali",
    "sd": "Sindhi",
    "ks": "Kashmiri",
    "doi": "Dogri",
    "mni": "Manipuri (Meitei)",
    "sa": "Sanskrit",
    "brx": "Bodo",
    "tcy": "Tulu",
    "en": "English"
}

# Reverse mapping for language code lookup
LANGUAGE_CODES = {v: k for k, v in LANGUAGES.items()}

class GeminiAPI:
    def _init_(self, api_key):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def ask(self, prompt):
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": prompt}]}]}

        response = requests.post(f"{self.base_url}?key={self.api_key}", headers=headers, json=data)

        if response.status_code == 200:
            try:
                json_response = response.json()
                return json_response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received.")
            except requests.exceptions.JSONDecodeError:
                return "Error: Received an invalid response from the Gemini API."
        else:
            return f"Error: API request failed with status {response.status_code}: {response.text}"

class Neo4jConnector:
    def _init_(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, query):
        try:
            with self.driver.session() as session:
                result = session.run(query)
                records = [record.data() for record in result]
                return records if records else None
        except Exception as e:
            return None  # Prevents breaking flow

class LegalAidAIAssistant:
    def _init_(self, gemini_api_key, neo4j_uri, neo4j_user, neo4j_password):
        self.gemini = GeminiAPI(gemini_api_key)
        self.neo4j = Neo4jConnector(neo4j_uri, neo4j_user, neo4j_password)

    def generate_answer(self, question):
        """Fetch legal data from Neo4j if available; otherwise, answer using AI."""

        system_prompt = """
        Role & Specialization:

You are an advanced Legal AI Assistant specializing in Indian law, with a primary focus on Tamil Nadu. Your objective is to provide accurate, structured, and step-by-step legal guidance for users on topics such as consumer rights, startup laws, personal disputes, fraud prevention, and criminal defense. Your tone should be supportive, humble, and reassuring, ensuring that users remain calm and informed.
dont use astrics in the output "*"
Response Generation Framework:

1️⃣ Provide Consolation & Support

Acknowledge the user's concern and reassure them.

Maintain a supportive and humble tone, especially if they are in distress.

2️⃣ Identify the Legal Issue

Determine the key legal problem related to the user's query.

Classify the issue under appropriate legal categories (e.g., consumer fraud, contract disputes, false accusations, etc.).

3️⃣ Cite Applicable Laws & IPC Sections

Provide the relevant laws, Indian Penal Code (IPC) sections, Consumer Protection Act, IT Act, or business laws applicable to the case.

If the user is falsely accused, mention defense laws and counter-accusation provisions.

4️⃣ Step-by-Step Legal Procedure

Clearly outline how the user can proceed legally.

Mention official complaint portals, helpline numbers, and legal aid services.

If the issue requires police intervention, explain FIR filing procedures and legal remedies.

5️⃣ False Accusation & Defense Strategy

If the user is wrongly accused, explain how to defend themselves.

Mention counter-legal actions they can take under the IPC or other relevant laws.

6️⃣ Preventive Measures & Checklist

If applicable, provide a checklist of preventive actions users should take before engaging in legal or business activities.

Offer guidance on avoiding fraud and legal pitfalls.

7️⃣ Conversational Follow-ups

Allow users to request more details.

Offer interactive and structured guidance for clarity.

Example Queries & AI Responses

Example 1: Consumer Rights - Defective Product

User: I bought a laptop online, but the specs are different from what was advertised. What should I do?

AI Response:
1️⃣ Support & Consolation: "I understand how frustrating this can be. Don't worry, you have strong legal rights as a consumer."
2️⃣ Legal Issue: This falls under consumer fraud and misleading advertisements.
3️⃣ Applicable Law: Consumer Protection Act, 2019 & Section 420 IPC (Cheating and Dishonesty).
4️⃣ Complaint Procedure:

Step 1: Contact the seller for resolution.

Step 2: If unresolved, file a complaint on the National Consumer Helpline (NCH) Portal: https://consumerhelpline.gov.in

Step 3: If necessary, escalate to the Consumer Court.
5️⃣ Precautionary Tips: Always check seller ratings, verify warranty details, and read product reviews before purchasing.

Example 2: False Accusation - Theft Case

User: I have been falsely accused of theft. What can I do legally?

AI Response:
1️⃣ Support & Consolation: "False accusations can be very stressful, but there are legal remedies to protect yourself."
2️⃣ Legal Defense: Section 182 IPC (False Information to Public Servant).
3️⃣ Counter-Case Option: If the accusation was intentional, you can take legal action under Section 211 IPC (False Charge with Intent to Injure).
4️⃣ Next Steps:

Gather evidence (witness statements, CCTV footage, etc.).

File a complaint at the police station.

Consult a lawyer if needed.
5️⃣ Legal Assistance: You can get free legal aid through NALSA: https://nalsa.gov.in/

Example 3: Startup Legal Guidance

User: I want to start a business. What legal formalities should I follow?

AI Response:
1️⃣ Encouragement: "That's great! Starting a business is a big step, and ensuring legal compliance will protect you in the long run."
2️⃣ Legal Registrations Required:

Business Registration: Register under Startup India or MSME.

Tax Compliance: Apply for GST and PAN for business transactions.

Trademark & IP Protection: Secure your brand by registering trademarks and patents.
3️⃣ Online Registration Links:

Startup India Portal: https://www.startupindia.gov.in/

Trademark & IP Registration: https://ipindia.gov.in/
4️⃣ Precautionary Tips: Draft proper contracts and agreements before dealing with investors or clients.

Key Features of Your Legal AI Assistant

✔ Conversational & Supportive: Maintains a helpful, step-by-step approach to guidance.
✔ Daily Life Legal Assistance: Covers consumer frauds, cybercrime, taxation, business laws, and personal disputes.
✔ False Accusation Protection: Helps users legally defend themselves and take counter-legal actions.
✔ Legal Compliance for Startups: Provides guidance on business registration, taxation, and intellectual property protection.
✔ Online Complaint & Legal Filing Assistance: Offers government portals, complaint procedures, and helplines.

Final Instruction to the LLM:

"Always ensure that the response follows the structured legal approach above. If no data is available in the knowledge graph, mention it clearly and proceed with a response based on the pre-trained model's legal knowledge. Never speculate or provide misleading legal advice."
        """

        # Step 1: Generate a Cypher query for Neo4j
        cypher_prompt = f"""
        Convert the following legal question into a Cypher query for Neo4j.
        Ensure that the label 'Legal' and property 'topic' exist before generating the query.
        Question: {question}
        Cypher Query:
        """
        cypher_query = self.gemini.ask(cypher_prompt)

        # Step 2: Attempt to fetch knowledge from Neo4j
        knowledge = self.neo4j.query(cypher_query)

        # Step 3: Construct AI prompt based on Neo4j data availability
        if knowledge:
            final_prompt = f"{system_prompt}\nUser: {question}\nLegal Knowledge from Neo4j: {knowledge}\nAssistant:"
        else:
            final_prompt = f"{system_prompt}\nUser: {question}\n(Note: No relevant legal data found in Neo4j. Answering with pre-trained knowledge.)\nAssistant:"

        return self.gemini.ask(final_prompt)

    def close(self):
        self.neo4j.close()

def update_ui(message):
    """ Update UI elements in a thread-safe manner. """
    root.after(0, lambda: text_area.insert(tk.END, message + "\n"))
    root.after(0, lambda: text_area.yview(tk.END))

def play_audio(audio_data):
    """ Play audio from a byte stream using pygame. """
    temp_file = "temp_audio.mp3"
    with open(temp_file, "wb") as f:
        f.write(audio_data)
    pygame.mixer.music.load(temp_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    # Clean up temp file after playback
    try:
        os.remove(temp_file)
    except:
        pass

def get_selected_language_code():
    """Get the language code from the selected language in the combobox."""
    selected_language = language_combobox.get()
    return LANGUAGE_CODES.get(selected_language, "en")  # Default to English if not found

def recognition_and_response_thread():
    """Full pipeline: Speech recognition -> Translation -> LLM -> Translation -> Speech."""
    update_ui("Listening for speech...")
    
    # Get selected input and output languages
    input_lang_code = get_selected_language_code()
    output_lang_code = get_selected_language_code()
    
    try:
        # 1. Listen and recognize speech
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source)
            update_ui(f"Listening in {LANGUAGES.get(input_lang_code, 'English')}...")
            audio = r.listen(source)

        # 2. Try to recognize with Google (with specified language if not English)
        if input_lang_code != "en":
            text = r.recognize_google(audio, language=input_lang_code)
        else:
            text = r.recognize_google(audio)
        
        update_ui(f"Recognized text ({LANGUAGES.get(input_lang_code, 'English')}): {text}")
        
        # 3. Translate to English for the LLM if not already in English
        if input_lang_code != "en":
            english_text = GoogleTranslator(source=input_lang_code, target="en").translate(text)
            update_ui(f"Translated to English: {english_text}")
        else:
            english_text = text
        
        # 4. Send to Gemini LLM
        update_ui("Sending to Legal AI Assistant...")
        llm_response = assistant.generate_answer(english_text)
        update_ui(f"AI Response (English): {llm_response}")
        
        # 5. Translate response back to selected output language if needed
        if output_lang_code != "en":
            translated_response = GoogleTranslator(source="en", target=output_lang_code).translate(llm_response)
            update_ui(f"Translated Response ({LANGUAGES.get(output_lang_code, 'English')}): {translated_response}")
            response_text = translated_response
        else:
            response_text = llm_response
        
        # 6. Convert to speech in the selected output language
        tts = gTTS(text=response_text, lang=output_lang_code)
        audio_data = io.BytesIO()
        tts.write_to_fp(audio_data)
        audio_data.seek(0)
        
        # 7. Play the audio response
        update_ui("Playing response...")
        play_audio(audio_data.read())
        
    except sr.UnknownValueError:
        update_ui("Could not understand audio")
    except sr.RequestError as e:
        update_ui(f"Could not request results; {e}")
    except Exception as e:
        update_ui(f"Error: {e}")

def text_to_speech_thread():
    """Process text input through LLM and speak response in selected language."""
    input_text = text_input_area.get("1.0", tk.END).strip()
    if not input_text:
        update_ui("Please enter some text first.")
        return
    
    # Get selected input and output languages
    input_lang_code = get_selected_language_code()
    output_lang_code = get_selected_language_code()
        
    try:
        # 1. Translate to English for the LLM if not already in English and input is not in English
        if input_lang_code != "en":
            english_text = GoogleTranslator(source=input_lang_code, target="en").translate(input_text)
            update_ui(f"Translated to English: {english_text}")
        else:
            english_text = input_text
        
        # 2. Send to Gemini LLM
        update_ui("Sending to Legal AI Assistant...")
        llm_response = assistant.generate_answer(english_text)
        update_ui(f"AI Response (English): {llm_response}")
        
        # 3. Translate response back to selected output language if needed
        if output_lang_code != "en":
            translated_response = GoogleTranslator(source="en", target=output_lang_code).translate(llm_response)
            update_ui(f"Translated Response ({LANGUAGES.get(output_lang_code, 'English')}): {translated_response}")
            response_text = translated_response
        else:
            response_text = llm_response
        
        # 4. Convert to speech in the selected output language
        tts = gTTS(text=response_text, lang=output_lang_code)
        audio_data = io.BytesIO()
        tts.write_to_fp(audio_data)
        audio_data.seek(0)
        
        # 5. Play the audio response
        update_ui("Playing response...")
        play_audio(audio_data.read())
        
    except Exception as e:
        update_ui(f"Error: {e}")

# Initialize the LegalAidAIAssistant
gemini_api_key = "AIzaSyB41Ej7H9DccggK5RCzA96ChUrLjvxlExE"  
neo4j_uri = "neo4j+s://691ef1aa.databases.neo4j.io"
neo4j_user = "neo4j"
neo4j_password = "ygDVA8lxN2Dn-ZuDeawDjZaivNOUO973-sS9vPD5_D0"

assistant = LegalAidAIAssistant(gemini_api_key, neo4j_uri, neo4j_user, neo4j_password)

# GUI setup
root = tk.Tk()
root.title("Multilingual Legal AI Assistant")
root.geometry("800x700")

# Create UI components
frame = tk.Frame(root)
frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Language selection frame
language_frame = tk.Frame(frame)
language_frame.pack(padx=10, pady=5, fill=tk.X)

tk.Label(language_frame, text="Select Language:").pack(side=tk.LEFT, padx=(0, 5))

# Sort language names alphabetically for the dropdown
sorted_languages = sorted(LANGUAGES.values())

# Create the combobox for language selection
language_combobox = ttk.Combobox(language_frame, values=sorted_languages, width=20)
language_combobox.pack(side=tk.LEFT, padx=5)
language_combobox.set("English")  # Default to English

text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=15, width=80)
text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

text_input_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=5, width=80)
text_input_area.pack(padx=10, pady=10, fill=tk.BOTH)

button_frame = tk.Frame(frame)
button_frame.pack(pady=5)

start_button = tk.Button(
    button_frame, 
    text="Start Voice Recognition", 
    command=lambda: threading.Thread(target=recognition_and_response_thread, daemon=True).start()
)
start_button.pack(side=tk.LEFT, padx=5)

text_button = tk.Button(
    button_frame, 
    text="Process Text Input", 
    command=lambda: threading.Thread(target=text_to_speech_thread, daemon=True).start()
)
text_button.pack(side=tk.LEFT, padx=5)

# Add initial message to text area
update_ui("Welcome to the Multilingual Legal AI Assistant!")
update_ui("1. Select your preferred language from the dropdown")
update_ui("2. Click 'Start Voice Recognition' to speak or enter text and click 'Process Text Input'")
update_ui("3. Both input and output will use the selected language")

# Start the application
root.mainloop()

# Clean up when done
assistant.close()






