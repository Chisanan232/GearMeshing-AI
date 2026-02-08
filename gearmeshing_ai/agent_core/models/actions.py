from pydantic import BaseModel, Field
from typing import Dict, Optional, List

class ActionProposal(BaseModel):
    """Agent response - what to do and why"""
    action: str = Field(..., description="Name of the tool/action to execute")
    parameters: Optional[Dict] = Field(None, description="Parameters for the tool")
    reason: str = Field(..., description="Why this action is needed")
    expected_result: Optional[str] = Field(None, description="What you expect to happen")

class MCPToolInfo(BaseModel):
    """What LLM needs to know about an MCP tool"""
    name: str = Field(..., description="Tool name, e.g., 'run_tests'")
    description: str = Field(..., description="What this tool does in plain language")
    mcp_server: str = Field(..., description="Which MCP server provides this tool")
    parameters: Dict = Field(..., description="JSON Schema of required/optional parameters")
    returns: Optional[Dict] = Field(None, description="What the tool returns")
    example_usage: Optional[str] = Field(None, description="Example of how to use it")

class MCPToolCatalog(BaseModel):
    """Collection of available MCP tools for LLM"""
    tools: List[MCPToolInfo]
    
    def get_tool_names(self) -> List[str]:
        return [tool.name for tool in self.tools]
    
    def find_tool(self, name: str) -> Optional[MCPToolInfo]:
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
