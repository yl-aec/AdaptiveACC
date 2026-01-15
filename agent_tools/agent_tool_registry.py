from toolregistry import ToolRegistry
from utils.base_classes import Singleton


class AgentToolRegistry(Singleton):
    """Singleton registry managing all agent tool interfaces"""

    def _initialize(self):
        """Initialize AgentToolRegistry instance"""
        # Create and manage the global ToolRegistry
        self.registry = ToolRegistry()

    # Proxy methods to underlying ToolRegistry
    def get_available_tools(self):
        """Get list of available tool names"""
        return self.registry.get_available_tools()

    def get_tools_json(self, api_format="openai-chatcompletion"):
        """Get tools schema in JSON format"""
        try:
            return self.registry.get_tools_json(api_format=api_format)
        except TypeError:
            # Older toolregistry versions do not accept api_format.
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

    def get_callable(self, tool_name):
        """Get a callable function by name"""
        return self.registry.get_callable(tool_name)
