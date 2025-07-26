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
        Generate a solution for the given problem using a two-step process
        
        Args:
            problem_info: Problem information from problem analyzer
            compiler_id: Target compiler/language
            attempt: Current attempt number (for retry logic)
            
        Returns:
            Dict containing generation results
        """
        try:
            console.print(f"[blue]  Attempt {attempt}: Generating solution for {compiler_id} (two-step process)...[/blue]")
            
            # Get problem statement
            problem_statement = self._get_problem_statement(problem_info)
            
            # STEP 1: Generate thoughts/process and initial code
            console.print(f"[blue]    Step 1: Generating approach and initial code...[/blue]")
            step1_prompt = self._create_step1_prompt(problem_statement, compiler_id, problem_info)
            
            step1_response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_step1_system_prompt(compiler_id)
                    },
                    {
                        "role": "user",
                        "content": step1_prompt
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            
            step1_raw_response = step1_response.choices[0].message.content
            
            # STEP 2: Format the previous response to exact output requirements
            console.print(f"[blue]    Step 2: Formatting to exact requirements...[/blue]")
            step2_prompt = self._create_step2_prompt(step1_raw_response, compiler_id, problem_info)
            
            step2_response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_step2_system_prompt(compiler_id)
                    },
                    {
                        "role": "user",
                        "content": step2_prompt
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=0.1,  # Lower temperature for formatting step
                timeout=self.config.timeout
            )
            
            # Extract code from the final response
            final_raw_response = step2_response.choices[0].message.content
            
            # Save raw response for debugging if enabled
            extraction_failed = False
            try:
                code = self._extract_code(final_raw_response, compiler_id)
                if not code:
                    extraction_failed = True
                    raise ValueError("No code found in Step 2 response")
                
                # For C++ code, validate template compliance
                if compiler_id in ["G++17", "G++"] and not self._validate_cpp_template(code):
                    console.print("[red]  ✗ Generation failed: Generated C++ code does not follow required template structure[/red]")
                    logger.warning(f"Template validation failed (attempt {attempt}): Generated C++ code does not follow required template structure")
                    self._save_raw_response_on_failure(final_raw_response, problem_info, compiler_id, attempt, "template_validation_failed", "Generated C++ code does not follow required template structure")
                    
                    return {
                        "success": False,
                        "error": "Format Error",
                        "error_details": "Generated C++ code does not follow required template structure",
                        "compiler_id": compiler_id,
                        "attempt": attempt,
                        "timestamp": datetime.now().isoformat(),
                        "error_type": "template_validation_failed",
                        "code": code  # Include the code for debugging
                    }
                    
            except Exception as e:
                extraction_failed = True
                self._save_raw_response_on_failure(final_raw_response, problem_info, compiler_id, attempt, "extraction_failed", str(e))
                # Also save step 1 response for debugging
                self._save_raw_response_on_failure(step1_raw_response, problem_info, compiler_id, attempt, "step1_response", "Step 1 response for debugging")
                raise
            
            # Save raw responses if logging is enabled (success case)
            self._save_raw_response(step1_raw_response, problem_info, compiler_id, attempt, "step1_success")
            self._save_raw_response(final_raw_response, problem_info, compiler_id, attempt, "step2_success")
            
            # Calculate total token usage
            total_tokens = step1_response.usage.total_tokens + step2_response.usage.total_tokens
            
            result = {
                "success": True,
                "code": code,
                "raw_response": final_raw_response,
                "step1_response": step1_raw_response,
                "compiler_id": compiler_id,
                "attempt": attempt,
                "model": self.config.model,
                "timestamp": datetime.now().isoformat(),
                "token_usage": {
                    "step1_prompt_tokens": step1_response.usage.prompt_tokens,
                    "step1_completion_tokens": step1_response.usage.completion_tokens,
                    "step1_total_tokens": step1_response.usage.total_tokens,
                    "step2_prompt_tokens": step2_response.usage.prompt_tokens,
                    "step2_completion_tokens": step2_response.usage.completion_tokens,
                    "step2_total_tokens": step2_response.usage.total_tokens,
                    "total_tokens": total_tokens
                }
            }
            
            console.print(f"[green]  ✓ Two-step solution generated ({total_tokens} tokens)[/green]")
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

🚨 CRITICAL COMPLETENESS REQUIREMENTS:
- Your solution MUST be a COMPLETE, RUNNABLE program
- ALWAYS include input reading (using input(), cin, Scanner, etc.)
- ALWAYS include output printing (using print(), cout, System.out, etc.)
- NEVER submit partial code, snippets, or incomplete solutions
- The code must work when executed directly without any additions

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
- Make sure to handle edge cases and constraints

🔍 MANDATORY CHECKLIST - Your code MUST include:
✅ Input reading mechanism (input(), scanf, cin, Scanner, etc.)
✅ All necessary variable declarations
✅ Complete algorithm implementation  
✅ Output printing mechanism (print(), printf, cout, System.out, etc.)
✅ Proper program structure (main function if required)"""

        if compiler_id == "Python3":
            return base_prompt + """

PYTHON SPECIFIC REQUIREMENTS:
- Use Python 3 syntax
- MANDATORY: Read input using input() function - NEVER assume variables exist
- MANDATORY: Print output using print() function - match format exactly as shown in Expected Output
- Be careful with integer division (use // for floor division)
- Use print() with appropriate separators and end parameters to match exact format
- Example: print(a, b, c) for space-separated vs print(f"({a},{b},{c})") for parentheses format

🚨 PYTHON COMPLETENESS CHECKLIST:
✅ ALWAYS start with input reading: input(), map(int, input().split()), etc.
✅ ALWAYS end with print() statement(s) producing the exact expected output
✅ NEVER use 'return' statements outside of functions - this causes SyntaxError
✅ Write main execution code at the top level, not inside functions unless specifically needed
✅ NEVER submit code that only assigns variables without printing results
✅ NEVER submit expressions like "result = char.lower()" without printing

COMPLETE PYTHON TEMPLATE PATTERN:
# Read input first
data = input()  # or appropriate input reading
# Process the data
result = process(data)  # your algorithm here
# Print the result
print(result)  # or appropriate output format

CRITICAL: If you don't include BOTH input reading AND print statements, your solution will fail!
"""
        elif compiler_id in ["G++17", "G++"]:
            return base_prompt + """

C++ SPECIFIC REQUIREMENTS:
- Use standard competitive programming includes: #include <iostream> and others as needed
- MANDATORY: Include proper main() function
- MANDATORY: Read input using std::cin, getline, scanf, or similar - NEVER assume variables exist
- MANDATORY: Print output using std::cout, printf, or similar - match format exactly as shown in Expected Output
- MANDATORY: Use the EXACT template structure shown below - DO NOT deviate from this format
- Pay attention to spacing and separators: cout << a << " " << b for space-separated vs cout << "(" << a << "," << b << "," << c << ")" for parentheses format

🚨 C++ COMPLETENESS CHECKLIST:
✅ #include <iostream> (and other necessary headers)
✅ using namespace std; statement
✅ int main() function definition 
✅ Input reading inside main (cin >> variables or getline)
✅ Algorithm implementation
✅ Output printing (cout << result)
✅ return 0; statement

🚨 MANDATORY C++ TEMPLATE - USE EXACTLY THIS STRUCTURE:
#include <iostream>
using namespace std;

int main() {
    // Read input
    [INSERT YOUR VARIABLE DECLARATIONS HERE]
    [INSERT YOUR INPUT READING HERE]
    
    // Process/Algorithm
    [INSERT YOUR ALGORITHM HERE]
    
    // Print output
    [INSERT YOUR OUTPUT PRINTING HERE]
    
    return 0;
}

📚 TEMPLATE EXAMPLES - Study these patterns:

Example 1 - Sum of two integers:
```cpp
#include <iostream>
using namespace std;

int main() {
    // Read input
    int a, b;
    cin >> a >> b;
    
    // Process/Algorithm
    int sum = a + b;
    
    // Print output
    cout << sum << endl;
    
    return 0;
}
```

Example 2 - String processing:
```cpp
#include <iostream>
using namespace std;

int main() {
    // Read input
    string text;
    cin >> text;
    
    // Process/Algorithm
    string result = "";
    for (char c : text) {
        result += (char)tolower(c);
    }
    
    // Print output
    cout << result << endl;
    
    return 0;
}
```

Example 3 - Multiple test cases:
```cpp
#include <iostream>
using namespace std;

int main() {
    // Read input
    int n;
    cin >> n;
    
    // Process/Algorithm
    for (int i = 0; i < n; i++) {
        int x;
        cin >> x;
        cout << x * 2 << endl;
    }
    
    return 0;
}
```

⚠️ CRITICAL: Your code MUST follow this exact template structure. Replace the bracketed sections with your specific implementation, but keep the overall structure identical.
"""

        elif compiler_id == "JDK":
            return base_prompt + """

JAVA SPECIFIC REQUIREMENTS:
- Create a public class named 'Main'
- MANDATORY: Include proper main method: public static void main(String[] args)
- MANDATORY: Read input using Scanner, BufferedReader, or similar - NEVER assume variables exist
- MANDATORY: Print output using System.out.println() or System.out.print() - match format exactly as shown in Expected Output
- Pay attention to spacing and separators: System.out.println(a + " " + b) for space-separated vs System.out.println("(" + a + "," + b + "," + c + ")") for parentheses format
- Be careful with data types and overflow

🚨 JAVA COMPLETENESS CHECKLIST:
✅ import java.util.Scanner; (or other necessary imports)
✅ public class Main declaration
✅ public static void main(String[] args) method
✅ Scanner input reading inside main
✅ Algorithm implementation
✅ System.out printing statements

COMPLETE JAVA TEMPLATE PATTERN:
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        
        // Read input
        int a = scanner.nextInt(); // or appropriate input reading
        int b = scanner.nextInt();
        
        // Process
        int result = a + b; // your algorithm here
        
        // Print output
        System.out.println(result); // or appropriate output format
    }
}
"""

        else:
            return base_prompt
    
    def _create_prompt(self, problem_data: Dict[str, Any], language: str) -> str:
        """Create prompt for the AI model"""
        if language == "G++17":
            # C++ specific prompt
            return f"""Please solve the following competitive programming problem in C++.
Your solution should be a single, complete, and runnable C++ program.
It must include all necessary headers, such as `<iostream>`, and be wrapped in a `main` function.
Do not use any external libraries or platform-specific features.
Focus on correctness and efficiency.

**Problem Details:**

**Title:** {problem_data.get('title', 'Unknown')}

**Statement:**
{problem_data.get('statement', '')}

**Input:**
{problem_data.get('input', '')}

**Output:**
{problem_data.get('output', '')}

**Sample Inputs and Outputs:**
{self._format_samples(problem_data.get('samples', []))}

Your final output should be only the C++ code, with no additional explanations or markdown.
"""
        else:
            # Default prompt for other languages
            return f"""Solve this programming problem in {language}:

Title: {problem_data.get('title', 'Unknown')}

Statement:
{problem_data.get('statement', '')}

Input:
{problem_data.get('input', '')}

Output:
{problem_data.get('output', '')}

Sample Inputs and Outputs:
{self._format_samples(problem_data.get('samples', []))}

Generate only the code solution without any explanation or markdown formatting.
"""
    
    def _format_samples(self, samples: List[Dict[str, str]]) -> str:
        """Format sample inputs and outputs"""
        if not samples:
            return "No samples provided"
        
        formatted = []
        for i, sample in enumerate(samples, 1):
            formatted.append(f"Sample {i}:")
            formatted.append(f"Input:\n{sample.get('input', '')}")
            formatted.append(f"Output:\n{sample.get('output', '')}\n")
        
        return "\n".join(formatted)
    
    def _get_language_name(self, compiler_id: str) -> str:
        """Get language name from compiler ID"""
        if "python" in compiler_id.lower():
            return "Python"
        elif "cpp" in compiler_id.lower() or "g++" in compiler_id.lower():
            return "C++"
        elif "java" in compiler_id.lower() or "jdk" in compiler_id.lower():
            return "Java"
        else:
            return compiler_id
    
    def _get_step1_system_prompt(self, compiler_id: str) -> str:
        """Get the system prompt for step 1: thinking and initial code generation"""
        
        language_name = self._get_language_name(compiler_id)
        
        base_step1_prompt = f"""You are an expert competitive programming assistant. Your task is to analyze programming problems and develop solutions.

This is STEP 1 of a two-step process. In this step, you should:

1. ANALYZE the problem thoroughly
2. THINK through the approach and algorithm
3. GENERATE the initial code solution

🚨 CRITICAL: Your code solution must be COMPLETE and RUNNABLE, including:
✅ INPUT READING: Always read input using appropriate methods (input(), cin, Scanner)
✅ ALGORITHM: Complete solution logic 
✅ OUTPUT PRINTING: Always print results using appropriate methods (print(), cout, System.out)

Be thorough in your analysis and explanation. You can include:
- Problem understanding
- Algorithm approach
- Key insights
- Implementation details
- Code with comments if helpful

Focus on correctness and completeness. Don't worry about exact formatting in this step - that will be handled in step 2.

Target language: {language_name}"""

        if compiler_id == "Python3":
            return base_step1_prompt + """

CRITICAL PYTHON SYNTAX CONSTRAINTS:
- NEVER use 'return' statements outside of functions - causes SyntaxError: 'return' outside function
- NEVER use 'continue' statements outside of loops - causes SyntaxError: 'continue' not properly in loop  
- NEVER use 'break' statements outside of loops - causes SyntaxError: 'break' outside loop
- These keywords MUST be used only in their proper contexts:
  * 'return' only inside function definitions (def)
  * 'continue' and 'break' only inside loop statements (for/while)
- For early exit logic, use conditional blocks (if/elif/else) or organize code properly in functions
- Write main execution code at the top level, not inside functions unless necessary
- Use proper control flow with if/elif/else statements for different cases

🚨 PYTHON COMPLETENESS REQUIREMENTS:
✅ ALWAYS start with input reading: input(), input().split(), map(int, input().split()), etc.
✅ ALWAYS end with print() statements - NEVER leave results unprinted
✅ NEVER submit partial code like "result = char.lower()" without input reading and printing
✅ Make sure the code is a complete program that runs from start to finish

REQUIRED PYTHON STRUCTURE:
# Step 1: Read input
data = input()  # or appropriate input method

# Step 2: Process/solve
result = solve(data)  # your algorithm here

# Step 3: Print output  
print(result)  # or appropriate output format"""
        
        return base_step1_prompt

    def _get_step2_system_prompt(self, compiler_id: str) -> str:
        """Get the system prompt for step 2: exact formatting"""
        
        base_prompt = """You are a code formatter that takes an AI-generated solution and formats it to exact submission requirements.

CRITICAL: Your ONLY job is to extract and format the final code for submission.

🚨 MANDATORY COMPLETENESS CHECK:
Before outputting code, verify it includes:
✅ INPUT READING: Code must read input (input(), cin, Scanner, etc.)
✅ OUTPUT PRINTING: Code must print results (print(), cout, System.out, etc.)
✅ COMPLETE ALGORITHM: Full solution implementation
✅ PROPER STRUCTURE: Runnable program with correct syntax

If the step 1 response is missing input reading or print statements, you MUST add them!

ABSOLUTE OUTPUT FORMAT REQUIREMENTS:
- Study the test cases CAREFULLY - the "Expected Output" shows the EXACT format required
- Your code output must match EXACTLY: spacing, punctuation, separators, newlines
- Even ONE wrong character will cause WRONG verdict
- Look at Expected Output patterns: "2 3 1" vs "(2,3,1)" vs "2,3,1" - match exactly
- Count spaces, check for parentheses, commas, brackets - be precise

CODE REQUIREMENTS:
- Output ONLY the clean, executable code
- NO explanations, comments, or text before/after the code  
- NO markdown formatting (no ```)
- Ensure the code is ready for direct submission to an online judge
- The code should be complete and runnable as-is

FORMAT ANALYSIS REQUIRED:
- Before writing code, analyze the Expected Output format in test cases
- Identify exact patterns: space-separated, comma-separated, parentheses, etc.
- Ensure your print statements match this format precisely"""

        if compiler_id == "Python3":
            return base_prompt + """

PYTHON SPECIFIC:
- Use Python 3 syntax
- CRITICAL FORMAT MATCHING: Your print() statements must produce EXACTLY the Expected Output format
- Examples of precise formatting:
  * For "2 3 1": use print(a, b, c) or print(f"{a} {b} {c}")
  * For "(2,3,1)": use print(f"({a},{b},{c})")  
  * For "2,3,1": use print(f"{a},{b},{c}")
  * For multiple lines: use separate print() calls

🚨 MANDATORY COMPLETENESS VERIFICATION:
If step 1 response is missing critical components, ADD THEM:

Missing input reading? ADD: 
- input() for single line
- input().split() for multiple values  
- map(int, input().split()) for integers
- int(input()) for single integer

Missing print statements? ADD:
- print(result) for single output
- print(a, b, c) for space-separated
- print(f"({a},{b},{c})") for formatted output

🚨 CRITICAL SYNTAX FIXING REQUIRED:
- MANDATORY: Scan step 1 response for these FATAL syntax errors:
  
  1. 'return' statements outside functions (causes SyntaxError: 'return' outside function)
  2. 'continue' statements outside loops (causes SyntaxError: 'continue' not properly in loop)
  3. 'break' statements outside loops (causes SyntaxError: 'break' outside loop)

- If ANY of these are found, you MUST fix them immediately
- Replace control flow with proper structures:
  
  ❌ BROKEN (causes SyntaxError):
  if n == 1:
      print(1)
      return  # ERROR: return outside function
  
  if condition:
      continue  # ERROR: continue not in loop
  
  ✅ FIXED (works correctly):
  if n == 1:
      print(1)
  else:
      # handle other cases
  
  # Or use early exit with proper structure:
  if condition:
      # handle this case
      pass
  else:
      # handle other cases

- SCAN EVERY LINE: Look for standalone 'return', 'continue', 'break' keywords
- These must ONLY appear inside their proper contexts (functions/loops)
- Write main execution code at the top level
- Double-check your print statements match the Expected Output format character-by-character
- Your final code must be syntactically correct and executable

🔍 FINAL VERIFICATION - Your output code MUST have:
✅ Input reading at the beginning
✅ Algorithm implementation in the middle  
✅ Print statements at the end
✅ Correct syntax (no return/continue/break outside proper contexts)
✅ Exact output format matching test cases"""

        elif compiler_id in ["G++17", "G++"]:
            return base_prompt + """

C++ SPECIFIC:
- Include necessary headers (#include <iostream>, etc.)
- Include proper main() function
- Use std::cin/cout for input/output
- Match output format exactly as specified
- MANDATORY: Use the exact template structure specified

🚨 MANDATORY TEMPLATE ENFORCEMENT:
Your output code MUST follow this EXACT structure:

#include <iostream>
using namespace std;

int main() {
    // Read input
    [variable declarations and input reading]
    
    // Process/Algorithm
    [your algorithm implementation]
    
    // Print output
    [output printing statements]
    
    return 0;
}

📚 CORRECT TEMPLATE EXAMPLES:

Example 1:
#include <iostream>
using namespace std;

int main() {
    // Read input
    int a, b;
    cin >> a >> b;
    
    // Process/Algorithm
    int result = a + b;
    
    // Print output
    cout << result << endl;
    
    return 0;
}

Example 2:
#include <iostream>
using namespace std;

int main() {
    // Read input
    string s;
    cin >> s;
    
    // Process/Algorithm
    string reversed = "";
    for (int i = s.length() - 1; i >= 0; i--) {
        reversed += s[i];
    }
    
    // Print output
    cout << reversed << endl;
    
    return 0;
}

🚨 MANDATORY COMPLETENESS VERIFICATION:
If step 1 response is missing critical components, ADD THEM:

Missing template structure? REFORMAT to match the exact template above
Missing input reading? ADD:
- cin >> variable; or getline(cin, variable); statements inside main()
- Proper variable declarations

Missing output printing? ADD:  
- cout << result << endl; statements
- Proper formatting to match expected output

🔍 FINAL VERIFICATION - Your output code MUST have:
✅ #include <iostream> and necessary headers
✅ using namespace std; statement
✅ int main() function (EXACTLY as shown)
✅ Input reading with cin inside main
✅ Algorithm implementation inside main
✅ Output printing with cout inside main
✅ return 0; statement
✅ EXACT template structure as specified above"""

        elif compiler_id == "JDK":
            return base_prompt + """

JAVA SPECIFIC:
- Public class named 'Main'
- Include main method: public static void main(String[] args)
- Use appropriate input/output methods
- Match output format exactly as specified

🚨 MANDATORY COMPLETENESS VERIFICATION:
If step 1 response is missing critical components, ADD THEM:

Missing input reading? ADD:
- Scanner scanner = new Scanner(System.in);
- scanner.nextInt(), scanner.nextLine(), etc.

Missing output printing? ADD:
- System.out.println() or System.out.print() statements
- Proper formatting to match expected output

🔍 FINAL VERIFICATION - Your output code MUST have:
✅ import statements (Scanner, etc.)
✅ public class Main
✅ public static void main method
✅ Scanner input reading
✅ Algorithm implementation  
✅ System.out printing statements"""

        return base_prompt

    def _create_step1_prompt(self, problem_statement: str, compiler_id: str, problem_info: Dict[str, Any] = None) -> str:
        """Create prompt for step 1: analysis and initial code generation"""
        
        language_name = self._get_language_name(compiler_id)
        
        # Extract test case information to help with output format understanding
        test_case_info = ""
        if problem_info:
            test_case_info = self._extract_test_cases_for_step1(problem_info)
        
        base_prompt = f"""Analyze this competitive programming problem and develop a solution in {language_name}.

{problem_statement}

{test_case_info}

Please provide:
1. Your understanding of the problem
2. The algorithm/approach you'll use
3. Any key insights or edge cases to consider
4. The complete {language_name} solution

Be thorough in your analysis and make sure your solution handles all the test cases correctly and produces the exact output format shown in the examples."""
        
        return base_prompt

    def _extract_test_cases_for_step1(self, problem_info: Dict[str, Any]) -> str:
        """Extract test case information for step 1 to help understand the expected output format"""
        if not problem_info:
            return ""
            
        test_cases = []
        
        # Get sample test cases
        sample_testcases = problem_info.get("sample_testcases", [])
        for i, testcase in enumerate(sample_testcases[:3], 1):  # Limit to first 3
            try:
                import base64
                # Handle both dict access and attribute access
                if hasattr(testcase, 'input_b64'):
                    input_data = base64.b64decode(testcase.input_b64).decode('utf-8').strip()
                    expected_output = base64.b64decode(testcase.correct_b64).decode('utf-8').strip()
                else:
                    input_data = base64.b64decode(testcase.get("input_b64", "")).decode('utf-8').strip()
                    expected_output = base64.b64decode(testcase.get("correct_b64", "")).decode('utf-8').strip()
                
                test_cases.append((input_data, expected_output, f"Sample {i}"))
            except Exception as e:
                continue
        
        # Get public test cases if not enough samples
        if len(test_cases) < 2:
            public_testcases = problem_info.get("public_testcases", [])
            for i, testcase in enumerate(public_testcases[:3], 1):
                try:
                    input_data = base64.b64decode(testcase.get("input_b64", "")).decode('utf-8').strip()
                    expected_output = base64.b64decode(testcase.get("correct_b64", "")).decode('utf-8').strip()
                    test_cases.append((input_data, expected_output, f"Public {i}"))
                except:
                    continue
        
        if not test_cases:
            return ""
        
        # Build test case information for step 1
        test_case_info = "📋 EXAMPLE TEST CASES (showing expected input/output format):\n"
        test_case_info += "=" * 60 + "\n\n"
        
        for input_data, expected_output, case_type in test_cases:
            test_case_info += f"{case_type} Test Case:\n"
            test_case_info += f"Input:\n{input_data}\n\n"
            test_case_info += f"Expected Output:\n{expected_output}\n\n"
            test_case_info += "-" * 40 + "\n\n"
        
        test_case_info += "🎯 CRITICAL: Your solution must produce EXACTLY the output format shown above.\n"
        test_case_info += "Pay close attention to spacing, separators, and line breaks.\n"
        
        return test_case_info

    def _create_step2_prompt(self, step1_response: str, compiler_id: str, problem_info: Dict[str, Any] = None) -> str:
        """Create prompt for step 2: exact formatting"""
        
        language_name = self._get_language_name(compiler_id)
        
        # Extract output format examples from test cases
        format_examples = self._extract_output_format_examples(problem_info) if problem_info else ""
        
        # Detect completeness issues (missing input/output) and syntax issues
        completeness_issues = self._detect_completeness_issues(step1_response, compiler_id)
        syntax_issues = ""
        if compiler_id == "Python3":
            syntax_issues = self._detect_syntax_issues(step1_response)
        
        base_prompt = f"""Take the following AI-generated solution and extract ONLY the final {language_name} code for submission.

{format_examples}

{completeness_issues}

{syntax_issues}

Previous response:
{step1_response}

🚨 CRITICAL VERIFICATION REQUIRED:
Check the previous response for these common issues and FIX them:
1. ❌ Missing input reading → ADD appropriate input statements
2. ❌ Missing print/output → ADD appropriate print statements  
3. ❌ Incomplete code (partial expressions) → COMPLETE the solution
4. ❌ Wrong output format → MATCH the expected format exactly

CRITICAL: Study the Expected Output format above and ensure your code produces EXACTLY that format.

Output ONLY the clean, executable {language_name} code with no explanations, comments, or formatting. The code should be ready for direct submission to an online judge."""
        
        return base_prompt
    
    def _detect_completeness_issues(self, step1_response: str, compiler_id: str) -> str:
        """Detect missing input reading and print statements in step 1 response"""
        
        issues = []
        
        # Check for input reading
        input_found = False
        if compiler_id == "Python3":
            input_patterns = ['input()', 'input().split()', 'map(int, input().split())', 'int(input())']
            input_found = any(pattern in step1_response for pattern in input_patterns)
        elif compiler_id in ["G++17", "G++"]:
            input_patterns = ['cin >>', 'scanf(', 'getline(', 'getline (']
            input_found = any(pattern in step1_response for pattern in input_patterns)
        elif compiler_id == "JDK":
            input_patterns = ['Scanner', 'nextInt()', 'nextLine()', 'BufferedReader']
            input_found = any(pattern in step1_response for pattern in input_patterns)
        
        if not input_found:
            issues.append("🚨 MISSING INPUT READING")
        
        # Check for output printing
        output_found = False
        if compiler_id == "Python3":
            output_patterns = ['print(']
            output_found = any(pattern in step1_response for pattern in output_patterns)
        elif compiler_id in ["G++17", "G++"]:
            output_patterns = ['cout <<', 'printf(']
            output_found = any(pattern in step1_response for pattern in output_patterns)
        elif compiler_id == "JDK":
            output_patterns = ['System.out.print', 'System.out.println']
            output_found = any(pattern in step1_response for pattern in output_patterns)
        
        if not output_found:
            issues.append("🚨 MISSING OUTPUT PRINTING")
        
        # Check for incomplete code patterns
        incomplete_patterns = []
        if compiler_id == "Python3":
            # Look for variable assignments without print statements that follow
            lines = step1_response.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Check for result assignments that aren't followed by prints
                if (stripped.startswith('result = ') and 
                    not any('print(' in lines[j] for j in range(i+1, min(len(lines), i+5)))):
                    incomplete_patterns.append(f"Assignment '{stripped}' not followed by print statement")
        
        if incomplete_patterns:
            issues.append("🚨 INCOMPLETE CODE PATTERNS DETECTED")
        
        if not issues:
            return ""
        
        issue_description = "🚨 CRITICAL COMPLETENESS ISSUES DETECTED:\n"
        issue_description += "=" * 50 + "\n\n"
        
        if "🚨 MISSING INPUT READING" in issues:
            issue_description += "❌ NO INPUT READING FOUND!\n"
            if compiler_id == "Python3":
                issue_description += "   MUST ADD: input(), input().split(), map(int, input().split()), etc.\n"
            elif compiler_id in ["G++17", "G++"]:
                issue_description += "   MUST ADD: cin >> variable; or getline(cin, variable); statements\n"
            elif compiler_id == "JDK":
                issue_description += "   MUST ADD: Scanner scanner = new Scanner(System.in); and reading methods\n"
            issue_description += "\n"
        
        if "🚨 MISSING OUTPUT PRINTING" in issues:
            issue_description += "❌ NO OUTPUT PRINTING FOUND!\n"
            if compiler_id == "Python3":
                issue_description += "   MUST ADD: print() statements to output results\n"
            elif compiler_id in ["G++17", "G++"]:
                issue_description += "   MUST ADD: cout << result << endl; statements\n"
            elif compiler_id == "JDK":
                issue_description += "   MUST ADD: System.out.println() or System.out.print() statements\n"
            issue_description += "\n"
        
        if incomplete_patterns:
            issue_description += "❌ INCOMPLETE CODE DETECTED:\n"
            for pattern in incomplete_patterns:
                issue_description += f"   • {pattern}\n"
            issue_description += "\n"
        
        issue_description += "🔧 MANDATORY FIXES:\n"
        issue_description += "✅ ADD input reading at the beginning\n"
        issue_description += "✅ ADD output printing at the end\n" 
        issue_description += "✅ COMPLETE any partial code snippets\n"
        issue_description += "✅ ENSURE the code is a complete, runnable program\n\n"
        
        return issue_description
    
    def _detect_syntax_issues(self, step1_response: str) -> str:
        """Detect problematic control flow statements in step 1 response and provide fixing instructions"""
        
        # Extract potential code blocks from step1 response
        code_blocks = []
        
        # Look for markdown code blocks
        import re
        markdown_pattern = r'```(?:python|py)?\n?(.*?)```'
        matches = re.findall(markdown_pattern, step1_response, re.DOTALL | re.IGNORECASE)
        code_blocks.extend(matches)
        
        # Also check the whole response for code-like content
        lines = step1_response.split('\n')
        potential_code = []
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith('def ') or stripped.startswith('if ') or 
                stripped.startswith('for ') or stripped.startswith('while ') or
                'print(' in stripped or stripped.startswith('return') or
                '=' in stripped and not stripped.startswith('#')):
                potential_code.append(line)
        
        if potential_code:
            code_blocks.append('\n'.join(potential_code))
        
        # Check for problematic control flow statements
        problematic_statements = []
        for code_block in code_blocks:
            lines = code_block.split('\n')
            in_function = False
            in_loop = False
            function_indent = 0
            loop_stack = []  # Stack to track nested loops
            
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                current_indent = len(line) - len(line.lstrip())
                
                # Track if we're inside a function
                if stripped.startswith('def '):
                    in_function = True
                    function_indent = current_indent
                elif in_function and stripped and current_indent <= function_indent:
                    # We've left the function (dedent to same level or less)
                    in_function = False
                    function_indent = 0
                
                # Track if we're inside a loop
                if (stripped.startswith('for ') or stripped.startswith('while ')):
                    loop_stack.append(current_indent)
                    in_loop = True
                elif in_loop and stripped and current_indent <= min(loop_stack) if loop_stack else False:
                    # We've left all loops (dedent to same level or less than the outermost loop)
                    loop_stack = [indent for indent in loop_stack if indent < current_indent]
                    in_loop = len(loop_stack) > 0
                
                # Check for return statements outside functions
                if 'return' in stripped:
                    is_return_statement = (stripped == 'return' or 
                                         stripped.startswith('return ') or 
                                         stripped.startswith('return#') or
                                         stripped.endswith('return'))
                    
                    if is_return_statement and not in_function:
                        problematic_statements.append({
                            'type': 'return',
                            'error': 'return outside function',
                            'line': i,
                            'content': line,
                            'context': lines[max(0, i-2):min(len(lines), i+2)]
                        })
                
                # Check for continue statements outside loops
                if 'continue' in stripped:
                    is_continue_statement = (stripped == 'continue' or 
                                           stripped.startswith('continue ') or 
                                           stripped.startswith('continue#') or
                                           stripped.endswith('continue'))
                    
                    if is_continue_statement and not in_loop:
                        problematic_statements.append({
                            'type': 'continue',
                            'error': 'continue not properly in loop',
                            'line': i,
                            'content': line,
                            'context': lines[max(0, i-2):min(len(lines), i+2)]
                        })
                
                # Check for break statements outside loops
                if 'break' in stripped:
                    is_break_statement = (stripped == 'break' or 
                                        stripped.startswith('break ') or 
                                        stripped.startswith('break#') or
                                        stripped.endswith('break'))
                    
                    if is_break_statement and not in_loop:
                        problematic_statements.append({
                            'type': 'break',
                            'error': 'break outside loop',
                            'line': i,
                            'content': line,
                            'context': lines[max(0, i-2):min(len(lines), i+2)]
                        })
        
        if problematic_statements:
            issue_description = "🚨 CRITICAL PYTHON SYNTAX ISSUES DETECTED:\n"
            issue_description += "=" * 50 + "\n\n"
            
            # Group by type
            returns = [s for s in problematic_statements if s['type'] == 'return']
            continues = [s for s in problematic_statements if s['type'] == 'continue']
            breaks = [s for s in problematic_statements if s['type'] == 'break']
            
            total_issues = len(problematic_statements)
            issue_description += f"Found {total_issues} FATAL syntax error(s) in step 1 response:\n"
            if returns:
                issue_description += f"  • {len(returns)} 'return' statement(s) outside functions\n"
            if continues:
                issue_description += f"  • {len(continues)} 'continue' statement(s) outside loops\n"
            if breaks:
                issue_description += f"  • {len(breaks)} 'break' statement(s) outside loops\n"
            issue_description += "\n"
            
            # Show details for each issue
            for i, issue in enumerate(problematic_statements, 1):
                issue_description += f"Issue {i} - SyntaxError: '{issue['error']}':\n"
                issue_description += f"  Line: {issue['line']}\n"
                issue_description += f"  Code: {issue['content'].strip()}\n"
                issue_description += f"  Context:\n"
                for ctx_line in issue['context']:
                    issue_description += f"    {ctx_line}\n"
                issue_description += "\n"
            
            issue_description += "MANDATORY FIXES REQUIRED:\n"
            if returns:
                issue_description += "✓ REMOVE all 'return' statements outside functions\n"
            if continues:
                issue_description += "✓ REMOVE all 'continue' statements outside loops\n"
            if breaks:
                issue_description += "✓ REMOVE all 'break' statements outside loops\n"
            issue_description += "✓ Replace with proper if/elif/else conditional blocks\n"
            issue_description += "✓ Use function/loop organization if complex logic needed\n"
            issue_description += "✓ Ensure main execution code is at top level\n\n"
            
            issue_description += "EXAMPLE FIXES:\n"
            issue_description += "❌ BAD:\n"
            issue_description += "   if condition:\n"
            issue_description += "       print('result')\n"
            issue_description += "       return  # ERROR: return outside function\n"
            issue_description += "   \n"
            issue_description += "   if other_condition:\n"
            issue_description += "       continue  # ERROR: continue not in loop\n"
            issue_description += "\n"
            issue_description += "✅ GOOD:\n"
            issue_description += "   if condition:\n"
            issue_description += "       print('result')\n"
            issue_description += "   elif other_condition:\n"
            issue_description += "       # handle this case\n"
            issue_description += "       pass\n"
            issue_description += "   else:\n"
            issue_description += "       # handle remaining cases\n\n"
            
            return issue_description
        
        return ""
    
    def _extract_output_format_examples(self, problem_info: Dict[str, Any]) -> str:
        """Extract structured output format analysis from test cases for step 2"""
        if not problem_info:
            return ""
            
        test_cases = []
        
        # Get sample test cases
        sample_testcases = problem_info.get("sample_testcases", [])
        for i, testcase in enumerate(sample_testcases[:3], 1):  # Limit to first 3
            try:
                input_data = base64.b64decode(testcase.get("input_b64", "")).decode('utf-8').strip()
                expected_output = base64.b64decode(testcase.get("correct_b64", "")).decode('utf-8').strip()
                test_cases.append((input_data, expected_output))
            except:
                continue
        
        # Get public test cases if not enough samples
        if len(test_cases) < 2:
            public_testcases = problem_info.get("public_testcases", [])
            for testcase in public_testcases[:2]:
                try:
                    input_data = base64.b64decode(testcase.get("input_b64", "")).decode('utf-8').strip()
                    expected_output = base64.b64decode(testcase.get("correct_b64", "")).decode('utf-8').strip()
                    test_cases.append((input_data, expected_output))
                except:
                    continue
        
        if not test_cases:
            return ""
        
        # Analyze format patterns
        format_analysis = self._analyze_output_patterns(test_cases)
        
        # Build structured format guide
        format_guide = "🎯 CRITICAL OUTPUT FORMAT REQUIREMENTS:\n"
        format_guide += "=" * 50 + "\n\n"
        
        # Show test cases with detailed analysis
        format_guide += "📋 TEST CASE ANALYSIS:\n"
        for i, (input_data, expected_output) in enumerate(test_cases, 1):
            format_guide += f"  Case {i}:\n"
            format_guide += f"    Input:  '{input_data}'\n"
            format_guide += f"    Output: '{expected_output}'\n"
            format_guide += f"    Length: {len(expected_output)} characters\n"
            if '\n' in expected_output:
                lines = expected_output.split('\n')
                format_guide += f"    Lines:  {len(lines)} lines\n"
                for j, line in enumerate(lines, 1):
                    format_guide += f"      Line {j}: '{line}' ({len(line)} chars)\n"
            format_guide += "\n"
        
        # Add pattern analysis
        format_guide += "🔍 FORMAT PATTERN ANALYSIS:\n"
        format_guide += format_analysis + "\n"
        
        # Add specific Python code instructions
        format_guide += "💻 EXACT PYTHON IMPLEMENTATION REQUIRED:\n"
        python_code = self._generate_python_format_code(test_cases)
        format_guide += python_code + "\n"
        
        format_guide += "⚠️  YOUR CODE MUST PRODUCE EXACTLY THE SAME OUTPUT - CHARACTER BY CHARACTER!\n"
        
        return format_guide
    
    def _analyze_output_patterns(self, test_cases: List[tuple]) -> str:
        """Analyze output patterns to identify format requirements"""
        if not test_cases:
            return ""
        
        patterns = []
        
        # Check for common patterns
        if all(' ' in output and ',' not in output and '(' not in output for _, output in test_cases):
            patterns.append("✓ SPACE-SEPARATED format detected")
            patterns.append("  Use: print(a, b, c) or print(f'{a} {b} {c}')")
        
        elif all('(' in output and ')' in output and ',' in output for _, output in test_cases):
            patterns.append("✓ PARENTHESES WITH COMMAS format detected")
            patterns.append("  Use: print(f'({a},{b},{c})')")
        
        elif all(',' in output and '(' not in output for _, output in test_cases):
            patterns.append("✓ COMMA-SEPARATED format detected")
            patterns.append("  Use: print(f'{a},{b},{c}')")
        
        # Check for multi-line output
        if any('\n' in output for _, output in test_cases):
            patterns.append("✓ MULTI-LINE output detected")
            patterns.append("  Use: Multiple print() statements")
        
        # Check for specific characters
        special_chars = set()
        for _, output in test_cases:
            for char in output:
                if char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n':
                    special_chars.add(char)
        
        if special_chars:
            patterns.append(f"✓ Special characters found: {', '.join(sorted(special_chars))}")
            patterns.append("  Must include these exact characters in output")
        
        # Check for trailing newlines
        has_trailing_newline = any(output.endswith('\n') for _, output in test_cases)
        if has_trailing_newline:
            patterns.append("✓ Trailing newline detected - use print() not print(..., end='')")
        
        return '\n'.join(patterns) if patterns else "Format pattern unclear - match examples exactly"
    
    def _generate_python_format_code(self, test_cases: List[tuple]) -> str:
        """Generate specific Python code examples for the detected format"""
        if not test_cases:
            return ""
        
        first_output = test_cases[0][1]
        
        code_examples = []
        
        # Generate format-specific code
        if ' ' in first_output and ',' not in first_output and '(' not in first_output:
            # Space-separated
            code_examples.append("# For space-separated output:")
            code_examples.append("print(value1, value2, value3)  # Automatic spaces")
            code_examples.append("# OR")
            code_examples.append("print(f'{value1} {value2} {value3}')  # Manual spaces")
        
        elif '(' in first_output and ')' in first_output and ',' in first_output:
            # Parentheses with commas
            code_examples.append("# For parentheses with commas:")
            code_examples.append("print(f'({value1},{value2},{value3})')")
        
        elif ',' in first_output and '(' not in first_output:
            # Comma-separated
            code_examples.append("# For comma-separated output:")
            code_examples.append("print(f'{value1},{value2},{value3}')")
        
        if '\n' in first_output:
            code_examples.append("# For multi-line output:")
            code_examples.append("print('first line')")
            code_examples.append("print('second line')")
        
        return '\n'.join(code_examples) if code_examples else "# Match the exact format shown above"
    
    def _validate_cpp_template(self, code: str) -> bool:
        """
        Validate that C++ code follows the required template structure:
        #include <iostream>
        using namespace std;
        int main() { ... return 0; }
        """
        if not code or not isinstance(code, str):
            console.print("[red]  ✗ Template validation failed: Code is empty or invalid[/red]")
            return False
        
        # Normalize whitespace for easier pattern matching
        normalized_code = ' '.join(code.split())
        lines = [line.strip() for line in code.split('\n') if line.strip()]
        
        template_issues = []
        
        # Check for required includes
        if '#include <iostream>' not in code and '#include<iostream>' not in normalized_code:
            template_issues.append("Missing required '#include <iostream>'")
        
        # Check for using namespace std
        if 'using namespace std;' not in code and 'using namespace std ;' not in normalized_code:
            template_issues.append("Missing required 'using namespace std;'")
        
        # Check for main function
        main_found = False
        for pattern in ['int main()', 'int main( )', 'int main ( )', 'int main(void)', 'int main( void )']:
            if pattern in normalized_code:
                main_found = True
                break
        
        if not main_found:
            template_issues.append("Missing required 'int main()' function")
        
        # Check for return 0
        if 'return 0;' not in code and 'return 0 ;' not in normalized_code:
            template_issues.append("Missing required 'return 0;' statement")
        
        # Check for basic input/output patterns (cin/cout/getline)
        has_input = any(pattern in code for pattern in ['cin >>', 'cin>>', 'std::cin >>', 'std::cin>>', 'getline(', 'getline ('])
        has_output = any(pattern in code for pattern in ['cout <<', 'cout<<', 'std::cout <<', 'std::cout<<'])
        
        if not has_input:
            template_issues.append("Missing input reading with cin")
        
        if not has_output:
            template_issues.append("Missing output printing with cout")
        
        # Check overall structure order
        structure_valid = True
        include_pos = -1
        using_pos = -1
        main_pos = -1
        
        for i, line in enumerate(lines):
            if '#include' in line and 'iostream' in line:
                include_pos = i
            elif 'using namespace std' in line:
                using_pos = i
            elif 'int main(' in line:
                main_pos = i
        
        if include_pos >= 0 and using_pos >= 0 and include_pos > using_pos:
            structure_valid = False
            template_issues.append("Template structure error: #include should come before using namespace")
        
        if using_pos >= 0 and main_pos >= 0 and using_pos > main_pos:
            structure_valid = False
            template_issues.append("Template structure error: using namespace should come before main function")
        
        if template_issues:
            console.print(f"[red]  ✗ C++ Template validation failed:[/red]")
            for issue in template_issues:
                console.print(f"[red]    • {issue}[/red]")
            return False
        
        console.print("[green]  ✓ C++ Template validation passed[/green]")
        return True
    
    def _extract_code(self, response: str, compiler_id: str) -> Optional[str]:
        """Extract code from OpenAI response"""
        
        # For C++, first check if this looks like raw C++ code (no markdown)
        # If so, use the specific extractor to avoid issues with _clean_code_blocks
        if compiler_id in ["G++17", "G++"]:
            # Check if response looks like raw C++ code
            response_lower = response.lower().strip()
            if (response_lower.startswith('#include') and 
                'using namespace std' in response and 
                'int main(' in response and
                '```' not in response):  # No markdown blocks
                # This looks like raw C++ code, use specific extractor
                extracted = self._extract_cpp_code(response)
                if extracted:
                    return extracted
        
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
