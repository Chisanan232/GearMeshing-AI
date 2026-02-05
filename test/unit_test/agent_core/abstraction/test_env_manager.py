"""
Unit tests for EnvManager implementation.
"""

import pytest
import os
from unittest.mock import patch, Mock
from pydantic import SecretStr

from gearmeshing_ai.agent_core.abstraction.env_manager import EnvManager
from gearmeshing_ai.core.models.setting import AIProviderSettings


class TestEnvManager:
    """Test cases for EnvManager implementation."""

    def test_env_manager_initialization(self):
        """Test EnvManager initialization."""
        env_manager = EnvManager()
        
        # Should have settings attribute
        assert hasattr(env_manager, 'settings')
        assert isinstance(env_manager.settings, AIProviderSettings)
        
        # Should have required methods
        assert hasattr(env_manager, 'validate_provider_keys')
        assert hasattr(env_manager, 'export_variables')
        assert hasattr(env_manager, 'get_settings')

    @patch('gearmeshing_ai.agent_core.abstraction.env_manager.AIProviderSettings')
    def test_env_manager_initialization_with_mock_settings(self, mock_settings_class):
        """Test EnvManager initialization with mocked settings."""
        mock_settings = Mock(spec=AIProviderSettings)
        mock_settings.openai_api_key = SecretStr("test-openai-key")
        mock_settings.anthropic_api_key = SecretStr("test-anthropic-key")
        mock_settings.gemini_api_key = None
        mock_settings_class.return_value = mock_settings
        
        with patch('gearmeshing_ai.core.models.setting.AIProviderSettings', mock_settings_class):
            env_manager = EnvManager()
        
        # Verify settings class was called
        mock_settings_class.assert_called_once()
        assert env_manager.settings is mock_settings

    def test_validate_provider_keys_openai(self):
        """Test provider key validation for OpenAI."""
        env_manager = EnvManager()
        
        # Mock settings with OpenAI key
        env_manager.settings.openai_api_key = SecretStr("sk-test-key")
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Test various case combinations
        assert env_manager.validate_provider_keys("openai") is True
        assert env_manager.validate_provider_keys("OpenAI") is True
        assert env_manager.validate_provider_keys("OPENAI") is True
        assert env_manager.validate_provider_keys("openAi") is True

    def test_validate_provider_keys_anthropic(self):
        """Test provider key validation for Anthropic."""
        env_manager = EnvManager()
        
        # Mock settings with Anthropic key
        env_manager.settings.openai_api_key = None
        env_manager.settings.anthropic_api_key = SecretStr("sk-ant-test-key")
        env_manager.settings.gemini_api_key = None
        
        # Test various case combinations
        assert env_manager.validate_provider_keys("anthropic") is True
        assert env_manager.validate_provider_keys("Anthropic") is True
        assert env_manager.validate_provider_keys("ANTHROPIC") is True

    def test_validate_provider_keys_gemini(self):
        """Test provider key validation for Gemini/Google."""
        env_manager = EnvManager()
        
        # Mock settings with Gemini key
        env_manager.settings.openai_api_key = None
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = SecretStr("test-gemini-key")
        
        # Test various names for Google provider
        assert env_manager.validate_provider_keys("gemini") is True
        assert env_manager.validate_provider_keys("Gemini") is True
        assert env_manager.validate_provider_keys("google") is True
        assert env_manager.validate_provider_keys("Google") is True
        assert env_manager.validate_provider_keys("GOOGLE") is True

    def test_validate_provider_keys_missing_keys(self):
        """Test provider key validation when keys are missing."""
        env_manager = EnvManager()
        
        # Mock settings with no keys
        env_manager.settings.openai_api_key = None
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # All should return False
        assert env_manager.validate_provider_keys("openai") is False
        assert env_manager.validate_provider_keys("anthropic") is False
        assert env_manager.validate_provider_keys("gemini") is False
        assert env_manager.validate_provider_keys("google") is False

    def test_validate_provider_keys_unsupported_provider(self):
        """Test provider key validation for unsupported providers."""
        env_manager = EnvManager()
        
        # Mock settings with some keys
        env_manager.settings.openai_api_key = SecretStr("test-key")
        
        # Unsupported providers should return False
        assert env_manager.validate_provider_keys("unsupported") is False
        assert env_manager.validate_provider_keys("huggingface") is False
        assert env_manager.validate_provider_keys("cohere") is False
        assert env_manager.validate_provider_keys("") is False

    def test_validate_provider_keys_case_insensitive(self):
        """Test that provider validation is case insensitive."""
        env_manager = EnvManager()
        
        # Mock settings with OpenAI key
        env_manager.settings.openai_api_key = SecretStr("test-key")
        env_manager.settings.anthropic_api_key = SecretStr("test-key")
        env_manager.settings.gemini_api_key = SecretStr("test-key")
        
        # Test various case combinations
        test_cases = [
            ("openai", True),
            ("OpenAI", True),
            ("OPENAI", True),
            ("OpenAi", True),
            ("oPeNaI", True),
            ("anthropic", True),
            ("Anthropic", True),
            ("ANTHROPIC", True),
            ("AnThRoPiC", True),
            ("gemini", True),
            ("Gemini", True),
            ("GEMINI", True),
            ("GeMiNi", True),
            ("google", True),
            ("Google", True),
            ("GOOGLE", True),
            ("GoOgLe", True),
            ("unsupported", False),
            ("huggingface", False),
        ]
        
        for provider, expected in test_cases:
            result = env_manager.validate_provider_keys(provider)
            assert result is expected, f"Failed for {provider}: expected {expected}, got {result}"

    @patch.dict(os.environ, {}, clear=True)
    def test_export_variables_with_all_keys(self):
        """Test exporting variables when all keys are present."""
        env_manager = EnvManager()
        
        # Mock settings with all keys
        env_manager.settings.openai_api_key = SecretStr("sk-openai-test")
        env_manager.settings.anthropic_api_key = SecretStr("sk-ant-anthropic-test")
        env_manager.settings.gemini_api_key = SecretStr("gemini-test-key")
        
        # Export variables
        env_manager.export_variables()
        
        # Verify environment variables are set
        assert os.environ.get("OPENAI_API_KEY") == "sk-openai-test"
        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-anthropic-test"
        assert os.environ.get("GEMINI_API_KEY") == "gemini-test-key"

    @patch.dict(os.environ, {}, clear=True)
    def test_export_variables_with_partial_keys(self):
        """Test exporting variables when only some keys are present."""
        env_manager = EnvManager()
        
        # Mock settings with only OpenAI key
        env_manager.settings.openai_api_key = SecretStr("sk-openai-test")
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Export variables
        env_manager.export_variables()
        
        # Verify only OpenAI key is exported
        assert os.environ.get("OPENAI_API_KEY") == "sk-openai-test"
        assert os.environ.get("ANTHROPIC_API_KEY") is None
        assert os.environ.get("GEMINI_API_KEY") is None

    @patch.dict(os.environ, {}, clear=True)
    def test_export_variables_with_no_keys(self):
        """Test exporting variables when no keys are present."""
        env_manager = EnvManager()
        
        # Mock settings with no keys
        env_manager.settings.openai_api_key = None
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Export variables
        env_manager.export_variables()
        
        # Verify no environment variables are set
        assert os.environ.get("OPENAI_API_KEY") is None
        assert os.environ.get("ANTHROPIC_API_KEY") is None
        assert os.environ.get("GEMINI_API_KEY") is None

    @patch.dict(os.environ, {"OPENAI_API_KEY": "existing-key"}, clear=False)
    def test_export_variables_overwrites_existing(self):
        """Test that export_variables overwrites existing environment variables."""
        env_manager = EnvManager()
        
        # Verify existing key
        assert os.environ.get("OPENAI_API_KEY") == "existing-key"
        
        # Mock settings with different OpenAI key
        env_manager.settings.openai_api_key = SecretStr("sk-new-key")
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Export variables
        env_manager.export_variables()
        
        # Verify key was overwritten
        assert os.environ.get("OPENAI_API_KEY") == "sk-new-key"

    def test_export_variables_secret_str_handling(self):
        """Test that SecretStr values are properly handled during export."""
        env_manager = EnvManager()
        
        # Mock settings with SecretStr
        secret_key = SecretStr("sk-secret-value")
        env_manager.settings.openai_api_key = secret_key
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Export variables
        with patch.dict(os.environ, {}, clear=True):
            env_manager.export_variables()
            
            # Verify the secret value was extracted and exported
            assert os.environ.get("OPENAI_API_KEY") == "sk-secret-value"
            
            # Verify the SecretStr object is still intact
            assert env_manager.settings.openai_api_key.get_secret_value() == "sk-secret-value"

    def test_get_settings(self):
        """Test get_settings method."""
        env_manager = EnvManager()
        
        # Should return the settings instance
        settings = env_manager.get_settings()
        assert settings is env_manager.settings
        assert isinstance(settings, AIProviderSettings)

    def test_env_manager_with_real_settings(self):
        """Test EnvManager with real AIProviderSettings (integration test)."""
        # Create real settings with actual values
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'sk-real-openai-key',
            'ANTHROPIC_API_KEY': 'sk-real-anthropic-key',
            'GEMINI_API_KEY': 'real-gemini-key'
        }):
            settings = AIProviderSettings()
            
            env_manager = EnvManager()
            env_manager.settings = settings
            
            # Test validation
            assert env_manager.validate_provider_keys("openai") is True
            assert env_manager.validate_provider_keys("anthropic") is True
            assert env_manager.validate_provider_keys("google") is True
            assert env_manager.validate_provider_keys("unsupported") is False
            
            # Test export
            with patch.dict(os.environ, {}, clear=True):
                env_manager.export_variables()
                assert os.environ.get("OPENAI_API_KEY") == "sk-real-openai-key"
                assert os.environ.get("ANTHROPIC_API_KEY") == "sk-real-anthropic-key"
                assert os.environ.get("GEMINI_API_KEY") == "real-gemini-key"

    def test_env_manager_error_handling(self):
        """Test EnvManager error handling scenarios."""
        env_manager = EnvManager()
        
        # Test with None settings (should handle gracefully)
        env_manager.settings = None
        
        # Should not crash, but may return False or raise
        try:
            result = env_manager.validate_provider_keys("openai")
            # If it doesn't crash, that's good enough
            assert isinstance(result, bool)
        except AttributeError:
            # Expected when settings is None
            pass

    def test_env_manager_multiple_exports(self):
        """Test multiple calls to export_variables."""
        env_manager = EnvManager()
        
        # Mock settings
        env_manager.settings.openai_api_key = SecretStr("sk-test-key")
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Export multiple times
        with patch.dict(os.environ, {}, clear=True):
            env_manager.export_variables()
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"
            
            env_manager.export_variables()
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"
            
            env_manager.export_variables()
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"

    def test_env_manager_provider_name_edge_cases(self):
        """Test provider name validation with edge cases."""
        env_manager = EnvManager()
        
        # Mock settings with OpenAI key
        env_manager.settings.openai_api_key = SecretStr("test-key")
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Test edge cases
        edge_cases = [
            "",  # Empty string
            " ",  # Space
            "open ai",  # With space
            "openai_",  # With underscore
            "_openai",  # Leading underscore
            "open-ai",  # With hyphen
            "123openai",  # Leading numbers
            "openai123",  # Trailing numbers
        ]
        
        for provider in edge_cases:
            result = env_manager.validate_provider_keys(provider)
            # All edge cases should return False
            assert result is False, f"Unexpectedly True for edge case: '{provider}'"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "old-value"}, clear=False)
    def test_export_variables_idempotency(self):
        """Test that export_variables is idempotent."""
        env_manager = EnvManager()
        
        # Mock settings
        env_manager.settings.openai_api_key = SecretStr("sk-new-value")
        env_manager.settings.anthropic_api_key = None
        env_manager.settings.gemini_api_key = None
        
        # Export multiple times and verify consistency
        for _ in range(5):
            env_manager.export_variables()
            assert os.environ.get("OPENAI_API_KEY") == "sk-new-value"
