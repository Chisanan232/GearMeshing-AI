"""
Test settings model for GearMeshing-AI smoke tests.

This module provides a Pydantic-based settings model specifically for testing,
with environment variable loading from a test-specific .env file.
"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field, SecretStr, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load test environment variables
TEST_ENV_PATH = Path(__file__).parent / ".env"
if TEST_ENV_PATH.exists():
    load_dotenv(TEST_ENV_PATH)
elif Path(__file__).parent.parent / ".env".exists():
    # Try parent directory .env as fallback
    load_dotenv(Path(__file__).parent.parent / ".env")

class TestModelSettings(BaseModel):
    """Test settings for a specific AI model configuration."""
    customized_name: str = Field(..., description="Unique name for this model configuration")
    provider: str = Field(..., description="The provider name (e.g., openai, anthropic)")
    model: str = Field(..., description="The specific model identifier (e.g., gpt-4, claude-3-opus)")
    api_key: Optional[SecretStr] = Field(None, description="API Key for the provider")
    api_base: Optional[str] = Field(None, description="Base URL for the API")
    temperature: float = Field(0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Provider specific parameters")

class TestAgentSettings(BaseModel):
    """Test settings for an AI agent."""
    role: str = Field(..., description="Unique role identifier for the agent")
    description: str = Field(..., description="Description of the agent's purpose")
    model_settings: TestModelSettings = Field(..., description="Configuration for the underlying model")
    tools: List[str] = Field(default_factory=list, description="List of tool names/identifiers this agent can use")
    system_prompt: Optional[str] = Field(None, description="System prompt to initialize the agent context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the agent")

class TestSettings(BaseSettings):
    """Main test settings container for GearMeshing-AI tests."""
    
    # AI Provider configurations
    openai_api_key: Optional[SecretStr] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[SecretStr] = Field(None, description="Anthropic API key")
    gemini_api_key: Optional[SecretStr] = Field(None, description="Google Gemini API key")
    
    # Test execution flags
    run_ai_tests: bool = Field(True, description="Whether to run tests that call real AI models")
    run_slow_tests: bool = Field(False, description="Whether to run slow integration tests")
    test_timeout: int = Field(60, description="Timeout for individual tests in seconds")
    
    # Model configurations for testing
    test_models: Dict[str, TestModelSettings] = Field(default_factory=dict, description="Test model configurations")
    test_agents: Dict[str, TestAgentSettings] = Field(default_factory=dict, description="Test agent configurations")
    
    model_config = SettingsConfigDict(
        env_file=str(TEST_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._setup_default_configurations()
    
    def _setup_default_configurations(self):
        """Setup default test configurations if API keys are available."""
        
        # Default OpenAI model configuration
        if self.openai_api_key:
            self.test_models["openai_gpt4"] = TestModelSettings(
                customized_name="openai_gpt4",
                provider="openai",
                model="gpt-4",
                api_key=self.openai_api_key,
                temperature=0.7,
                max_tokens=1000
            )
            
            self.test_agents["test_assistant"] = TestAgentSettings(
                role="test_assistant",
                description="A test assistant for smoke testing",
                model_settings=self.test_models["openai_gpt4"],
                system_prompt="You are a helpful test assistant. Respond briefly and accurately.",
                tools=[]
            )
        
        # Default Anthropic model configuration
        if self.anthropic_api_key:
            self.test_models["anthropic_claude"] = TestModelSettings(
                customized_name="anthropic_claude",
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key=self.anthropic_api_key,
                temperature=0.7,
                max_tokens=1000
            )
            
            self.test_agents["claude_assistant"] = TestAgentSettings(
                role="claude_assistant",
                description="A Claude-based test assistant",
                model_settings=self.test_models["anthropic_claude"],
                system_prompt="You are a helpful Claude test assistant. Respond briefly and accurately.",
                tools=[]
            )
        
        # Default Gemini model configuration
        if self.gemini_api_key:
            self.test_models["gemini_pro"] = TestModelSettings(
                customized_name="gemini_pro",
                provider="google",
                model="gemini-pro",
                api_key=self.gemini_api_key,
                temperature=0.7,
                max_tokens=1000
            )
            
            self.test_agents["gemini_assistant"] = TestAgentSettings(
                role="gemini_assistant",
                description="A Gemini-based test assistant",
                model_settings=self.test_models["gemini_pro"],
                system_prompt="You are a helpful Gemini test assistant. Respond briefly and accurately.",
                tools=[]
            )
    
    def get_available_providers(self) -> List[str]:
        """Get list of available AI providers based on API keys."""
        providers = []
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.gemini_api_key:
            providers.append("google")
        return providers
    
    def has_provider(self, provider: str) -> bool:
        """Check if a specific provider has API key configured."""
        provider = provider.lower()
        if provider == "openai":
            return self.openai_api_key is not None
        elif provider == "anthropic":
            return self.anthropic_api_key is not None
        elif provider in ["google", "gemini"]:
            return self.gemini_api_key is not None
        return False

# Singleton instance for use across tests
test_settings = TestSettings()
