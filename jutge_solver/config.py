"""
Configuration management for Jutge Problem Solver
"""

import os
import yaml
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from rich.console import Console

console = Console()


class OpenAIConfig(BaseModel):
    """OpenAI API configuration"""
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30
    base_url: Optional[str] = None


class JutgeConfig(BaseModel):
    """Jutge API configuration"""
    email: Optional[str] = None
    password: Optional[str] = None
    default_compiler: str = "Python3"
    submission_timeout: int = 60
    max_retries: int = 3


class SolverConfig(BaseModel):
    """General solver configuration"""
    preferred_languages: list[str] = ["Python3", "G++17", "JDK"]
    max_generation_attempts: int = 3
    enable_local_testing: bool = True
    log_level: str = "INFO"
    accepted_verdicts: list[str] = ["AC", "PE"]  # Verdicts considered as correct answers


class Config(BaseModel):
    """Main configuration class"""
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    jutge: JutgeConfig = Field(default_factory=JutgeConfig)
    solver: SolverConfig = Field(default_factory=SolverConfig)

    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        config = cls()
        
        # Load from environment variables
        if api_key := os.getenv("OPENAI_API_KEY"):
            config.openai.api_key = api_key
        elif api_key := os.getenv("OPENROUTER_API_KEY"):
            config.openai.api_key = api_key
            config.openai.base_url = "https://openrouter.ai/api/v1"
        if model := os.getenv("OPENAI_MODEL"):
            config.openai.model = model
        if email := os.getenv("JUTGE_EMAIL"):
            config.jutge.email = email
        if password := os.getenv("JUTGE_PASSWORD"):
            config.jutge.password = password
            
        return config

    @classmethod
    def load_from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            return cls(**data)
        except FileNotFoundError:
            console.print(f"[yellow]Config file {config_path} not found, using defaults[/yellow]")
            return cls()
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return cls()

    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file"""
        with open(config_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    def load_env_file(self, env_path: str = ".env") -> None:
        """Load environment variables from .env file"""
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

    def validate(self) -> bool:
        """Validate that required configuration is present"""
        errors = []
        
        if not self.openai.api_key:
            errors.append("OpenAI API key is required")
        if not self.jutge.email:
            errors.append("Jutge email is required")
        if not self.jutge.password:
            errors.append("Jutge password is required")
            
        if errors:
            console.print("[red]Configuration errors:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            return False
            
        return True