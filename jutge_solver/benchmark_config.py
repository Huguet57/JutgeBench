"""
Configuration for AI model benchmarking
"""

import os
import yaml
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class AIModelConfig(BaseModel):
    """Configuration for a single AI model"""
    name: str
    provider: str  # "openai", "anthropic", "google", etc.
    model_id: str
    api_key: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30
    enabled: bool = True


class BenchmarkConfig(BaseModel):
    """Configuration for AI model benchmarks"""
    models: List[AIModelConfig] = Field(default_factory=list)
    problem_sets: Dict[str, List[str]] = Field(default_factory=dict)
    max_attempts_per_problem: int = 1
    timeout_per_problem: int = 300  # 5 minutes
    retry_on_failure: bool = True
    max_retries: int = 2
    save_detailed_logs: bool = True
    output_format: str = "json"  # "json", "csv", "html"
    
    @classmethod
    def create_default(cls) -> "BenchmarkConfig":
        """Create default benchmark configuration with common AI models"""
        default_models = [
            AIModelConfig(
                name="GPT-4o-mini",
                provider="openai",
                model_id="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.1
            ),
            AIModelConfig(
                name="GPT-4o",
                provider="openai", 
                model_id="gpt-4o",
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.1
            ),
            # Placeholder for other models - can be extended
            AIModelConfig(
                name="Claude-3.5-Sonnet",
                provider="anthropic",
                model_id="claude-3-5-sonnet-20241022",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.1,
                enabled=False  # Disabled by default until API key is provided
            ),
        ]
        
        default_problem_sets = {
            "hello_world": ["P68688_en"],
            "basic_algorithms": [
                "P68688_en",  # Hello world
                "P34279_en",  # Add two numbers
                "P96767_en",  # Powers
            ],
            "medium_problems": [
                "P68688_en",
                "P34279_en", 
                "P96767_en",
                "P13623_en",  # Rectangles
                "P29448_en",  # Caesar cipher
            ]
        }
        
        return cls(
            models=default_models,
            problem_sets=default_problem_sets
        )
    
    @classmethod
    def load_from_file(cls, config_path: str) -> "BenchmarkConfig":
        """Load benchmark configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            config = cls(**data)
            
            # Load API keys from environment variables if not set in config
            for model in config.models:
                if model.api_key is None:
                    if model.provider == "openai":
                        model.api_key = os.getenv("OPENAI_API_KEY")
                    elif model.provider == "anthropic":
                        model.api_key = os.getenv("ANTHROPIC_API_KEY")
                    elif model.provider == "google":
                        model.api_key = os.getenv("GOOGLE_API_KEY")
            
            return config
        except FileNotFoundError:
            print(f"Benchmark config file {config_path} not found, creating default")
            config = cls.create_default()
            config.save_to_file(config_path)
            return config
        except Exception as e:
            print(f"Error loading benchmark config: {e}, using default")
            return cls.create_default()
    
    def save_to_file(self, config_path: str) -> None:
        """Save benchmark configuration to YAML file"""
        with open(config_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
    
    def get_enabled_models(self) -> List[AIModelConfig]:
        """Get list of enabled AI models"""
        return [model for model in self.models if model.enabled and model.api_key]
    
    def validate(self) -> bool:
        """Validate benchmark configuration"""
        enabled_models = self.get_enabled_models()
        if not enabled_models:
            print("Error: No enabled AI models with API keys found")
            return False
        
        if not self.problem_sets:
            print("Error: No problem sets defined")
            return False
            
        return True