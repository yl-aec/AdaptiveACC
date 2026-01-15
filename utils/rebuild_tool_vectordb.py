"""
Script to rebuild the tool vector database with current domain tools
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import shutil
from datetime import datetime
from ifc_tools.ifc_tool_registry import IFCToolRegistry
from utils.rag_tool import ToolVectorManager
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from config import Config

def clear_vectordb():
    """Clear existing vector database"""
    vectordb_path = Path("vectordb") / "tools"

    if vectordb_path.exists():
        print(f"Clearing existing vectordb at {vectordb_path}...")
        shutil.rmtree(vectordb_path)
        print("OK: Old vectordb cleared")

    # Recreate directory
    vectordb_path.mkdir(parents=True, exist_ok=True)
    print(f"OK: Created fresh vectordb directory")

def create_fresh_vectordb():
    """Create a fresh empty vector database"""
    vectordb_path = Path("vectordb") / "tools"
    collection_name = "tool_vectors"

    # Create embeddings
    embedding_kwargs = {
        "model": Config.EMBEDDING_MODEL_NAME,
        "openai_api_key": Config.EMBEDDING_API_KEY,
        "dimensions": 1536
    }

    if Config.EMBEDDING_API_BASE:
        embedding_kwargs["openai_api_base"] = Config.EMBEDDING_API_BASE

    embeddings = OpenAIEmbeddings(**embedding_kwargs)

    # Create new empty Chroma collection
    vector_store = Chroma(
        persist_directory=str(vectordb_path),
        embedding_function=embeddings,
        collection_name=collection_name
    )

    print(f"OK: Created fresh Chroma collection '{collection_name}'")
    return vector_store

def extract_tool_metadata(tool_name: str, tool_schema: dict) -> dict:
    """Extract metadata from tool schema"""

    # Get function details
    function = tool_schema.get("function", {})
    parameters = function.get("parameters", {})
    properties = parameters.get("properties", {})

    # Extract parameter names
    param_names = list(properties.keys())

    # Extract description
    description = function.get("description", "")

    metadata = {
        "tool_name": tool_name,
        "description": description,
        "parameters": ", ".join(param_names)
    }

    return metadata

def rebuild_vectordb():
    """Main function to rebuild the vector database"""

    print("=" * 60)
    print("REBUILDING TOOL VECTOR DATABASE")
    print("=" * 60)

    # Step 1: Clear old vectordb
    print("\n[1/4] Clearing old vector database...")
    clear_vectordb()

    # Step 2: Create fresh vectordb
    print("\n[2/4] Creating fresh vector database...")
    vector_store = create_fresh_vectordb()

    # Step 3: Load domain tools
    print("\n[3/4] Loading domain tools from registry...")
    domain_registry = IFCToolRegistry.get_instance()
    tool_names = domain_registry.get_available_tools()
    tool_schemas = domain_registry.get_tools_json(api_format="openai-chatcompletion")

    print(f"Found {len(tool_names)} domain tools")

    # Step 4: Add tools to vectordb
    print("\n[4/4] Adding tools to vector database...")

    tools_added = 0
    tools_failed = 0

    # Create ToolVectorManager instance
    tool_vector_manager = ToolVectorManager.get_instance()
    # Force reload to use our fresh vector store
    tool_vector_manager.vector_store = vector_store

    for tool_schema in tool_schemas:
        function_name = tool_schema.get("function", {}).get("name", "unknown")

        try:
            # Extract metadata
            metadata = extract_tool_metadata(function_name, tool_schema)

            # Add to vectordb
            success = tool_vector_manager.add_tool(metadata)

            if success:
                tools_added += 1
                print(f"  [OK] Added: {function_name}")
            else:
                tools_failed += 1
                print(f"  [FAIL] Failed: {function_name}")

        except Exception as e:
            tools_failed += 1
            print(f"  [ERROR] Error adding {function_name}: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("REBUILD COMPLETE")
    print("=" * 60)
    print(f"Tools added: {tools_added}")
    print(f"Tools failed: {tools_failed}")
    print(f"Total: {len(tool_schemas)}")

    # Verify
    print("\n[Verification]")
    stats = tool_vector_manager.get_stats()
    print(f"Vector database stats: {stats}")

    return tools_added, tools_failed

if __name__ == "__main__":
    try:
        tools_added, tools_failed = rebuild_vectordb()

        if tools_failed == 0:
            print("\n[SUCCESS] All tools added to vector database")
        else:
            print(f"\n[WARNING] {tools_failed} tools failed to add")

    except Exception as e:
        print(f"\n[ERROR] Rebuild failed with error: {e}")
        import traceback
        traceback.print_exc()
