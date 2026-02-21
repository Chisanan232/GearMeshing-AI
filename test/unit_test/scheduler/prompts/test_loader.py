"""Unit tests for prompt template loader."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from gearmeshing_ai.scheduler.prompts.loader import PromptTemplate, PromptTemplateLoader


class TestPromptTemplate:
    """Test PromptTemplate dataclass."""

    def test_prompt_template_initialization(self):
        """Test PromptTemplate initialization with all fields."""
        template = PromptTemplate(
            template_id="test_template",
            name="Test Template",
            description="A test template",
            version="1.0",
            template="Hello {name}, your status is {status}",
            variables_schema={"name": "string", "status": "string"},
            agent_role="analyzer",
            timeout_seconds=300,
            approval_timeout_seconds=1800,
            tags=["test", "example"],
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert template.template_id == "test_template"
        assert template.name == "Test Template"
        assert template.version == "1.0"
        assert template.agent_role == "analyzer"
        assert template.timeout_seconds == 300
        assert len(template.tags) == 2

    def test_prompt_template_default_values(self):
        """Test PromptTemplate with default values."""
        template = PromptTemplate(
            template_id="minimal_template",
            name="Minimal",
            description="Minimal template",
            version="1.0",
            template="Content",
            variables_schema={}
        )
        
        assert template.timeout_seconds == 600
        assert template.approval_timeout_seconds == 3600
        assert template.author == "System"
        assert template.tags == []

    def test_prompt_template_tags_initialization(self):
        """Test that tags are initialized as empty list when None."""
        template = PromptTemplate(
            template_id="no_tags",
            name="No Tags",
            description="Template without tags",
            version="1.0",
            template="Content",
            variables_schema={},
            tags=None
        )
        
        assert template.tags == []


class TestPromptTemplateLoader:
    """Test PromptTemplateLoader functionality."""

    def test_loader_initialization(self):
        """Test loader initialization."""
        loader = PromptTemplateLoader()
        assert loader is not None

    def test_load_from_yaml_string_single_template(self):
        """Test loading a single template from YAML string."""
        yaml_content = """
prompt_templates:
  - template_id: greeting
    name: Greeting Template
    description: A simple greeting template
    version: 1.0
    template: "Hello {name}!"
    variables_schema:
      name: string
"""
        loader = PromptTemplateLoader()
        templates = loader.load_from_yaml_string(yaml_content)
        
        assert len(templates) == 1
        assert templates[0].template_id == "greeting"
        assert templates[0].name == "Greeting Template"
        assert "name" in templates[0].variables_schema

    def test_load_from_yaml_string_multiple_templates(self):
        """Test loading multiple templates from YAML string."""
        yaml_content = """
prompt_templates:
  - template_id: greeting
    name: Greeting
    description: Greeting template
    version: 1.0
    template: "Hello {name}!"
    variables_schema:
      name: string
  - template_id: farewell
    name: Farewell
    description: Farewell template
    version: 1.0
    template: "Goodbye {name}!"
    variables_schema:
      name: string
"""
        loader = PromptTemplateLoader()
        templates = loader.load_from_yaml_string(yaml_content)
        
        assert len(templates) == 2
        assert templates[0].template_id == "greeting"
        assert templates[1].template_id == "farewell"

    def test_load_from_yaml_string_with_agent_role(self):
        """Test loading template with agent role."""
        yaml_content = """
prompt_templates:
  - template_id: analyzer_template
    name: Analyzer Template
    description: Template for analyzer agent
    version: 1.0
    template: "Analyze {data}"
    variables_schema:
      data: string
    agent_role: analyzer
"""
        loader = PromptTemplateLoader()
        templates = loader.load_from_yaml_string(yaml_content)
        
        assert templates[0].agent_role == "analyzer"

    def test_load_from_yaml_string_with_custom_timeout(self):
        """Test loading template with custom timeout."""
        yaml_content = """
prompt_templates:
  - template_id: slow_task
    name: Slow Task
    description: Template for slow tasks
    version: 1.0
    template: "Process {data}"
    variables_schema:
      data: string
    timeout_seconds: 1200
    approval_timeout_seconds: 7200
"""
        loader = PromptTemplateLoader()
        templates = loader.load_from_yaml_string(yaml_content)
        
        assert templates[0].timeout_seconds == 1200
        assert templates[0].approval_timeout_seconds == 7200

    def test_load_from_yaml_string_with_tags(self):
        """Test loading template with tags."""
        yaml_content = """
prompt_templates:
  - template_id: tagged_template
    name: Tagged Template
    description: Template with tags
    version: 1.0
    template: "Content"
    variables_schema: {}
    tags:
      - urgent
      - critical
      - monitoring
"""
        loader = PromptTemplateLoader()
        templates = loader.load_from_yaml_string(yaml_content)
        
        assert len(templates[0].tags) == 3
        assert "urgent" in templates[0].tags
        assert "critical" in templates[0].tags

    def test_load_from_yaml_string_with_timestamps(self):
        """Test loading template with timestamps."""
        yaml_content = """
prompt_templates:
  - template_id: timestamped
    name: Timestamped Template
    description: Template with timestamps
    version: "1.0"
    template: "Content"
    variables_schema: {}
    created_at: "2024-01-15T10:30:00"
    updated_at: "2024-01-20T14:45:00"
"""
        loader = PromptTemplateLoader()
        templates = loader.load_from_yaml_string(yaml_content)
        
        assert templates[0].created_at is not None
        assert templates[0].updated_at is not None

    def test_load_from_yaml_string_missing_required_field(self):
        """Test error handling for missing required fields."""
        yaml_content = """
