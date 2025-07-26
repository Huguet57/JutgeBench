"""
AI Model Benchmarking System for Jutge Problems
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import logging
import multiprocessing as mp

import openai
from openai import OpenAI

# Optional imports for other AI providers
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    Anthropic = None

try:
    import google.generativeai as genai
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False
    genai = None

from jutge_api_client import JutgeApiClient
from jutge_solver import Config
from jutge_solver.benchmark_config import BenchmarkConfig, AIModelConfig
from jutge_solver.problem_analyzer import ProblemAnalyzer
from jutge_solver.solution_generator import SolutionGenerator


class BenchmarkResult:
    """Result of a single problem attempt"""
    def __init__(self, model_name: str, problem_id: str):
        self.model_name = model_name
        self.problem_id = problem_id
        self.verdict = None
        self.submission_id = None
        self.attempts = 0
        self.total_time = 0.0
        self.generation_time = 0.0
        self.submission_time = 0.0
        self.tokens_used = 0
        self.error = None
        self.solution_code = None
        self.language = None
        self.submission_details = None  # For storing compiler output, test case results, etc.
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "model_name": self.model_name,
            "problem_id": self.problem_id,
            "verdict": self.verdict,
            "submission_id": self.submission_id,
            "attempts": self.attempts,
            "total_time": self.total_time,
            "generation_time": self.generation_time,
            "submission_time": self.submission_time,
            "tokens_used": self.tokens_used,
            "error": self.error,
            "language": self.language,
            "success": self.verdict == "AC",
            "solution_code": self.solution_code,  # Add the generated code for debugging
            "submission_details": self.submission_details,  # Compiler output, test results, etc.
            "timestamp": datetime.now().isoformat()
        }


class AIModelAdapter:
    """Adapter for different AI model providers"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.client = self._create_client()
        # Create a SolutionGenerator instance for code extraction
        self.solution_generator = SolutionGenerator(None, None)
    
    def _create_client(self):
        """Create the appropriate client based on provider"""
        if self.config.provider == "openai":
            return OpenAI(api_key=self.config.api_key)
        elif self.config.provider == "openrouter":
            return OpenAI(api_key=self.config.api_key, base_url=self.config.base_url or "https://openrouter.ai/api/v1")
        elif self.config.provider == "anthropic":
            if not HAS_ANTHROPIC:
                raise ValueError("Anthropic library not installed. Run: pip install anthropic")
            return Anthropic(api_key=self.config.api_key)
        elif self.config.provider == "google":
            if not HAS_GOOGLE:
                raise ValueError("Google Generative AI library not installed. Run: pip install google-generativeai")
            genai.configure(api_key=self.config.api_key)
            return genai.GenerativeModel(self.config.model_id)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
    
    def generate_solution(self, problem_data: Dict[str, Any], language: str) -> Tuple[str, int, float]:
        """Generate solution using the AI model"""
        prompt = self._create_prompt(problem_data, language)
        
        start_time = time.time()
        
        if self.config.provider in {"openai", "openrouter"}:
            response = self.client.chat.completions.create(
                model=self.config.model_id,
                messages=[
                    {"role": "system", "content": "You are an expert competitive programmer. Generate only the code solution without any explanation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                timeout=self.config.timeout
            )
            raw_solution = response.choices[0].message.content
            tokens = response.usage.total_tokens
            
        elif self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system="You are an expert competitive programmer. Generate only the code solution without any explanation."
            )
            raw_solution = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            
        elif self.config.provider == "google":
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                }
            )
            raw_solution = response.text
            tokens = 0  # Google doesn't provide token counts directly
            
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
        
        # Extract clean code from the AI response
        clean_solution = self.solution_generator._extract_code(raw_solution, language)
        if not clean_solution:
            # If extraction fails, fall back to raw solution
            clean_solution = raw_solution
        
        generation_time = time.time() - start_time
        return clean_solution, tokens, generation_time
    
    def _create_prompt(self, problem_data: Dict[str, Any], language: str) -> str:
        """Create prompt for the AI model"""
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


