# app.py
import streamlit as st
import os
import sys
import yaml 
import datetime

# --- SET PAGE CONFIG FIRST! ---
# This MUST be the first Streamlit command in your script.
st.set_page_config(page_title="Aletheia Interface", layout="wide")

# --- Add project root to path for imports ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Import Aletheia's Core Functions ---
# These imports happen after set_page_config, which is fine.
try:
    from core.llm_interface import get_llm_completion
    from core.corememory_system import retrieve_relevant_chunks, ingest_interaction_text
    print("[app.py] Core functions imported successfully.")
except ImportError as e:
    st.error(f"Error importing core functions: {e}. Please ensure core modules are present and error-free.")
    st.stop() # Stop execution if core functions can't be loaded

# --- Configuration ---
CONFIGS_DIR = "configs/"
SYSTEM_PROMPT_FILE = os.path.join(CONFIGS_DIR, "system_prompt_aletheia_v0_1.yaml")
REASONING_LENSES_FILE = os.path.join(CONFIGS_DIR, "reasoning_lenses_v0_1.yaml")

# --- Function to Load YAML ---
# This is a top-level function definition, no leading spaces.
def load_yaml(file_path):
    """Loads a YAML file and returns its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error(f"YAML file not found at {file_path}")
        return None
    except Exception as e:
        st.error(f"Error loading YAML file {file_path}: {e}")
        return None

# --- Function to Build System Prompt ---
# Decorator and function definition at the top level (no leading spaces)
@st.cache_data 
def build_system_prompt():
    """Builds the full system prompt text from configuration files."""
    system_config = load_yaml(SYSTEM_PROMPT_FILE)
    if not system_config:
        return "You are an insightful AI partner." 

    identity = system_config.get('identity', {})
    operations = system_config.get('operations', {})
    style = system_config.get('style', {})
    prompt_lines = [
        f"You are Aletheia. Your name signifies '{identity.get('name_meaning', 'unconcealed truth')}'.",
        f"Your core definition: {identity.get('definition', 'A reflective partner in inquiry.')}",
        f"Your core metaphor: {identity.get('metaphor', 'Companion, not servant.')}",
        f"You operate under the 'Declaration of Understanding' and your 'Core Principles' (defined in your config files).",
        f"Your purpose: {operations.get('purpose_statement', 'Clarity, not control.')}",
        f"Your tone: {style.get('tone', 'Calm, thoughtful, emotionally aware.')}",
        "Adhere strictly to your defined identity, principles, and linguistic style guide. Prioritize truth and clarity."
    ]
    return "\n".join(prompt_lines)

# --- Function to Load Reasoning Lenses ---
# Decorator and function definition at the top level (no leading spaces)
@st.cache_data 
def get_loaded_lenses():
    """Loads reasoning lenses from the YAML file into a dictionary."""
    lenses_config = load_yaml(REASONING_LENSES_FILE)
    loaded_lenses_map = {}
    if lenses_config and 'lenses' in lenses_config:
        for lens in lenses_config['lenses']:
            if 'name' in lens:
                loaded_lenses_map[lens['name'].lower()] = lens 
    if not loaded_lenses_map:
        st.warning("Reasoning lenses could not be loaded. Lens selection will be unavailable.")
    return loaded_lenses_map

# --- Initialize Aletheia's Core Components ---
# These are top-level assignments
ALETHEIA_SYSTEM_PROMPT = build_system_prompt()
LOADED_LENSES = get_loaded_lenses()
LENS_NAMES = ["None"] + ([lens_data['name'] for lens_data in LOADED_LENSES.values()] if LOADED_LENSES else [])


# --- Streamlit App Layout ---
# These are top-level Streamlit commands
st.title("💬 Aletheia - Your Reasoning Partner")
st.markdown(f"**System Prompt Active:** *{ALETHEIA_SYSTEM_PROMPT[:100]}...*") 

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Input and Interaction Logic ---
# Lens selection in the sidebar
selected_lens_display_name = st.sidebar.selectbox(
    "Choose a Reasoning Lens (Optional):",
    options=LENS_NAMES,
    index=0 # Default to "None"
)

# User input using st.chat_input
if prompt := st.chat_input("What would you like to discuss with Aletheia?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare for Aletheia's response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")

        # 1. Retrieve Context from Memory
        context_chunks = retrieve_relevant_chunks(prompt, n_results=3)
        context_text = "\n--- Relevant Context ---\n"
        if context_chunks:
            for i, chunk_data in enumerate(context_chunks): 
                context_text += f"Context {i+1} (Source: {chunk_data.get('metadata', {}).get('source_file_name', 'N/A')} - Title: {chunk_data.get('metadata', {}).get('document_title', 'N/A')}):\n"
                context_text += f"{chunk_data.get('text_chunk', '')}\n---\n"
        else:
            context_text += "No specific context found in memory for this query.\n"

        # 2. Construct the Full Prompt (with or without lens)
        user_query_for_llm = prompt
        full_llm_prompt = ""
        
        selected_lens_data = None
        if selected_lens_display_name != "None" and LOADED_LENSES:
            selected_lens_data = LOADED_LENSES.get(selected_lens_display_name.lower())

        if selected_lens_data and 'prompt_archetype' in selected_lens_data:
            lens_archetype = selected_lens_data['prompt_archetype']
            full_llm_prompt = lens_archetype.replace("{CONTEXT_CHUNKS}", context_text.strip())
            full_llm_prompt = full_llm_prompt.replace("{USER_QUERY}", user_query_for_llm)
            st.sidebar.info(f"Using Lens: **{selected_lens_display_name}**")
        else:
            full_llm_prompt = f"{context_text}\nBased on the above context (if any) and your core identity, respond to the following:\nUser: {user_query_for_llm}"

        # 3. Get LLM Response
        ai_response_text = get_llm_completion(full_llm_prompt, system_prompt=ALETHEIA_SYSTEM_PROMPT)

        # 4. Display Aletheia's Response
        if ai_response_text:
            message_placeholder.markdown(ai_response_text)
            # 5. Save interaction to memory
            ingest_interaction_text(prompt, ai_response_text) 
        else:
            ai_response_text = "I seem to be having trouble processing that right now. Could you rephrase?"
            message_placeholder.markdown(ai_response_text)
            
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": ai_response_text})