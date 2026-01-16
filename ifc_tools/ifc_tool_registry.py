from pathlib import Path
from toolregistry import ToolRegistry
import importlib.util
from utils.base_classes import Singleton


class IFCToolRegistry(Singleton):
    """Singleton IFC Tool Registry for global access to IFC tools"""

    def _initialize(self):
        self.registry = ToolRegistry()
        self._register_tools()
        print("IFCToolRegistry: Singleton instance initialized")


    def _register_tools(self):
        """Register tools from core and generated directories"""

        total_loaded = 0

        # 1. Load core tools (manually created tools)
        print("Loading core tools...")
        core_loaded = self._load_tools_from_base_dir("ifc_tools/core")
        total_loaded += core_loaded
        if core_loaded > 0:
            print(f"IFCToolRegistry: Loaded {core_loaded} core tools")

        # 2. Load generated tools (agent-created tools)
        print("Loading generated tools...")
        generated_loaded = self._load_tools_from_base_dir("ifc_tools/generated")
        total_loaded += generated_loaded
        if generated_loaded > 0:
            print(f"IFCToolRegistry: Loaded {generated_loaded} generated tools")

        print(f"IFCToolRegistry: Total loaded {total_loaded} tools (core: {core_loaded}, generated: {generated_loaded})")

    def _load_tools_from_base_dir(self, base_dir: str) -> int:
        """Load tools from a base directory with category subdirectories"""
        tools_base_dir = Path(base_dir)
        if not tools_base_dir.exists():
            return 0

        total_loaded = 0

        # Discover all category directories
        for category_dir in tools_base_dir.iterdir():
            if (category_dir.is_dir() and
                not category_dir.name.startswith('.') and
                category_dir.name != '__pycache__'):

                category_name = category_dir.name
                category_loaded = self._load_tools_from_category_path(category_dir, category_name, base_dir)
                total_loaded += category_loaded

        return total_loaded

    def _load_tools_from_category_path(self, category_dir: Path, category_name: str, base_dir: str) -> int:
        """Load all tools from a specific category directory path"""
        loaded_count = 0

        if not category_dir.exists():
            return 0

        for tool_file in category_dir.glob("*.py"):
            tool_name = tool_file.stem

            # Skip __init__.py files
            if tool_name == "__init__":
                continue

            try:
                # Use importlib to load the module
                spec = importlib.util.spec_from_file_location(
                    f"{base_dir.replace('/', '_')}_{category_name}_{tool_name}", tool_file
                )
                if spec is None or spec.loader is None:
                    print(f"Warning: Could not create spec for {category_name}/{tool_name}")
                    continue

                module = importlib.util.module_from_spec(spec)

                spec.loader.exec_module(module)

                # Register all functions defined in this module (not imported)
                functions_registered = 0

                for attr_name in dir(module):
                    if (attr_name.startswith('_') or
                        attr_name in ['Dict', 'Any', 'List', 'Optional', 'Callable']):  # Skip private and type imports
                        continue

                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, '__doc__'):
                        # Only register functions (not classes) defined in this module
                        if hasattr(attr, '__module__') and not isinstance(attr, type):
                            # Strict check: only register functions defined in the current module
                            # This excludes all imported functions (including from ifc_tool_utils)
                            if attr.__module__ == module.__name__:
                                try:
                                    self.registry.register(attr)
                                    functions_registered += 1
                                    print(f"Loaded {category_name} tool: {tool_name} (function: {attr_name}) -> registered as: {attr.__name__}")
                                except Exception as e:
                                    # Skip this function if it can't be registered (e.g., unsupported types)
                                    print(f"Skipped {category_name}/{tool_name}.{attr_name}: {str(e)[:80]}")
                                    continue

                if functions_registered > 0:
                    loaded_count += functions_registered
                else:
                    print(f"Warning: No valid function found in {category_name}/{tool_name}")

            except Exception as e:
                print(f"Failed to load {category_name} tool {tool_name}: {e}")

        return loaded_count

    # Proxy methods to underlying ToolRegistry
    def get_available_tools(self):
        """Get list of available tool names"""
        return self.registry.get_available_tools()
    
    def get_tools_json(self, api_format="openai-chatcompletion"):
        """Get tools schema in JSON format"""
        try:
            return self.registry.get_tools_json(api_format=api_format)
        except TypeError:
            return self.registry.get_tools_json()
    
    def execute_tool_calls(self, tool_calls):
        """Execute tool calls"""
        return self.registry.execute_tool_calls(tool_calls)
    
    def register(self, func):
        """Register a new tool function"""
        return self.registry.register(func)
    
    def get_tool(self, tool_name):
        """Get a specific tool by name"""
        return self.registry.get_tool(tool_name)      
