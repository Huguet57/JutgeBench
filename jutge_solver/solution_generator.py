"""
Solution generation module using OpenAI API
"""

import re
import base64
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


class SolutionGenerator:
    """Generates programming solutions using OpenAI API"""
    
    def __init__(self, openai_client, openai_config, raw_logging_config=None):
        self.client = openai_client
        self.config = openai_config
        self.raw_logging_config = raw_logging_config or {}
        
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
            
            # Save raw response for debugging if enabled
            extraction_failed = False
            try:
                code = self._extract_code(raw_response, compiler_id)
                if not code:
                    extraction_failed = True
                    raise ValueError("No code found in OpenAI response")
            except Exception as e:
                extraction_failed = True
                self._save_raw_response_on_failure(raw_response, problem_info, compiler_id, attempt, "extraction_failed", str(e))
                raise
            
            # Save raw response if logging is enabled (success case)
            self._save_raw_response(raw_response, problem_info, compiler_id, attempt, "success")
            
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
        """Extract comprehensive problem information including statement and test cases"""
        try:
            title = problem_info.get("title", "Unknown Problem")
            statement = problem_info.get("statement", "")
            author = problem_info.get("author", "Unknown Author")
            
            # Build the problem description
            result = f"Title: {title}\\nAuthor: {author}\\n\\n"
            
            # Add the statement
            if statement:
                result += f"Problem Statement:\\n{statement}\\n\\n"
            
            # Add sample test cases if available
            sample_testcases = problem_info.get("sample_testcases", [])
            if sample_testcases:
                result += "Sample Test Cases:\\n"
                for i, testcase in enumerate(sample_testcases, 1):
                    try:
                        input_data = base64.b64decode(testcase.get("input_b64", "")).decode('utf-8')
                        expected_output = base64.b64decode(testcase.get("correct_b64", "")).decode('utf-8')
                        result += f"Test Case {i}:\\n"
                        result += f"Input: {input_data.strip()}\\n"
                        result += f"Expected Output: {expected_output.strip()}\\n\\n"
                    except:
                        continue
            
            # Add public test cases if available
            public_testcases = problem_info.get("public_testcases", [])
            if public_testcases and len(public_testcases) > len(sample_testcases):
                result += "Additional Public Test Cases:\\n"
                for i, testcase in enumerate(public_testcases[len(sample_testcases):], len(sample_testcases) + 1):
                    try:
                        input_data = base64.b64decode(testcase.get("input_b64", "")).decode('utf-8')
                        expected_output = base64.b64decode(testcase.get("correct_b64", "")).decode('utf-8')
                        result += f"Test Case {i}:\\n"
                        result += f"Input: {input_data.strip()}\\n"
                        result += f"Expected Output: {expected_output.strip()}\\n\\n"
                    except:
                        continue
            
            return result
            
        except:
            title = "Unknown Problem"
            if problem_info and isinstance(problem_info, dict):
                title = problem_info.get("title", "Unknown Problem")
            return f"Title: {title}\\n\\nProblem: Please solve this programming problem."
    
    def _get_system_prompt(self, compiler_id: str) -> str:
        """Get the system prompt based on the target language"""
        
        base_prompt = """You are an expert competitive programming assistant. Your task is to solve programming problems with clean, efficient, and correct code.

CRITICAL OUTPUT FORMAT REQUIREMENT:
- Your program's output must match the expected output format EXACTLY - character by character
- Pay extremely close attention to spacing, punctuation, commas, parentheses, and separators
- Even one wrong character will result in a WRONG verdict
- Study the "Expected Output" in test cases to see the precise format required

CODE REQUIREMENTS:
- Write ONLY the solution code, no explanations or comments
- Output the raw code directly - DO NOT wrap in markdown blocks (no ```)
- If you must use formatting, we will extract the code, but raw code is strongly preferred
- Ensure the code handles all input/output exactly as specified
- Use efficient algorithms appropriate for competitive programming
- Make sure to handle edge cases and constraints"""

        if compiler_id == "Python3":
            return base_prompt + """

PYTHON SPECIFIC:
- Use Python 3 syntax
- Read input using input() function
- Print output using print() function - match format exactly as shown in Expected Output
- Be careful with integer division (use // for floor division)
- Use print() with appropriate separators and end parameters to match exact format
- Example: print(a, b, c) for space-separated vs print(f"({a},{b},{c})") for parentheses format
- CRITICAL: Do NOT use 'return' statements outside of functions - this causes SyntaxError
- Write main execution code at the top level, not inside functions unless specifically needed
- If you must use functions, ensure all code paths are properly structured
"""
        elif compiler_id in ["G++17", "G++"]:
            return base_prompt + """

C++ SPECIFIC:
- Use standard competitive programming includes: #include <iostream> and others as needed
- Include proper main() function
- Use std::cin/cout for input/output - match format exactly as shown in Expected Output
- Pay attention to spacing and separators: cout << a << " " << b for space-separated vs cout << "(" << a << "," << b << "," << c << ")" for parentheses format
"""

        elif compiler_id == "JDK":
            return base_prompt + """

JAVA SPECIFIC:
- Create a public class named 'Main'
- Include proper main method: public static void main(String[] args)
- Use Scanner for input or BufferedReader for faster input
- System.out.println() or System.out.print() for output - match format exactly as shown in Expected Output
- Pay attention to spacing and separators: System.out.println(a + " " + b) for space-separated vs System.out.println("(" + a + "," + b + "," + c + ")") for parentheses format
- Be careful with data types and overflow"""

        else:
            return base_prompt
    
    def _create_prompt(self, problem_statement: str, compiler_id: str) -> str:
        """Create a detailed prompt for the specific problem and language"""
        
        language_name = self._get_language_name(compiler_id)
        
        prompt = f"""Solve this competitive programming problem in {language_name}:

{problem_statement}

CRITICAL OUTPUT FORMAT Requirements:
- Your output must match the expected output format EXACTLY - character by character
- Pay close attention to the "Expected Output" examples in the test cases above
- Match spacing, punctuation, parentheses, commas, and separators exactly as shown
- For example: if expected output shows "2 3 1", output exactly "2 3 1" (NOT "(2,3,1)" or "2,3,1")
- If expected output shows "(2,3,1)", output exactly "(2,3,1)" (NOT "2 3 1" or "2,3,1")
- Even a single character difference will cause your solution to be marked as WRONG
- The sample and public test cases show the EXACT format required

Code Requirements:
- Provide only the complete, runnable code
- Output raw code directly (no markdown formatting, no ```)
- No explanations, comments, or text before/after the code
- Handle input/output exactly as specified in the problem
- Ensure the solution is efficient and handles edge cases
- Code should be ready to submit to an online judge

Write your {language_name} solution below:"""

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
        
        # First, try the comprehensive cleaning approach
        cleaned_code = self._clean_code_blocks(response, compiler_id)
        if cleaned_code:
            return cleaned_code
        
        # If that fails, fall back to language-specific extraction
        if compiler_id == "Python3":
            extracted = self._extract_python_code(response)
            if extracted:
                return extracted
        elif compiler_id in ["G++17", "G++"]:
            extracted = self._extract_cpp_code(response)
            if extracted:
                return extracted
        elif compiler_id == "JDK":
            extracted = self._extract_java_code(response)
            if extracted:
                return extracted
        
        # Last resort: return the whole response cleaned up
        return self._clean_response(response)
    
    def _clean_code_blocks(self, response: str, compiler_id: str) -> Optional[str]:
        """
        Comprehensive cleaning of code blocks from AI responses
        Handles various markdown formats and edge cases
        """
        # Remove leading/trailing whitespace
        response = response.strip()
        
        # Common language identifiers in code blocks
        language_patterns = {
            "Python3": ["python", "py", "python3"],
            "G++17": ["cpp", "c\\+\\+", "C\\+\\+", "cc", "cxx"],
            "G++": ["cpp", "c\\+\\+", "C\\+\\+", "cc", "cxx"],
            "JDK": ["java", "Java"]
        }
        
        # First, handle responses with literal \n characters (escaped newlines)
        # This is common when the API returns JSON-encoded strings
        if '\\n' in response:
            # Try to extract code from various markdown block formats with escaped newlines
            # Pattern 1: Standard markdown with language identifier and escaped newlines
            for lang in language_patterns.get(compiler_id, []):
                pattern = rf'```{lang}\\n(.*?)```'
                matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
                if matches:
                    # Replace escaped newlines with actual newlines
                    code = matches[0].replace('\\n', '\n').strip()
                    return code
            
            # Pattern 2: Generic code blocks without language identifier (escaped newlines)
            pattern = r'```\\n(.*?)```'
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                code = matches[0].replace('\\n', '\n').strip()
                if self._is_valid_code(code, compiler_id):
                    return code
        
        # Now handle responses with actual newline characters
        # Pattern 1: Standard markdown with language identifier
        for lang in language_patterns.get(compiler_id, []):
            pattern = rf'```{lang}\s*\n(.*?)```'
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # Pattern 2: Generic code blocks without language identifier
        pattern = r'```\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            # If multiple blocks, try to find the main one
            for match in matches:
                if self._is_valid_code(match.strip(), compiler_id):
                    return match.strip()
            # If no valid code found, return the first block
            return matches[0].strip()
        
        # Pattern 3: Code blocks with just triple backticks (no newline)
        pattern = r'```(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            for match in matches:
                # Skip if it looks like a language identifier
                if len(match.strip().split('\n')[0].split()) == 1 and match.strip().split('\n')[0].lower() in ['python', 'cpp', 'java', 'c++']:
                    continue
                # Also check for escaped newlines
                cleaned_match = match.replace('\\n', '\n').strip()
                # Skip if the first line is just a language identifier
                first_line = cleaned_match.split('\n')[0].strip()
                if first_line.lower() in ['python', 'cpp', 'java', 'c++', 'py', 'python3']:
                    # Extract everything after the first line
                    remaining = '\n'.join(cleaned_match.split('\n')[1:]).strip()
                    if self._is_valid_code(remaining, compiler_id):
                        return remaining
                elif self._is_valid_code(cleaned_match, compiler_id):
                    return cleaned_match
        
        # Pattern 4: Indented code blocks (4 spaces or tab)
        lines = response.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            # Check if line is indented (code block)
            if line.startswith('    ') or line.startswith('\t'):
                in_code_block = True
                # Remove the indentation
                code_lines.append(line[4:] if line.startswith('    ') else line[1:])
            elif in_code_block and line.strip() == '':
                # Empty line in code block
                code_lines.append('')
            elif in_code_block and not line.startswith((' ', '\t')):
                # End of code block
                break
        
        if code_lines:
            code = '\n'.join(code_lines).strip()
            if self._is_valid_code(code, compiler_id):
                return code
        
        # Pattern 5: Look for code between explanation text
        # Remove common explanation phrases and try to extract code
        explanation_patterns = [
            r'^.*?[Hh]ere\'s?\s+(?:the|a|my)\s+(?:solution|code|implementation).*?:?\s*\n',
            r'^.*?[Ss]olution.*?:?\s*\n',
            r'^.*?[Cc]ode.*?:?\s*\n',
            r'^.*?[Ii]mplementation.*?:?\s*\n',
            r'\n\s*(?:Explanation|Note|Output|This).*$'
        ]
        
        cleaned_response = response
        for pattern in explanation_patterns:
            cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.MULTILINE | re.DOTALL)
        
        cleaned_response = cleaned_response.strip()
        if cleaned_response and self._is_valid_code(cleaned_response, compiler_id):
            return cleaned_response
        
        return None
    
    def _is_valid_code(self, code: str, compiler_id: str) -> bool:
        """
        Check if the extracted text is likely valid code for the given language
        """
        if not code or len(code.strip()) < 10:
            return False
        
        # Language-specific validation
        if compiler_id == "Python3":
            # Check for Python keywords or patterns
            python_indicators = ['def ', 'import ', 'print(', 'input(', 'for ', 'while ', 'if ', '=', ':']
            return any(indicator in code for indicator in python_indicators)
        
        elif compiler_id in ["G++17", "G++"]:
            # Check for C++ keywords or patterns
            cpp_indicators = ['#include', 'int main', 'using namespace', 'cin', 'cout', '{', '}', ';']
            return any(indicator in code for indicator in cpp_indicators)
        
        elif compiler_id == "JDK":
            # Check for Java keywords or patterns
            java_indicators = ['public class', 'class Main', 'public static void main', 'import java', 'System.out', '{', '}', ';']
            return any(indicator in code for indicator in java_indicators)
        
        # If language not recognized, accept if it looks like code
        return True
    
    def _extract_python_code(self, response: str) -> Optional[str]:
        """Extract Python code from response"""
        # First check if the entire response is already valid Python code
        if self._is_valid_code(response, "Python3"):
            return response
        
        # Otherwise, try to extract code by looking for code patterns
        lines = response.split('\n')
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
        
        return '\n'.join(code_lines).strip() if code_lines else None
    
    def _extract_cpp_code(self, response: str) -> Optional[str]:
        """Extract C++ code from response"""
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if not in_code and (line.strip().startswith('#include') or
                               line.strip().startswith('using namespace') or
                               'int main(' in line):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        return '\n'.join(code_lines).strip() if code_lines else None
    
    def _extract_java_code(self, response: str) -> Optional[str]:
        """Extract Java code from response"""
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if not in_code and ('public class' in line or 
                               'class Main' in line or
                               'import java' in line):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        return '\n'.join(code_lines).strip() if code_lines else None
    
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
    
    def _save_raw_response(self, raw_response: str, problem_info: Dict[str, Any], compiler_id: str, attempt: int, status: str = "success") -> None:
        """Save raw AI response to file for debugging purposes"""
        if not self.raw_logging_config.get('save_raw_responses', False):
            return
        
        # Only save on failure if that option is enabled
        if self.raw_logging_config.get('save_raw_on_failure_only', False) and status == "success":
            return
            
        try:
            # Create directory if it doesn't exist
            raw_responses_dir = self.raw_logging_config.get('raw_responses_dir', 'results/raw_responses')
            os.makedirs(raw_responses_dir, exist_ok=True)
            
            # Generate filename
            problem_id = problem_info.get('problem_id', 'unknown_problem')
            model_name = getattr(self.config, 'model', 'unknown_model').replace('/', '_').replace(':', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{model_name}_{problem_id}_attempt{attempt}_{status}_{timestamp}.txt"
            filepath = os.path.join(raw_responses_dir, filename)
            
            # Save response with metadata
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"RAW AI RESPONSE DEBUG LOG\n")
                f.write("="*80 + "\n")
                f.write(f"Model: {getattr(self.config, 'model', 'unknown')}\n")
                f.write(f"Problem ID: {problem_id}\n")
                f.write(f"Compiler: {compiler_id}\n")
                f.write(f"Attempt: {attempt}\n")
                f.write(f"Status: {status}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Response Length: {len(raw_response)} characters\n")
                f.write("="*80 + "\n\n")
                f.write("RAW RESPONSE:\n")
                f.write("-"*40 + "\n")
                f.write(raw_response)
                f.write("\n" + "-"*40 + "\n")
            
            logger.info(f"Raw response saved to: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save raw response: {e}")
    
    def _save_raw_response_on_failure(self, raw_response: str, problem_info: Dict[str, Any], compiler_id: str, attempt: int, failure_type: str, error_msg: str) -> None:
        """Save raw response when there's a failure (extraction, generation, etc.)"""
        if not self.raw_logging_config.get('save_raw_responses', False):
            return
            
        try:
            # Create directory if it doesn't exist
            raw_responses_dir = self.raw_logging_config.get('raw_responses_dir', 'results/raw_responses')
            os.makedirs(raw_responses_dir, exist_ok=True)
            
            # Generate filename
            problem_id = problem_info.get('problem_id', 'unknown_problem')
            model_name = getattr(self.config, 'model', 'unknown_model').replace('/', '_').replace(':', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{model_name}_{problem_id}_attempt{attempt}_FAILED_{failure_type}_{timestamp}.txt"
            filepath = os.path.join(raw_responses_dir, filename)
            
            # Save response with failure details
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"RAW AI RESPONSE DEBUG LOG - FAILURE\n")
                f.write("="*80 + "\n")
                f.write(f"Model: {getattr(self.config, 'model', 'unknown')}\n")
                f.write(f"Problem ID: {problem_id}\n")
                f.write(f"Compiler: {compiler_id}\n")
                f.write(f"Attempt: {attempt}\n")
                f.write(f"Failure Type: {failure_type}\n")
                f.write(f"Error Message: {error_msg}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Response Length: {len(raw_response)} characters\n")
                f.write("="*80 + "\n\n")
                f.write("RAW RESPONSE:\n")
                f.write("-"*40 + "\n")
                f.write(raw_response)
                f.write("\n" + "-"*40 + "\n")
                
                # Add extraction analysis for debugging
                if failure_type == "extraction_failed":
                    f.write("\nEXTRACTION ANALYSIS:\n")
                    f.write("-"*40 + "\n")
                    f.write(f"Response contains triple backticks: {'```' in raw_response}\n")
                    f.write(f"Response contains 'def ': {'def ' in raw_response}\n")
                    f.write(f"Response contains 'import ': {'import ' in raw_response}\n")
                    f.write(f"Response contains 'print(': {'print(' in raw_response}\n")
                    f.write(f"Response contains common code patterns: {any(pattern in raw_response for pattern in ['=', '{', '}', '(', ')', ';'])}\n")
                    
                    # Show first and last 200 characters for pattern analysis
                    f.write(f"\nFirst 200 characters:\n{repr(raw_response[:200])}\n")
                    f.write(f"\nLast 200 characters:\n{repr(raw_response[-200:])}\n")
            
            logger.warning(f"Raw response saved due to {failure_type}: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save raw response on failure: {e}")
