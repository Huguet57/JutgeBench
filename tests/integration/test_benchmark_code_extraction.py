"""
Integration tests for benchmark code extraction functionality
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from jutge_solver.benchmark import AIModelAdapter
from jutge_solver.benchmark_config import AIModelConfig


class TestBenchmarkCodeExtraction:
    """Test that benchmark properly extracts code from AI model responses"""
    
    def create_mock_response(self, content: str, provider: str):
        """Create a mock response object based on provider"""
        if provider in {"openai", "openrouter"}:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = content
            mock_response.usage = Mock()
            mock_response.usage.total_tokens = 100
            return mock_response
        elif provider == "anthropic":
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = content
            mock_response.usage = Mock()
            mock_response.usage.input_tokens = 50
            mock_response.usage.output_tokens = 50
            return mock_response
        elif provider == "google":
            mock_response = Mock()
            mock_response.text = content
            return mock_response
    
    @pytest.mark.parametrize("provider", ["openai", "anthropic", "google", "openrouter"])
    def test_markdown_extraction(self, provider):
        """Test extraction from markdown-wrapped responses"""
        # Create config
        config = AIModelConfig(
            name=f"test-{provider}",
            provider=provider,
            model_id="test-model",
            api_key="test-key"
        )
        
        # Create adapter with mocked client
        with patch.object(AIModelAdapter, '_create_client', return_value=Mock()):
            adapter = AIModelAdapter(config)
        
        # Test responses that caused issues in benchmark
        test_cases = [
            {
                "input": '```python\nprint("Hello world!")\n```',
                "expected": 'print("Hello world!")',
                "description": "Markdown with actual newlines (Gemini/DeepSeek issue)"
            },
            {
                "input": '```python\\nprint("Hello world!")\\n```',
                "expected": 'print("Hello world!")',
                "description": "Markdown with escaped newlines"
            },
            {
                "input": 'print("Hello world!")',
                "expected": 'print("Hello world!")',
                "description": "Clean code without markdown"
            }
        ]
        
        for case in test_cases:
            # Mock the API response
            mock_response = self.create_mock_response(case["input"], provider)
            
            if provider in {"openai", "openrouter"}:
                adapter.client.chat.completions.create.return_value = mock_response
            elif provider == "anthropic":
                adapter.client.messages.create.return_value = mock_response
            elif provider == "google":
                adapter.client.generate_content.return_value = mock_response
            
            # Generate solution
            problem_data = {
                "title": "Test Problem",
                "statement": "Print hello world",
                "input": "",
                "output": "Hello world!",
                "samples": []
            }
            
            solution, tokens, time = adapter.generate_solution(problem_data, "Python3")
            
            # Verify the code was properly extracted
            assert solution == case["expected"], f"Failed for {provider} with {case['description']}"
    
    def test_real_world_responses(self):
        """Test with actual response patterns from different models"""
        # Simulate exact responses from the benchmark results
        model_responses = {
            "Gemini-2.5-Pro": '```python\nprint("Hello world!")\n```',
            "DeepSeek": '```python\nprint("Hello world!")\n```',
            "Gemini-2.5-Flash": 'print("Hello world!")',
            "Claude-Sonnet": 'print("Hello world!")'
        }
        
        for model_name, response in model_responses.items():
            # Use openai provider for testing
            config = AIModelConfig(
                name=model_name,
                provider="openai",
                model_id="test-model",
                api_key="test-key"
            )
            
            with patch.object(AIModelAdapter, '_create_client', return_value=Mock()):
                adapter = AIModelAdapter(config)
            
            # Mock response
            mock_response = self.create_mock_response(response, "openai")
            adapter.client.chat.completions.create.return_value = mock_response
            
            # Generate solution
            problem_data = {"title": "Test", "statement": "Test", "samples": []}
            solution, _, _ = adapter.generate_solution(problem_data, "Python3")
            
            # All should extract to clean code
            assert solution == 'print("Hello world!")', f"Failed for {model_name}"


if __name__ == "__main__":
    # Run tests without pytest
    test = TestBenchmarkCodeExtraction()
    
    print("Testing benchmark code extraction...\n")
    
    # Test each provider
    for provider in ["openai", "anthropic", "google", "openrouter"]:
        try:
            test.test_markdown_extraction(provider)
            print(f"✓ {provider} extraction tests passed")
        except AssertionError as e:
            print(f"✗ {provider} extraction tests failed: {e}")
        except Exception as e:
            print(f"✗ {provider} tests error: {e}")
    
    # Test real-world responses
    try:
        test.test_real_world_responses()
        print("✓ Real-world response tests passed")
    except AssertionError as e:
        print(f"✗ Real-world response tests failed: {e}")
    except Exception as e:
        print(f"✗ Real-world tests error: {e}")
    
    print("\nAll tests completed!") 