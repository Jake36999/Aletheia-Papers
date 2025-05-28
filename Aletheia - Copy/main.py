import os
import sys
import yaml # For loading our config files

# --- Add project root to path for imports ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Import Aletheia's Core Functions ---
try:
    from core.llm_interface import get_llm_completion
    from core.corememory_system import retrieve_relevant_chunks, ingest_interaction_text
    print("[main.py] Core functions imported successfully.")
except ImportError as e:
    print(f"[main.py] Error importing core functions: {e}")
    print("Please ensure core/llm_interface.py and core/corememory_system.py exist and are error-free.")
    sys.exit(1)

# --- Configuration ---
CONFIGS_DIR = "configs/"
SYSTEM_PROMPT_FILE = os.path.join(CONFIGS_DIR, "system_prompt_aletheia_v0_1.yaml")
REASONING_LENSES_FILE = os.path.join(CONFIGS_DIR, "reasoning_lenses_v0_1.yaml") # <-- NEW

# --- Global variable for loaded lenses ---
LOADED_LENSES = {}

# --- Function to Load YAML ---
def load_yaml(file_path):
    """Loads a YAML file and returns its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: YAML file not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        return None

# --- Function to Load Reasoning Lenses ---
def load_reasoning_lenses():
    """Loads reasoning lenses from the YAML file into a dictionary."""
    global LOADED_LENSES
    lenses_config = load_yaml(REASONING_LENSES_FILE)
    if lenses_config and 'lenses' in lenses_config:
        for lens in lenses_config['lenses']:
            if 'name' in lens:
                LOADED_LENSES[lens['name'].lower()] = lens # Store by lowercase name for easy lookup
        print(f"[main.py] Successfully loaded {len(LOADED_LENSES)} reasoning lenses.")
    else:
        print("[main.py] Warning: Could not load reasoning lenses or file is improperly formatted.")

# --- Function to Build System Prompt ---
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

# --- Main Interaction Loop ---
def run_chat():
    """Runs the main interactive chat loop with Aletheia."""
    print("\n--- Aletheia Initializing ---")
    
    aletheia_system_prompt = build_system_prompt()
    print(f"[main.py] System prompt loaded. Length: {len(aletheia_system_prompt)} chars.")
    
    load_reasoning_lenses() # <-- Load lenses at startup
    
    print("\n--- Aletheia is ready. ---")
    print("To use a specific lens, type: lens: [lens_name] [your query]")
    print("Example: lens: Contextual Self-Referencing How does my latest idea about OIWs fit our past discussions?")
    print("Type 'quit' to exit.")

    while True:
        try:
            user_input_full = input("\nYou: ")
            if user_input_full.lower() == 'quit':
                print("Aletheia: Farewell. May your path be clear.")
                break
            if not user_input_full.strip():
                continue

            user_query = user_input_full
            selected_lens_name = None
            lens_archetype = None

            # Check if user wants to use a specific lens
            if user_input_full.lower().startswith("lens:"):
                parts = user_input_full.split(maxsplit=2) # lens: LensName query
                if len(parts) > 1:
                    potential_lens_name_command = parts[1].lower() 
                    # Match lens name, allowing for multi-word lens names
                    for known_lens_name_key in LOADED_LENSES.keys():
                        # Check if the command starts with a known lens name (case-insensitive)
                        # This allows for "lens: contextual self-referencing query" or "lens: contextual query"
                        # For simplicity, let's assume the user types the full lens name for now or we find the best match
                        # A more robust approach would be needed for partial matches or aliases
                        # For now, we'll try an exact match of the first part of the user's lens command
                        # to a known lens name (case-insensitive)
                        
                        # Attempt to match the user's specified lens name against loaded lenses
                        # This simple check requires user to type the lens name accurately
                        # More complex matching could be added later.
                        
                        # Let's split the command part into words for a more flexible match
                        command_words = potential_lens_name_command.split()
                        
                        # Check if the command words match any full lens name
                        # Trying to find a lens name that is a prefix of the user's command
                        matched_lens = None
                        for ln_key in LOADED_LENSES.keys():
                            # Simple check: if user's command STARTS with the lens name
                            # (e.g. "contextual self-referencing how does..." will match "contextual self-referencing")
                            if potential_lens_name_command.startswith(ln_key):
                                matched_lens = ln_key
                                break
                        
                        if matched_lens:
                            selected_lens_name = LOADED_LENSES[matched_lens]['name'] # Get the proper cased name
                            lens_archetype = LOADED_LENSES[matched_lens].get('prompt_archetype')
                            # The actual query is what remains after "lens: Lens Name "
                            # Reconstruct the query part
                            query_start_index = user_input_full.lower().find(matched_lens) + len(matched_lens)
                            user_query = user_input_full[query_start_index:].strip()
                            print(f"[main.py] Using Lens: '{selected_lens_name}' for query: '{user_query}'")
                            break # Found and processed lens command

            # 1. Retrieve Context from Memory (based on the actual user_query)
            print(f"[main.py] Retrieving context for query: '{user_query}'...")
            context_chunks = retrieve_relevant_chunks(user_query, n_results=3) 
            
            context_text = "\n--- Relevant Context ---\n"
            if context_chunks:
                for i, chunk in enumerate(context_chunks):
                    context_text += f"Context {i+1} (Source: {chunk['metadata'].get('source_file_name', 'N/A')} - Title: {chunk['metadata'].get('document_title', 'N/A')}):\n"
                    context_text += f"{chunk['text_chunk']}\n---\n"
            else:
                context_text += "No specific context found in memory for this query.\n"

            # 2. Construct the Full Prompt
            if lens_archetype:
                # Substitute placeholders in the lens archetype
                full_prompt = lens_archetype.replace("{CONTEXT_CHUNKS}", context_text.strip())
                full_prompt = full_prompt.replace("{USER_QUERY}", user_query)
            else:
                # Default prompt construction if no specific lens is used
                full_prompt = f"{context_text}\nBased on the above context (if any) and your core identity, respond to the following:\nUser: {user_query}"
            
            # 3. Get LLM Response
            print("[main.py] Thinking...")
            ai_response = get_llm_completion(full_prompt, system_prompt=aletheia_system_prompt)

            # 4. Print Aletheia's Response
            if ai_response:
                print(f"Aletheia: {ai_response}")
                # 5. Save this interaction back to memory
                print("[main.py] Saving interaction to memory...")
                ingest_interaction_text(user_input_full, ai_response) # Save the original full input
            else:
                print("Aletheia: I seem to be having trouble processing that right now. Could you rephrase?")

        except KeyboardInterrupt: 
            print("\nAletheia: Session interrupted. Farewell.")
            break
        except Exception as e:
            print(f"\n[main.py] An unexpected error occurred: {e}")

# --- Run the Chat when Script is Executed ---
if __name__ == "__main__":
    run_chat()