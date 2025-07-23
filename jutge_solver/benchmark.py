"""
AI Model Benchmarking System for Jutge Problems
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

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
from jutge_solver import JutgeProblemSolver, Config
from jutge_solver.solution_generator import SolutionGenerator
from jutge_solver.benchmark_config import BenchmarkConfig, AIModelConfig
from jutge_solver.problem_analyzer import ProblemAnalyzer


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
            "timestamp": datetime.utcnow().isoformat()
        }


class AIModelAdapter:
    """Adapter to handle different AI model providers"""
    
    def __init__(self, model_config: AIModelConfig):
        self.config = model_config
        self.client = self._create_client()
        
    def _create_client(self):
        """Create the appropriate client based on provider"""
        if self.config.provider == "openai":
            return OpenAI(api_key=self.config.api_key)
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
        
        if self.config.provider == "openai":
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
            solution = response.choices[0].message.content
            tokens = response.usage.total_tokens
            
        elif self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system="You are an expert competitive programmer. Generate only the code solution without any explanation."
            )
            solution = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            
        elif self.config.provider == "google":
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                }
            )
            solution = response.text
            tokens = 0  # Google doesn't provide token counts directly
            
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
        
        generation_time = time.time() - start_time
        return solution, tokens, generation_time
    
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


class AIModelBenchmark:
    """Main benchmark orchestrator"""
    
    def __init__(self, benchmark_config: BenchmarkConfig, jutge_config: Config):
        self.benchmark_config = benchmark_config
        self.jutge_config = jutge_config
        self.jutge_client = JutgeApiClient()
        self.jutge_client.login(jutge_config.jutge.email, jutge_config.jutge.password)
        self.problem_analyzer = ProblemAnalyzer(self.jutge_client)
        self.results: List[BenchmarkResult] = []
        self.logger = self._setup_logger()
        
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
        
        # Run benchmarks
        for model_config in models:
            self.logger.info(f"Benchmarking model: {model_config.name}")
            self._benchmark_model(model_config, problem_ids)
        
        total_time = time.time() - start_time
        
        # Generate summary
        summary = self._generate_summary(total_time)
        
        # Save results
        self._save_results(problem_set_name)
        
        return summary
    
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
                solved = False
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
                            solved = True
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
        for model_name, stats in model_stats.items():
            stats["success_rate"] = (stats["solved"] / stats["total_problems"]) * 100 if stats["total_problems"] > 0 else 0
            stats["avg_time_per_problem"] = stats["total_time"] / stats["total_problems"] if stats["total_problems"] > 0 else 0
        
        return {
            "benchmark_time": total_time,
            "total_problems": len(set(r.problem_id for r in self.results)),
            "total_models": len(model_stats),
            "model_stats": model_stats,
            "timestamp": datetime.utcnow().isoformat()
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