prompt_templates:
  - template_id: incomplete
    name: Incomplete Template
    version: 1.0
    template: "Content"
    variables_schema: {}
"""
        loader = PromptTemplateLoader()
        
        with pytest.raises(ValueError, match="Missing required field"):
            loader.load_from_yaml_string(yaml_content)

    def test_load_from_yaml_string_invalid_yaml(self):
        """Test error handling for invalid YAML."""
        yaml_content = """
prompt_templates:
  - template_id: invalid
    name: Invalid
    [invalid yaml content
"""
        loader = PromptTemplateLoader()
        
        with pytest.raises(ValueError, match="Invalid YAML format"):
            loader.load_from_yaml_string(yaml_content)

    def test_load_from_yaml_string_missing_prompt_templates_key(self):
        """Test error handling when prompt_templates key is missing."""
        yaml_content = """
templates:
  - template_id: test
    name: Test
"""
        loader = PromptTemplateLoader()
        
        with pytest.raises(ValueError, match="prompt_templates"):
            loader.load_from_yaml_string(yaml_content)

    def test_load_from_yaml_file(self):
        """Test loading templates from a YAML file."""
        yaml_content = """
prompt_templates:
  - template_id: file_template
    name: File Template
    description: Template from file
    version: 1.0
    template: "Content from file"
    variables_schema: {}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            loader = PromptTemplateLoader()
            templates = loader.load_from_yaml(temp_file)
            
            assert len(templates) == 1
            assert templates[0].template_id == "file_template"
        finally:
            Path(temp_file).unlink()

    def test_load_from_yaml_file_not_found(self):
        """Test error handling for non-existent file."""
        loader = PromptTemplateLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load_from_yaml("/non/existent/file.yaml")

    def test_validate_template_file_valid(self):
        """Test validating a valid template file."""
        yaml_content = """
prompt_templates:
  - template_id: valid_template
    name: Valid Template
    description: A valid template
    version: "1.0"
    template: "Hello {name}"
    variables_schema:
      name: string
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            loader = PromptTemplateLoader()
            errors = loader.validate_template_file(temp_file)
            
            assert len(errors) == 0
        finally:
            Path(temp_file).unlink()

    def test_validate_template_file_invalid_variable_type(self):
        """Test validation detects invalid variable types."""
        yaml_content = """
prompt_templates:
  - template_id: invalid_var_type
    name: Invalid Var Type
    description: Template with invalid variable type
    version: 1.0
    template: "Content {var}"
    variables_schema:
      var: invalid_type
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            loader = PromptTemplateLoader()
            errors = loader.validate_template_file(temp_file)
            
            assert len(errors) > 0
            assert any("Invalid variable type" in error for error in errors)
        finally:
            Path(temp_file).unlink()

    def test_validate_template_file_undefined_variables(self):
        """Test validation detects variables in template not in schema."""
        yaml_content = """
prompt_templates:
  - template_id: undefined_vars
    name: Undefined Variables
    description: Template with undefined variables
    version: 1.0
    template: "Hello {name}, your age is {age}"
    variables_schema:
      name: string
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            loader = PromptTemplateLoader()
            errors = loader.validate_template_file(temp_file)
            
            assert len(errors) > 0
            assert any("not defined in schema" in error for error in errors)
        finally:
            Path(temp_file).unlink()

    def test_validate_template_file_unused_variables(self):
        """Test validation detects variables in schema not used in template."""
        yaml_content = """
prompt_templates:
  - template_id: unused_vars
    name: Unused Variables
    description: Template with unused variables
    version: 1.0
    template: "Hello {name}"
    variables_schema:
      name: string
      age: number
      email: string
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name
        
        try:
            loader = PromptTemplateLoader()
            errors = loader.validate_template_file(temp_file)
            
            assert len(errors) > 0
            assert any("not used in template" in error for error in errors)
        finally:
            Path(temp_file).unlink()

    def test_export_to_yaml(self):
        """Test exporting templates to YAML file."""
        template = PromptTemplate(
            template_id="export_test",
            name="Export Test",
            description="Template for export test",
            version="1.0",
            template="Content {var}",
            variables_schema={"var": "string"},
            agent_role="executor",
            tags=["test"]
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "exported.yaml"
            
            loader = PromptTemplateLoader()
            loader.export_to_yaml([template], str(output_file))
            
            assert output_file.exists()
            
            # Verify exported content
            exported_templates = loader.load_from_yaml(str(output_file))
            assert len(exported_templates) == 1
            assert exported_templates[0].template_id == "export_test"
            assert exported_templates[0].agent_role == "executor"

    def test_extract_template_variables(self):
        """Test extracting variables from template content."""
        loader = PromptTemplateLoader()
        
        template_content = "Hello {name}, your status is {status} and priority is {priority}"
        variables = loader._extract_template_variables(template_content)
        
        assert len(variables) == 3
        assert "name" in variables
        assert "status" in variables
        assert "priority" in variables

    def test_parse_datetime_iso_format(self):
        """Test parsing ISO format datetime."""
        loader = PromptTemplateLoader()
        
        dt = loader._parse_datetime("2024-01-15T10:30:00")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_datetime_date_only(self):
        """Test parsing date-only format."""
        loader = PromptTemplateLoader()
        
        dt = loader._parse_datetime("2024-01-15")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_datetime_invalid_format(self):
        """Test error handling for invalid datetime format."""
        loader = PromptTemplateLoader()
        
        with pytest.raises(ValueError, match="Invalid datetime format"):
            loader._parse_datetime("invalid-date")
