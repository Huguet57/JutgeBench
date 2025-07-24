"""
Solution generation module using OpenAI API
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


class SolutionGenerator:
    """Generates programming solutions using OpenAI API"""
    
    def __init__(self, openai_client, openai_config):
        self.client = openai_client
        self.config = openai_config
        
        # Language-specific settings
        self.language_settings = {
            "Python3": {
                "extension": "py",
                "template": "python",
                "main_wrapper": False
            },
            "G++17": {
                "extension": "cpp",
                "template": "cpp",
                "main_wrapper": True
            },
            "JDK": {
                "extension": "java",
                "template": "java",
                "main_wrapper": True
            }
        }
    
    def generate_solution(self, problem_info: Dict[str, Any], compiler_id: str, attempt: int = 1) -> Dict[str, Any]:
        """
        Generate a solution for the given problem
        
        Args:
            problem_info: Problem information from problem analyzer
            compiler_id: Target compiler/language
            attempt: Current attempt number (for retry logic)
            
        Returns:
            Dict containing generation results
        """
        try:
            console.print(f"[blue]  Attempt {attempt}: Generating solution for {compiler_id}...[/blue]")
            
            # Get problem statement
            problem_statement = self._get_problem_statement(problem_info)
            
            # Generate prompt based on language and problem
            prompt = self._create_prompt(problem_statement, compiler_id)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(compiler_id)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            # Extract code from response
            raw_response = response.choices[0].message.content
            code = self._extract_code(raw_response, compiler_id)
            
            if not code:
                raise ValueError("No code found in OpenAI response")
            
            result = {
                "success": True,
                "code": code,
                "raw_response": raw_response,
                "compiler_id": compiler_id,
                "attempt": attempt,
                "model": self.config.model,
                "timestamp": datetime.now().isoformat(),
                "token_usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            console.print(f"[green]  ✓ Solution generated ({response.usage.total_tokens} tokens)[/green]")
            return result
            
        except Exception as e:
            console.print(f"[red]  ✗ Generation failed: {e}[/red]")
            logger.error(f"Solution generation failed (attempt {attempt}): {e}")
            
            return {
                "success": False,
                "error": str(e),
                "compiler_id": compiler_id,
                "attempt": attempt,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_problem_statement(self, problem_info: Dict[str, Any]) -> str:
        """Extract the problem statement from the problem info"""
        try:
            title = problem_info.get("title", "Unknown Problem")
            statement = problem_info.get("statement", "")
            
            # If we have the full statement, use it
            if statement:
                return f"Title: {title}\\n\\n{statement}"
            else:
                return f"Title: {title}\\n\\nProblem: Please solve this programming problem."
        except:
            return "Programming problem to solve"
    
    def _get_system_prompt(self, compiler_id: str) -> str:
        """Get the system prompt based on the target language"""
        
        base_prompt = """You are an expert competitive programming assistant. Your task is to solve programming problems with clean, efficient, and correct code.

IMPORTANT REQUIREMENTS:
- Write ONLY the solution code, no explanations or comments
- DO NOT use markdown code blocks (```python, ```cpp, ```java, etc.)
- Output the raw code directly without any formatting or backticks
- Ensure the code handles all input/output exactly as specified
- Use efficient algorithms appropriate for competitive programming
- Make sure to handle edge cases and constraints"""

        if compiler_id == "Python3":
            return base_prompt + """

PYTHON SPECIFIC:
- Use Python 3 syntax
- Read input using input() function
- Print output using print() function
- Be careful with integer division (use // for floor division)
"""
        elif compiler_id in ["G++17", "G++"]:
            return base_prompt + """

C++ SPECIFIC:
- Use standard competitive programming includes: #include <iostream> and others as needed
- Include proper main() function
- Use std::'s cin/cout for input/output
"""

        elif compiler_id == "JDK":
            return base_prompt + """

JAVA SPECIFIC:
- Create a public class named 'Main'
- Include proper main method: public static void main(String[] args)
- Use Scanner for input or BufferedReader for faster input
- System.out.println() for output
- Be careful with data types and overflow"""

        else:
            return base_prompt
    
    def _create_prompt(self, problem_statement: str, compiler_id: str) -> str:
        """Create a detailed prompt for the specific problem and language"""
        
        language_name = self._get_language_name(compiler_id)
        
        prompt = f"""Solve this competitive programming problem in {language_name}:

{problem_statement}

Requirements:
- Provide only the complete, runnable code
- DO NOT wrap the code in markdown blocks (```python, ```cpp, ```java, etc.)
- Output the raw code directly without backticks or formatting
- No explanations, comments, or markdown formatting
- Handle input/output exactly as specified in the problem
- Ensure the solution is efficient and handles edge cases
- Code should be ready to submit to an online judge

{language_name} solution:"""

        return prompt
    
    def _get_language_name(self, compiler_id: str) -> str:
        """Get human-readable language name"""
        mapping = {
            "Python3": "Python",
            "G++17": "C++",
            "G++": "C++",
            "JDK": "Java"
        }
        return mapping.get(compiler_id, compiler_id)
    
    def _extract_code(self, response: str, compiler_id: str) -> Optional[str]:
        """Extract code from OpenAI response"""
        
        # Try to find code blocks first
        code_block_patterns = [
            r'```(?:python|py)\\n(.*?)```',
            r'```(?:cpp|c\\+\\+)\\n(.*?)```',
            r'```(?:java)\\n(.*?)```',
            r'```\\n(.*?)```',
            r'```(.*?)```'
        ]
        
        for pattern in code_block_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # If no code blocks found, try to extract based on language patterns
        if compiler_id == "Python3":
            return self._extract_python_code(response)
        elif compiler_id in ["G++17", "G++"]:
            return self._extract_cpp_code(response)
        elif compiler_id == "JDK":
            return self._extract_java_code(response)
        
        # Last resort: return the whole response cleaned up
        return self._clean_response(response)
    
    def _extract_python_code(self, response: str) -> Optional[str]:
        """Extract Python code from response"""
        lines = response.split('\\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Skip explanatory text at the beginning
            if not in_code and (line.strip().startswith('#') or 
                               line.strip().startswith('import ') or
                               line.strip().startswith('def ') or
                               line.strip().startswith('print(') or
                               line.strip().startswith('input(') or
                               'input()' in line or 'print(' in line):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        return '\\n'.join(code_lines).strip() if code_lines else None
    
    def _extract_cpp_code(self, response: str) -> Optional[str]:
        """Extract C++ code from response"""
        lines = response.split('\\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if not in_code and (line.strip().startswith('#include') or
                               line.strip().startswith('using namespace') or
                               'int main(' in line):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        return '\\n'.join(code_lines).strip() if code_lines else None
    
    def _extract_java_code(self, response: str) -> Optional[str]:
        """Extract Java code from response"""
        lines = response.split('\\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if not in_code and ('public class' in line or 
                               'class Main' in line or
                               'import java' in line):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        return '\\n'.join(code_lines).strip() if code_lines else None
    
    def _clean_response(self, response: str) -> str:
        """Clean up the response as a last resort"""
        # Remove common explanation phrases
        clean_response = response
        
        # Remove explanation patterns
        patterns_to_remove = [
            r'Here\\s+is\\s+the\\s+solution.*?:\\s*',
            r'Here\\s+is\\s+my\\s+solution.*?:\\s*',
            r'Solution:\\s*',
            r'Answer:\\s*',
        ]
        
        for pattern in patterns_to_remove:
            clean_response = re.sub(pattern, '', clean_response, flags=re.IGNORECASE)
        
        return clean_response.strip()
