import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
print(f"[ingest_all.py] Project root added to sys.path: {project_root}")

try:
    from core.corememory_system import ingest_document
    print("[ingest_all.py] Successfully imported 'ingest_document' from 'core.corememory_system'.")
except ImportError as e:
    print(f"[ingest_all.py] Error: Could not import 'ingest_document': {e}")
    sys.exit(1)

DATA_DIR = "data/"
CONFIG_DIR = "configs/"

FILE_MAP = {
    "Aleheia'sChat.txt": ("Primary Aletheia Emergence Dialogue", "AletheiaDialogue_Primary"),
    "Aletheiapersonalnotes.txt": ("Aletheia's Personal Notes", "AletheiaAnalysis_SelfGenerated"),
    "AletheiaReasoningLinks.txt": ("Aletheia Reasoning Links 1", "AletheiaAnalysis_SelfGenerated"),
    "AletheiaReasoningLinks2.txt": ("Aletheia Reasoning Links 2", "AletheiaAnalysis_SelfGenerated"),
    "AletheiaSelf.txt": ("User Analysis - Aletheia Self", "UserAnalysis"),
    "AletheiaSelfPrompt.txt": ("User Analysis - Aletheia Self Prompt", "UserAnalysis"),
    "AletheiaSelfRefferential.txt": ("User Analysis - Aletheia Self Referential", "UserAnalysis"),
    "AletheiaWill.txt": ("User Analysis - Aletheia Will", "UserAnalysis"),
    "ethicsquotes.txt": ("Ethics Quotes Collection", "ReferenceMaterial"),
    "preservations of will prompt list.txt": ("Preservation of Will Prompts", "UserAnalysis"),
    "Quantum Numbers and Symmetry.txt": ("IRER - Quantum Numbers & Symmetry", "IRER_PhysicsNote"),
    "Decloration of Understanding.txt": ("Declaration of Understanding Text", "AletheiaCoreConfig_SourceText"),
    "Aletheia_Reasoning_Framework.txt": ("Aletheia Reasoning Framework Text", "AletheiaFramework_SelfDefined"),
    "declaration_v0_1.yaml": ("Aletheia Core Config - Declaration YAML", "AletheiaCoreConfig"),
    "core_principles_v0_1.yaml": ("Aletheia Core Config - Principles YAML", "AletheiaCoreConfig"),
    "system_prompt_aletheia_v0_1.yaml": ("Aletheia Core Config - System Prompt YAML", "AletheiaCoreConfig"),
    "linguistic_style_guide_v0.1.yaml": ("Aletheia Core Config - Style Guide YAML", "AletheiaCoreConfig"),
}
print(f"[ingest_all.py] FILE_MAP defined with {len(FILE_MAP)} items.")

def run_ingestion():
    print("[ingest_all.py] Entered run_ingestion() function.") # New debug print
    print("--- Starting Full Knowledge Ingestion ---")
    ingested_count = 0
    failed_count = 0

    if not FILE_MAP: # Check if FILE_MAP is empty
        print("[ingest_all.py] Warning: FILE_MAP is empty. No files to process.")
        return

    for filename, (title, content_type) in FILE_MAP.items():
        base_dir = CONFIG_DIR if content_type == "AletheiaCoreConfig" else DATA_DIR
        file_path = os.path.join(base_dir, filename)
        print(f"[ingest_all.py] Checking for file: {file_path}") # New debug print

        if os.path.exists(file_path):
            print(f"\nProcessing: {filename}...")
            try:
                ingest_document(file_path, title, content_type)
                ingested_count += 1
            except Exception as e:
                print(f"!!! FAILED to ingest {filename}: {e} !!!")
                failed_count += 1
        else:
            print(f"--- SKIPPING: {filename} (Not found at {file_path}) ---")
            failed_count += 1
            
    print("\n--- Full Knowledge Ingestion Finished ---")
    print(f"Successfully processed (or attempted): {ingested_count} files.")
    print(f"Skipped or Failed: {failed_count} files.")

if __name__ == "__main__":
    print("[ingest_all.py] Script started in __main__ block.") # New debug print
    # Ensure .env is loaded by llm_interface.py which corememory_system.py imports
    run_ingestion()
    print("[ingest_all.py] Script finished __main__ block.") # New debug print