def benchmark_single_problem(model_config: AIModelConfig, problem_id: str, jutge_config: Config, 
                            max_attempts: int, logger_name: str, raw_logging_config: Dict[str, Any] = None) -> BenchmarkResult:
    """Benchmark a single problem with a single model - designed for parallel execution"""
    # Create fresh instances for this worker
    jutge_client = JutgeApiClient()
    jutge_client.login(jutge_config.jutge.email, jutge_config.jutge.password)
    problem_analyzer = ProblemAnalyzer(jutge_client)
    
    # Create SolutionGenerator with raw logging config for this specific model
    openai_client = openai.OpenAI(
        api_key=model_config.api_key,
        base_url=model_config.base_url or "https://openrouter.ai/api/v1"
    )
    
    # Mock openai config for SolutionGenerator (it only uses model, max_tokens, temperature, timeout)
    class MockOpenAIConfig:
        def __init__(self, model_config):
            self.model = model_config.model_id
            self.max_tokens = model_config.max_tokens
            self.temperature = model_config.temperature
            self.timeout = model_config.timeout
    
    solution_generator = SolutionGenerator(openai_client, MockOpenAIConfig(model_config), raw_logging_config or {})
    
    adapter = AIModelAdapter(model_config)
    
    # Setup logger for this worker
    logger = logging.getLogger(logger_name)
    
    result = BenchmarkResult(model_config.name, problem_id)
    
    try:
        # Get problem data
        problem_info = problem_analyzer.analyze_problem(problem_id)
        if not problem_info or not problem_info.get("success"):
            raise Exception(f"Failed to fetch problem {problem_id}")
        
        problem_data = problem_info
        
        # Attempt to solve
        for attempt in range(max_attempts):
            result.attempts = attempt + 1
            
            try:
                # Generate solution using SolutionGenerator (with raw response logging)
                start_time = time.time()
                generation_result = solution_generator.generate_solution(problem_data, "Python3", attempt + 1)
                gen_time = time.time() - start_time
                
                if not generation_result.get("success"):
                    raise Exception(f"Solution generation failed: {generation_result.get('error', 'Unknown error')}")
                
                result.solution_code = generation_result["code"]
                result.tokens_used = generation_result["token_usage"]["total_tokens"]
                result.generation_time = gen_time
                result.language = "Python3"
                
                # Submit solution with retry logic for server errors
                submission_start = time.time()
                submission_retries = 0
                max_submission_retries = 3
                
                while submission_retries < max_submission_retries:
                    try:
                        submission_id = jutge_client.student.submissions.submit(
                            problem_id, 
                            "Python3",
                            solution,
                            f"Benchmark test by {model_config.name}"
                        )
                        result.submission_time = time.time() - submission_start
                        result.submission_id = submission_id
                        break  # Success, exit retry loop
                        
                    except Exception as submit_error:
                        submission_retries += 1
                        error_str = str(submit_error)
                        
                        # Check if it's a rate limit error (UNREPORTED_ERROR) that needs longer wait
                        if "UNREPORTED_ERROR" in error_str or "An error occurred" in error_str:
                            wait_time = min(5 * submission_retries, 30)  # Exponential backoff: 5s, 10s, 15s (max 30s)
                            logger.warning(f"Jutge rate limit detected on attempt {submission_retries}: {error_str}")
                            if submission_retries < max_submission_retries:
                                logger.info(f"Waiting {wait_time}s before retry due to rate limiting...")
                                time.sleep(wait_time)
                                continue
                            else:
                                logger.error(f"Max retries reached for {problem_id} after rate limiting: {error_str}")
                        
                        # For other errors or max retries reached, record and raise
                        result.error = f"Submission failed: {error_str}"
                        result.submission_details = {"error_type": "submission_error", "details": error_str}
                        raise submit_error
                
                # Wait for verdict
                verdict = _wait_for_verdict_standalone(jutge_client, problem_id, submission_id, logger)
                result.verdict = verdict
                
                # Try to get additional submission details
                try:
                    state = jutge_client.student.submissions.get(problem_id, submission_id)
                    if hasattr(state, '__dict__'):
                        details = {}
                        for attr in ['compiler_output', 'execution_time', 'memory_usage', 'test_results']:
                            if hasattr(state, attr):
                                details[attr] = getattr(state, attr)
                        if details:
                            result.submission_details = details
                except Exception as e:
                    logger.debug(f"Could not fetch submission details: {e}")
                
                if verdict == "AC":
                    break
                    
            except Exception as e:
                logger.error(f"Problem {problem_id} attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    result.error = str(e)
        
        result.total_time = result.generation_time + result.submission_time
        logger.info(f"Problem {problem_id} result: {result.verdict} ({result.attempts} attempts, {result.total_time:.2f}s)")
        
    except Exception as e:
        logger.error(f"Failed to benchmark problem {problem_id}: {e}")
        result.error = str(e)
        result.verdict = "ERROR"
    
    return result


def _wait_for_verdict_standalone(jutge_client: JutgeApiClient, problem_id: str, 
                                submission_id: str, logger: logging.Logger, timeout: int = 60) -> str:
    """Wait for submission verdict - standalone version for parallel execution"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            state = jutge_client.student.submissions.get(problem_id, submission_id)
            
            # Check if submission is done
            if hasattr(state, 'state') and state.state == "done":
                # Try different possible verdict attribute names
                if hasattr(state, 'veredict'):
                    return state.veredict
                elif hasattr(state, 'verdict'):
                    return state.verdict
                else:
                    logger.warning(f"Submission done but no verdict found in state object")
                    return "NO_VERDICT"
            
            # Log current state for debugging
            current_state = getattr(state, 'state', 'unknown')
            logger.debug(f"Submission {submission_id} state: {current_state}")
                
        except Exception as e:
            logger.error(f"Error checking submission status: {e}")
            # Don't give up immediately on errors
            
        time.sleep(2)
    
    logger.warning(f"Verdict polling timeout for submission {submission_id}")
    return "TIMEOUT"


class AIModelBenchmark:
    """Main benchmark orchestrator"""
    
    def __init__(self, benchmark_config: BenchmarkConfig, jutge_config: Config, 
                 max_workers: Optional[int] = None, use_processes: bool = True):
        self.benchmark_config = benchmark_config
        self.jutge_config = jutge_config
        self.jutge_client = JutgeApiClient()
        self.jutge_client.login(jutge_config.jutge.email, jutge_config.jutge.password)
        self.problem_analyzer = ProblemAnalyzer(self.jutge_client)
        self.results: List[BenchmarkResult] = []
        self.logger = self._setup_logger()
        
        # Parallelization settings
        self.max_workers = max_workers or min(mp.cpu_count(), 8)  # Cap at 8 to avoid overwhelming the API
        self.use_processes = use_processes
        
    def _setup_logger(self) -> logging.Logger:
        """Setup benchmark logger"""
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        
        logger = logging.getLogger("benchmark")
        log_filename = os.path.join("results", f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
        
    def run_benchmark(self, problem_set_name: str) -> Dict[str, Any]:
        """Run benchmark for a specific problem set"""
        problem_ids = self.benchmark_config.problem_sets.get(problem_set_name, [])
        if not problem_ids:
            raise ValueError(f"Problem set '{problem_set_name}' not found")
        
        models = self.benchmark_config.get_enabled_models()
        if not models:
            raise ValueError("No enabled models found")
        
        self.logger.info(f"Starting benchmark for problem set: {problem_set_name}")
        self.logger.info(f"Problems: {problem_ids}")
        self.logger.info(f"Models: {[m.name for m in models]}")
        
        start_time = time.time()
        
        # Jutge authentication already done in __init__
        
        # Run benchmarks in parallel
        self.logger.info(f"Running benchmarks with {self.max_workers} workers using {'processes' if self.use_processes else 'threads'}")
        if self.benchmark_config.parallel_strategy == "full":
            self._benchmark_models_parallel(models, problem_ids)
        elif self.benchmark_config.parallel_strategy == "models":
            self._benchmark_models_sequential_problems_parallel(models, problem_ids)
        else:  # sequential fallback
            for model_config in models:
                self.logger.info(f"Benchmarking model: {model_config.name}")
                self._benchmark_model(model_config, problem_ids)
        
        total_time = time.time() - start_time
        
        # Generate summary
        summary = self._generate_summary(total_time)
        
        # Create full results data structure for HTML generation
        full_results = {
            "problem_set": problem_set_name,
            "config": self.benchmark_config.model_dump(),
            "results": [r.to_dict() for r in self.results],
            "summary": summary,
            "benchmark_time": total_time
        }
        
        # Save results
        self._save_results(problem_set_name)
        
        return full_results
    
    def _benchmark_models_parallel(self, models: List[AIModelConfig], problem_ids: List[str]) -> None:
        """Benchmark all models on all problems in parallel"""
        # Create all (model, problem) pairs
        tasks = []
        for model_config in models:
            for problem_id in problem_ids:
                tasks.append((model_config, problem_id))
        
        self.logger.info(f"Created {len(tasks)} benchmark tasks")
        
        # Choose executor based on configuration
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {}
            for model_config, problem_id in tasks:
                # Raw logging config from benchmark config
                raw_logging_config = {
                    'save_raw_responses': self.benchmark_config.save_raw_responses,
                    'raw_responses_dir': self.benchmark_config.raw_responses_dir,
                    'save_raw_on_failure_only': self.benchmark_config.save_raw_on_failure_only
                }
                
                future = executor.submit(
                    benchmark_single_problem,
                    model_config,
                    problem_id,
                    self.jutge_config,
                    self.benchmark_config.max_attempts_per_problem,
                    f"benchmark.{model_config.name}",
                    raw_logging_config
                )
                future_to_task[future] = (model_config.name, problem_id)
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                model_name, problem_id = future_to_task[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    self.logger.info(f"Completed {model_name} on {problem_id}: {result.verdict}")
                except Exception as e:
                    self.logger.error(f"Task {model_name}/{problem_id} failed: {e}")
                    # Create error result
                    error_result = BenchmarkResult(model_name, problem_id)
                    error_result.error = str(e)
                    error_result.verdict = "ERROR"
                    self.results.append(error_result)
    
    def _benchmark_models_sequential_problems_parallel(self, models: List[AIModelConfig], problem_ids: List[str]) -> None:
        """Benchmark models sequentially, but problems within each model in parallel"""
        for model_config in models:
            self.logger.info(f"Benchmarking model: {model_config.name}")
            self._benchmark_model_parallel(model_config, problem_ids)
    
    def _benchmark_model_parallel(self, model_config: AIModelConfig, problem_ids: List[str]) -> None:
        """Benchmark a single model on all problems in parallel"""
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all problems for this model
            future_to_problem = {}
            for problem_id in problem_ids:
                # Raw logging config from benchmark config
                raw_logging_config = {
                    'save_raw_responses': self.benchmark_config.save_raw_responses,
                    'raw_responses_dir': self.benchmark_config.raw_responses_dir,
                    'save_raw_on_failure_only': self.benchmark_config.save_raw_on_failure_only
                }
                
                future = executor.submit(
                    benchmark_single_problem,
                    model_config,
                    problem_id,
                    self.jutge_config,
                    self.benchmark_config.max_attempts_per_problem,
                    f"benchmark.{model_config.name}",
                    raw_logging_config
                )
                future_to_problem[future] = problem_id
            
            # Collect results as they complete
            for future in as_completed(future_to_problem):
                problem_id = future_to_problem[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    self.logger.info(f"  Problem {problem_id}: {result.verdict} ({result.attempts} attempts, {result.total_time:.2f}s)")
                except Exception as e:
                    self.logger.error(f"  Problem {problem_id} failed: {e}")
                    # Create error result
                    error_result = BenchmarkResult(model_config.name, problem_id)
                    error_result.error = str(e)
                    error_result.verdict = "ERROR"
                    self.results.append(error_result)
    
    def _benchmark_model(self, model_config: AIModelConfig, problem_ids: List[str]) -> None:
        """Benchmark a single model on all problems"""
        adapter = AIModelAdapter(model_config)
        
        for problem_id in problem_ids:
            self.logger.info(f"  Problem {problem_id}")
            result = BenchmarkResult(model_config.name, problem_id)
            
            try:
                # Get problem data
                problem_info = self.problem_analyzer.analyze_problem(problem_id)
                if not problem_info or not problem_info.get("success"):
                    raise Exception(f"Failed to fetch problem {problem_id}")
                
                problem_data = problem_info  # Use the analyzed problem info
                
                # Attempt to solve
                for attempt in range(self.benchmark_config.max_attempts_per_problem):
                    result.attempts = attempt + 1
                    
                    try:
                        # Generate solution
                        solution, tokens, gen_time = adapter.generate_solution(problem_data, "Python3")
                        result.solution_code = solution
                        result.tokens_used = tokens
                        result.generation_time = gen_time
                        result.language = "Python3"
                        
                        # Submit solution
                        submission_start = time.time()
                        submission_id = self.jutge_client.student.submissions.submit(
                            problem_id, 
                            "Python3",
                            solution,
                            f"Benchmark test by {model_config.name}"
                        )
                        result.submission_time = time.time() - submission_start
                        result.submission_id = submission_id
                        
                        # Wait for verdict
                        verdict = self._wait_for_verdict(problem_id, submission_id)
                        result.verdict = verdict
                        
                        if verdict == "AC":
                            break
                            
                    except Exception as e:
                        self.logger.error(f"    Attempt {attempt + 1} failed: {e}")
                        if attempt == self.benchmark_config.max_attempts_per_problem - 1:
                            result.error = str(e)
                
                result.total_time = result.generation_time + result.submission_time
                self.logger.info(f"    Result: {result.verdict} ({result.attempts} attempts, {result.total_time:.2f}s)")
                
            except Exception as e:
                self.logger.error(f"    Failed to benchmark: {e}")
                result.error = str(e)
                result.verdict = "ERROR"
            
            self.results.append(result)
    
    def _wait_for_verdict(self, problem_id: str, submission_id: str, timeout: int = 60) -> str:
        """Wait for submission verdict"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Get submission status
                state = self.jutge_client.student.submissions.get(problem_id, submission_id)
                
                if state.state == "done":
                    return state.veredict  # Note: 'veredict' is the actual field name in the API
                    
            except Exception as e:
                self.logger.error(f"Error checking submission status: {e}")
                
            time.sleep(2)
        
        return "TIMEOUT"
    
    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate benchmark summary statistics"""
        model_stats = {}
        
        for result in self.results:
            if result.model_name not in model_stats:
                model_stats[result.model_name] = {
                    "total_problems": 0,
                    "solved": 0,
                    "failed": 0,
                    "errors": 0,
                    "total_time": 0,
                    "total_tokens": 0,
                    "verdicts": {}
                }
            
            stats = model_stats[result.model_name]
            stats["total_problems"] += 1
            stats["total_time"] += result.total_time
            stats["total_tokens"] += result.tokens_used
            
            if result.verdict == "AC":
                stats["solved"] += 1
            elif result.error:
                stats["errors"] += 1
            else:
                stats["failed"] += 1
            
            stats["verdicts"][result.verdict] = stats["verdicts"].get(result.verdict, 0) + 1
        
        # Calculate success rates
        for stats in model_stats.values():
            stats["success_rate"] = (stats["solved"] / stats["total_problems"]) * 100 if stats["total_problems"] > 0 else 0
            stats["avg_time_per_problem"] = stats["total_time"] / stats["total_problems"] if stats["total_problems"] > 0 else 0
        
        return {
            "benchmark_time": total_time,
            "total_problems": len(set(r.problem_id for r in self.results)),
            "total_models": len(model_stats),
            "model_stats": model_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def _save_results(self, problem_set_name: str) -> None:
        """Save benchmark results to file"""
        # Ensure results directory exists
        os.makedirs("results", exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join("results", f"benchmark_results_{problem_set_name}_{timestamp}.json")
        
        data = {
            "problem_set": problem_set_name,
            "config": self.benchmark_config.model_dump(),
            "results": [r.to_dict() for r in self.results],
            "summary": self._generate_summary(0)
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Results saved to {filename}") 