#!/usr/bin/env python3
"""
Command Line Interface for Jutge Problem Solver
"""

import argparse
import os
from datetime import datetime
from typing import Optional
import json
import csv

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from jutge_solver import JutgeProblemSolver, Config
from jutge_solver.benchmark import AIModelBenchmark
from jutge_solver.benchmark_config import BenchmarkConfig

console = Console()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Jutge Problem Solver - Automatically solve programming problems using OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run cli.py solve P68688_en                    # Solve Hello World problem
  uv run cli.py solve P68688_en --compiler G++17   # Use C++ compiler
  uv run cli.py solve --batch problems.txt         # Solve multiple problems
  uv run cli.py config                             # Setup configuration
  uv run cli.py benchmark hello_world              # Benchmark AI models on hello_world problem set
  uv run cli.py benchmark basic_algorithms --models GPT-4o-mini GPT-4o  # Benchmark specific models
  uv run cli.py benchmark --report html            # Generate HTML report
  uv run cli.py benchmark --parallel               # Run models in parallel for faster execution
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Solve command
    solve_parser = subparsers.add_parser('solve', help='Solve a programming problem')
    solve_parser.add_argument('problem_id', nargs='?', help='Problem ID (e.g., P68688_en)')
    solve_parser.add_argument('--compiler', '-c', help='Compiler to use (Python3, G++17, JDK)')
    solve_parser.add_argument('--batch', '-b', help='File containing list of problem IDs')
    solve_parser.add_argument('--config', help='Config file path')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Setup configuration')
    config_parser.add_argument('--interactive', '-i', action='store_true', help='Interactive setup')
    
    # Test command
    subparsers.add_parser('test', help='Test the system setup')
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark AI models on problem sets')
    benchmark_parser.add_argument('problem_set', nargs='?', help='Problem set to benchmark (hello_world, basic_algorithms, medium_problems)')
    benchmark_parser.add_argument('--models', '-m', nargs='+', help='Models to benchmark (GPT-4o-mini, GPT-4o, Claude-3.5-Sonnet)')
    benchmark_parser.add_argument('--config', help='Benchmark config file path')
    benchmark_parser.add_argument('--report', '-r', choices=['json', 'csv', 'html'], default='json', help='Report format')
    benchmark_parser.add_argument('--parallel', '-p', action='store_true', help='Run models in parallel')
    benchmark_parser.add_argument('--language', '-l', default=None, help='Programming language to use for solutions (e.g., Python3, G++17). If not specified, uses default_language from config.')
    
    args = parser.parse_args()
    
    if args.command == 'solve':
        handle_solve_command(args)
    elif args.command == 'config':
        handle_config_command(args)
    elif args.command == 'test':
        handle_test_command(args)
    elif args.command == 'benchmark':
        handle_benchmark_command(args)
    else:
        parser.print_help()


def handle_solve_command(args):
    """Handle the solve command"""
    
    # Load configuration
    config = load_config(args.config)
    if not config.validate():
        console.print("[red]Configuration validation failed. Run 'python cli.py config' to setup.[/red]")
        return
    
    # Initialize solver
    solver = JutgeProblemSolver(config)
    
    if args.batch:
        # Batch processing
        solve_batch(solver, args.batch, args.compiler)
    elif args.problem_id:
        # Single problem
        solve_single(solver, args.problem_id, args.compiler)
    else:
        # Interactive mode
        solve_interactive(solver, args.compiler)


def handle_config_command(args):
    """Handle the config command"""
    if args.interactive:
        setup_interactive_config()
    else:
        setup_default_config()


def handle_test_command(args):
    """Handle the test command"""
    console.print("[blue]Testing system setup...[/blue]")
    
    config = load_config()
    if not config.validate():
        console.print("[red]✗ Configuration is incomplete[/red]")
        return
    
    try:
        solver = JutgeProblemSolver(config)
        if solver.authenticate():
            console.print("[green]✓ Jutge authentication successful[/green]")
        else:
            console.print("[red]✗ Jutge authentication failed[/red]")
            return
        
        # Test OpenAI API
        test_response = solver.openai_client.chat.completions.create(
            model=config.openai.model,
            messages=[{"role": "user", "content": "Hello, this is a test. Respond with 'API working'."}],
            max_tokens=10
        )
        
        if "API working" in test_response.choices[0].message.content:
            console.print("[green]✓ OpenAI API connection successful[/green]")
        else:
            console.print("[yellow]⚠ OpenAI API responded but with unexpected content[/yellow]")
        
        console.print("[green]✓ All systems operational[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ System test failed: {e}[/red]")


def handle_benchmark_command(args):
    """Handle the benchmark command"""
    console.print("[blue]🔬 Starting AI Model Benchmark[/blue]")
    
    # Load configuration
    config = load_config(args.config)
    if not config.validate():
        console.print("[red]Configuration validation failed. Run 'python cli.py config' to setup.[/red]")
        return
    
    # Load benchmark configuration
    benchmark_config_path = args.config or "benchmark_config.yaml"
    benchmark_config = BenchmarkConfig.load_from_file(benchmark_config_path)
    
    # Override models if specified in command line
    if args.models:
        # Filter to only requested models
        benchmark_config.models = [m for m in benchmark_config.models if m.name in args.models]
        if not benchmark_config.models:
            console.print(f"[red]No valid models found from: {args.models}[/red]")
            return
    
    # Validate benchmark config
    if not benchmark_config.validate():
        console.print("[red]Benchmark configuration validation failed[/red]")
        return
    
    # Select problem set
    if args.problem_set:
        if args.problem_set not in benchmark_config.problem_sets:
            console.print(f"[red]Unknown problem set: {args.problem_set}[/red]")
            console.print(f"Available sets: {list(benchmark_config.problem_sets.keys())}")
            return
    else:
        # Interactive selection
        console.print("\nAvailable problem sets:")
        for name, problems in benchmark_config.problem_sets.items():
            console.print(f"  - {name}: {len(problems)} problems")
        
        args.problem_set = Prompt.ask(
            "Select problem set",
            choices=list(benchmark_config.problem_sets.keys()),
            default="basic_algorithms"
        )
    
    # Initialize benchmark with parallel support
    max_workers = 4 if args.parallel else 1
    use_processes = args.parallel
    benchmark = AIModelBenchmark(
        benchmark_config, 
        config,
        max_workers=max_workers,
        use_processes=use_processes
    )
    
    try:
        # Use default language from config if not specified
        language = args.language or benchmark_config.default_language
        
        # Run benchmark
        console.print(f"\n[blue]Running benchmark on '{args.problem_set}' problem set[/blue]")
        results = benchmark.run_benchmark(args.problem_set, language)
        
        # Display summary
        display_benchmark_summary(results)
        
        # Generate report
        if args.report == 'csv':
            generate_csv_report(results)
        elif args.report == 'html':
            generate_html_report(results)
        
    except Exception as e:
        console.print(f"[red]✗ Benchmark failed: {e}[/red]")
        import traceback
        traceback.print_exc()


def display_benchmark_summary(results: dict):
    """Display benchmark results summary in a nice table"""
    console.print("\n[bold green]Benchmark Results Summary[/bold green]")
    
    # Create summary table
    table = Table(title="Model Performance")
    table.add_column("Model", style="cyan")
    table.add_column("Problems", justify="right")
    table.add_column("Solved", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Time", justify="right")
    table.add_column("Total Tokens", justify="right")
    
    # Handle both old and new data structures for backward compatibility
    model_stats = results.get('model_stats', results.get('summary', {}).get('model_stats', {}))
    
    for model_name, stats in model_stats.items():
        success_rate = f"{stats['success_rate']:.1f}%"
        avg_time = f"{stats['avg_time_per_problem']:.2f}s"
        
        table.add_row(
            model_name,
            str(stats['total_problems']),
            str(stats['solved']),
            str(stats['failed'] + stats['errors']),
            success_rate,
            avg_time,
            str(stats['total_tokens'])
        )
    
    console.print(table)
    
    # Handle both old and new data structures for backward compatibility
    benchmark_time = results.get('benchmark_time', results.get('summary', {}).get('benchmark_time', 0))
    console.print(f"\n[dim]Total benchmark time: {benchmark_time:.2f} seconds[/dim]")


def generate_csv_report(results: dict):
    """Generate CSV report from benchmark results"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"results/benchmark_report_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Model', 'Problems', 'Solved', 'Failed', 'Success Rate', 'Avg Time', 'Total Tokens'])
        
        for model_name, stats in results['model_stats'].items():
            writer.writerow([
                model_name,
                stats['total_problems'],
                stats['solved'],
                stats['failed'] + stats['errors'],
                f"{stats['success_rate']:.1f}",
                f"{stats['avg_time_per_problem']:.2f}",
                stats['total_tokens']
            ])
    
    console.print(f"[green]✓ CSV report saved to {filename}[/green]")


def generate_html_report(results: dict):
    """Generate enhanced HTML report from benchmark results with detailed submission information"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"results/benchmark_report_{timestamp}.html"
    
    # Group individual results by model for detailed display
    results_by_model = {}
    individual_results = results.get('results', [])
    
    for result in individual_results:
        model = result.get('model_name', 'Unknown Model')
        if model not in results_by_model:
            results_by_model[model] = []
        results_by_model[model].append(result)
    
    # Extract model configurations from results
    model_configs = {}
    benchmark_config = results.get('config', {})
    
    # Get model configurations from the benchmark config if available
    for result in individual_results:
        model_name = result.get('model_name', 'Unknown Model')
        if model_name not in model_configs:
            # Try to find model config in benchmark config
            model_config = None
            if 'models' in benchmark_config:
                for model in benchmark_config['models']:
                    if model.get('name') == model_name:
                        model_config = model
                        break
            
            if model_config:
                model_configs[model_name] = {
                    'name': model_name,
                    'provider': model_config.get('provider', 'Unknown'),
                    'model_id': model_config.get('model_id', 'Unknown'),
                    'description': f"{model_config.get('provider', 'AI')} {model_config.get('model_id', 'model')} for competitive programming"
                }
            else:
                # Fallback for when config is not available
                model_configs[model_name] = {
                    'name': model_name,
                    'provider': 'Unknown',
                    'model_id': 'Unknown',
                    'description': f'AI model used for competitive programming problem solving'
                }
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jutge AI Benchmark Report</title>
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 40px; 
                background: #f8f9fa; 
                line-height: 1.6;
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 40px; 
                border-radius: 8px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #2c3e50; margin-bottom: 10px; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h3 {{ color: #2c3e50; margin-top: 30px; }}
            .meta {{ color: #7f8c8d; margin-bottom: 30px; }}
            
            /* Model Details Grid */
            .model-details-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }}
            
            .model-card {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                overflow: hidden;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            
            .model-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            }}
            
            .model-card-header {{
                padding: 20px;
                background: linear-gradient(135deg, #2c3e50, #34495e);
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .model-card-header h3 {{
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }}
            
            .success-badge {{
                background: rgba(255,255,255,0.2);
                padding: 8px 12px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            
            .high-success .success-badge {{ background: rgba(39,174,96,0.2); }}
            .medium-success .success-badge {{ background: rgba(241,196,15,0.2); }}
            .low-success .success-badge {{ background: rgba(231,76,60,0.2); }}
            
            .model-card-body {{
                padding: 20px;
            }}
            
            .model-info {{
                margin-bottom: 20px;
            }}
            
            .info-item {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                padding: 4px 0;
            }}
            
            .info-label {{
                font-weight: 600;
                color: #2c3e50;
            }}
            
            .info-value {{
                color: #7f8c8d;
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 13px;
            }}
            
            .model-stats {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 15px;
                margin-top: 15px;
            }}
            
            .stat-item {{
                text-align: center;
                padding: 10px 5px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            
            .stat-value {{
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 4px;
            }}
            
            .stat-label {{
                font-size: 12px;
                color: #7f8c8d;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            /* Summary table */
            .summary-table {{ 
                border-collapse: collapse; 
                width: 100%; 
                margin-bottom: 40px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .summary-table th {{ 
                background: linear-gradient(135deg, #3498db, #2980b9); 
                color: white; 
                padding: 15px 12px;
                text-align: left;
                font-weight: 600;
            }}
            .summary-table td {{ 
                padding: 12px; 
                border-bottom: 1px solid #ecf0f1;
            }}
            .summary-table tr:hover {{ background-color: #f8f9fa; }}
            
            /* Detailed results */
            .model-section {{ 
                margin: 40px 0; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                overflow: hidden;
            }}
            .model-header {{ 
                background: linear-gradient(135deg, #2c3e50, #34495e); 
                color: white; 
                padding: 15px 20px; 
                cursor: pointer;
                user-select: none;
            }}
            .model-header:hover {{ background: linear-gradient(135deg, #34495e, #2c3e50); }}
            .model-content {{ 
                display: none; 
                padding: 20px; 
                background: #fafbfc;
            }}
            .model-content.expanded {{ display: block; }}
            
            /* Problem results table */
            .results-table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-bottom: 20px;
                background: white;
            }}
            .results-table th {{ 
                background: #34495e; 
                color: white; 
                padding: 12px 8px; 
                text-align: left;
                font-size: 14px;
            }}
            .results-table td {{ 
                padding: 10px 8px; 
                border-bottom: 1px solid #eee; 
                vertical-align: top;
            }}
            .results-table tr:hover {{ background-color: #f1f2f6; }}
            
            /* Problem Cards */
            .problem-card {{
                background: white;
                border-radius: 8px;
                margin-bottom: 25px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border-left: 4px solid #ccc;
                overflow: hidden;
            }}
            
            .success-card {{ border-left-color: #27ae60; }}
            .failed-card {{ border-left-color: #e74c3c; }}
            .error-card {{ border-left-color: #f39c12; }}
            
            .problem-header {{
                background: #f8f9fa;
                padding: 15px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #e9ecef;
            }}
            
            .problem-header h4 {{
                margin: 0;
                color: #2c3e50;
                font-size: 16px;
            }}
            
            .problem-meta {{
                display: flex;
                gap: 10px;
                align-items: center;
            }}
            
            .verdict-badge, .time-badge, .token-badge {{
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .verdict-badge.verdict-AC {{ background: #d4edda; color: #155724; }}
            .verdict-badge.verdict-WA {{ background: #f8d7da; color: #721c24; }}
            .verdict-badge.verdict-TLE {{ background: #fff3cd; color: #856404; }}
            .verdict-badge.verdict-CE {{ background: #e2e3f1; color: #6f42c1; }}
            .verdict-badge.verdict-RE {{ background: #f5c6cb; color: #721c24; }}
            .verdict-badge.verdict-NULL {{ background: #f8f9fa; color: #6c757d; }}
            
            .time-badge {{ background: #e3f2fd; color: #0d47a1; }}
            .token-badge {{ background: #f3e5f5; color: #4a148c; }}
            
            /* Solution Section */
            .solution-section {{
                margin: 20px;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                overflow: hidden;
            }}
            
            .solution-header {{
                background: #2c3e50;
                color: white;
                padding: 12px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .solution-header h5 {{
                margin: 0;
                font-size: 14px;
                font-weight: 600;
            }}
            
            .copy-btn {{
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                transition: background-color 0.2s;
            }}
            
            .copy-btn:hover {{
                background: rgba(255,255,255,0.2);
            }}
            
            .solution-code {{
                background: #2f3542;
                padding: 0;
                max-height: 400px;
                overflow-y: auto;
            }}
            
            .solution-code pre {{
                margin: 0;
                padding: 16px;
                color: #f1f2f6;
                font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.4;
                white-space: pre-wrap;
                overflow-x: auto;
            }}
            
            .solution-code code {{
                background: none;
                color: inherit;
                padding: 0;
            }}
            
            /* Performance Section */
            .performance-section {{
                margin: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                padding: 16px;
            }}
            
            .perf-metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 12px;
            }}
            
            .perf-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
                background: white;
                border-radius: 6px;
                border-left: 3px solid #3498db;
            }}
            
            .perf-label {{
                font-size: 12px;
                color: #7f8c8d;
                font-weight: 600;
            }}
            
            .perf-value {{
                font-size: 13px;
                color: #2c3e50;
                font-weight: 600;
                font-family: 'Monaco', 'Consolas', monospace;
            }}
            
            /* Error Section */
            .error-section {{
                margin: 20px;
                background: #fff5f5;
                border: 1px solid #fed7d7;
                border-radius: 8px;
                padding: 16px;
            }}
            
            .error-section h5 {{
                margin: 0 0 10px 0;
                color: #c53030;
                font-size: 14px;
            }}
            
            .error-content {{
                color: #742a2a;
                font-size: 13px;
                line-height: 1.4;
                background: white;
                padding: 12px;
                border-radius: 4px;
                border-left: 4px solid #fc8181;
            }}
            
            /* Submission Section */
            .submission-section {{
                margin: 20px;
                background: #f7fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px;
            }}
            
            .submission-section h5 {{
                margin: 0 0 10px 0;
                color: #2d3748;
                font-size: 14px;
            }}
            
            .submission-content {{
                background: white;
                padding: 12px;
                border-radius: 4px;
                border-left: 4px solid #4299e1;
                font-size: 12px;
                max-height: 200px;
                overflow-y: auto;
            }}
            
            .submission-content pre {{
                margin: 0;
                color: #4a5568;
                font-family: 'Monaco', 'Consolas', monospace;
                white-space: pre-wrap;
            }}
            
            /* Status styling */
            .verdict-AC {{ color: #27ae60; font-weight: bold; }}
            .verdict-WA {{ color: #e74c3c; font-weight: bold; }}
            .verdict-TLE {{ color: #f39c12; font-weight: bold; }}
            .verdict-CE {{ color: #9b59b6; font-weight: bold; }}
            .verdict-RE {{ color: #e67e22; font-weight: bold; }}
            .verdict-NULL {{ color: #95a5a6; font-weight: bold; }}
            
            .success {{ color: #27ae60; font-weight: bold; }}
            .failed {{ color: #e74c3c; font-weight: bold; }}
            .warning {{ color: #f39c12; font-weight: bold; }}
            
            /* Metrics */
            .metrics {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
                gap: 10px; 
                margin: 15px 0;
                font-size: 14px;
            }}
            .metric {{ 
                background: white; 
                padding: 8px 12px; 
                border-radius: 4px; 
                border-left: 4px solid #3498db;
            }}
            .metric-label {{ font-weight: 600; color: #2c3e50; }}
            .metric-value {{ color: #7f8c8d; }}
            
            /* Utility classes */
            .toggle-all {{ 
                background: #3498db; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 5px; 
                cursor: pointer; 
                margin-bottom: 20px;
                font-size: 14px;
            }}
            .toggle-all:hover {{ background: #2980b9; }}
            
            .error-message {{ 
                background: #fee; 
                color: #c62828; 
                padding: 10px; 
                border-radius: 4px; 
                border-left: 4px solid #e53e3e; 
                margin: 10px 0;
                font-size: 14px;
            }}
        </style>
        <script>
            function toggleModel(modelId) {{
                console.log('Toggling model:', modelId);
                const content = document.getElementById(modelId);
                if (!content) {{
                    console.error('Content element not found:', modelId);
                    return;
                }}
                const header = content.previousElementSibling;
                content.classList.toggle('expanded');
                const isExpanded = content.classList.contains('expanded');
                console.log('Model expanded:', isExpanded);
                header.innerHTML = isExpanded ? 
                    header.innerHTML.replace('▶', '▼') : 
                    header.innerHTML.replace('▼', '▶');
            }}
            
            function toggleCode(codeId) {{
                console.log('Toggling code:', codeId);
                const content = document.getElementById(codeId);
                if (!content) {{
                    console.error('Code element not found:', codeId);
                    return;
                }}
                const header = content.previousElementSibling;
                content.classList.toggle('expanded');
                const isExpanded = content.classList.contains('expanded');
                header.innerHTML = isExpanded ? 
                    header.innerHTML.replace('▶', '▼') : 
                    header.innerHTML.replace('▼', '▶');
            }}
            
            function toggleAll() {{
                console.log('Toggle all clicked');
                const contents = document.querySelectorAll('.model-content');
                console.log('Found model contents:', contents.length);
                
                if (contents.length === 0) {{
                    console.warn('No model content sections found!');
                    return;
                }}
                
                const allExpanded = Array.from(contents).every(c => c.classList.contains('expanded'));
                console.log('All expanded:', allExpanded);
                
                contents.forEach((content, index) => {{
                    const header = content.previousElementSibling;
                    console.log(`Processing content ${{index}}, expanded: ${{content.classList.contains('expanded')}}`);
                    if (allExpanded) {{
                        content.classList.remove('expanded');
                        header.innerHTML = header.innerHTML.replace('▼', '▶');
                    }} else {{
                        content.classList.add('expanded');
                        header.innerHTML = header.innerHTML.replace('▶', '▼');
                    }}
                }});
                
                const toggleButton = document.querySelector('.toggle-all');
                if (toggleButton) {{
                    toggleButton.textContent = allExpanded ? 'Expand All Models' : 'Collapse All Models';
                }}
            }}
            
            // Copy code functionality
            function copyCode(codeId) {{
                const codeElement = document.getElementById(codeId);
                if (!codeElement) {{
                    console.error('Code element not found:', codeId);
                    return;
                }}
                
                const codeText = codeElement.querySelector('pre code');
                if (!codeText) {{
                    console.error('Code text not found in:', codeId);
                    return;
                }}
                
                // Create a temporary textarea to copy the text
                const textarea = document.createElement('textarea');
                textarea.value = codeText.textContent;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                
                // Show visual feedback
                const copyBtn = codeElement.parentElement.querySelector('.copy-btn');
                if (copyBtn) {{
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = '✓ Copied!';
                    copyBtn.style.background = 'rgba(39,174,96,0.3)';
                    setTimeout(() => {{
                        copyBtn.textContent = originalText;
                        copyBtn.style.background = 'rgba(255,255,255,0.1)';
                    }}, 2000);
                }}
            }}
            
            // Debug function to check DOM state
            window.debugReport = function() {{
                console.log('=== Debug Report ===');
                console.log('Model sections:', document.querySelectorAll('.model-section').length);
                console.log('Model contents:', document.querySelectorAll('.model-content').length);
                console.log('Problem cards:', document.querySelectorAll('.problem-card').length);
                console.log('Toggle button:', document.querySelector('.toggle-all'));
                document.querySelectorAll('.model-content').forEach((el, i) => {{
                    console.log(`Model content ${{i}}:`, el.id, el.classList.contains('expanded'));
                }});
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>Jutge AI Model Benchmark Report</h1>
            <div class="meta">
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Problem Set:</strong> {results.get('problem_set', 'Unknown')}</p>
                <p><strong>Total Benchmark Time:</strong> {results.get('benchmark_time', 0):.2f} seconds</p>
            </div>
            
            <h2>Model Details</h2>
            <div class="model-details-grid">
    """
    
    # Add model details cards
    for model_name, config in model_configs.items():
        # Handle both old and new data structures
        model_stats = results.get('model_stats', results.get('summary', {}).get('model_stats', {}))
        stats = model_stats.get(model_name, {})
        success_rate = stats.get('success_rate', 0)
        success_class = 'high-success' if success_rate >= 80 else 'low-success' if success_rate < 50 else 'medium-success'
        
        html_content += f"""
                <div class="model-card {success_class}">
                    <div class="model-card-header">
                        <h3>{model_name}</h3>
                        <div class="success-badge">{success_rate:.1f}%</div>
                    </div>
                    <div class="model-card-body">
                        <div class="model-info">
                            <div class="info-item">
                                <span class="info-label">Provider:</span>
                                <span class="info-value">{config['provider']}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Model ID:</span>
                                <span class="info-value">{config['model_id']}</span>
                            </div>
                        </div>
                        <div class="model-stats">
                            <div class="stat-item">
                                <div class="stat-value">{stats.get('total_problems', 0)}</div>
                                <div class="stat-label">Problems</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value success">{stats.get('solved', 0)}</div>
                                <div class="stat-label">Solved</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value failed">{stats.get('failed', 0) + stats.get('errors', 0)}</div>
                                <div class="stat-label">Failed</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">{stats.get('avg_time_per_problem', 0):.2f}s</div>
                                <div class="stat-label">Avg Time</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">{stats.get('total_tokens', 0):,}</div>
                                <div class="stat-label">Tokens</div>
                            </div>
                        </div>
                    </div>
                </div>
        """
    
    html_content += """
            </div>
            
            <h2>Performance Summary</h2>
            <table class="summary-table">
                <tr>
                    <th>Model</th>
                    <th>Problems</th>
                    <th>Solved</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                    <th>Avg Time</th>
                    <th>Total Tokens</th>
                </tr>
    """
    
    # Add summary rows
    for model_name, stats in results.get('model_stats', {}).items():
        success_class = 'success' if stats['success_rate'] >= 80 else 'failed' if stats['success_rate'] < 50 else 'warning'
        html_content += f"""
                <tr>
                    <td><strong>{model_name}</strong></td>
                    <td>{stats['total_problems']}</td>
                    <td class="success">{stats['solved']}</td>
                    <td class="failed">{stats.get('failed', 0) + stats.get('errors', 0)}</td>
                    <td class="{success_class}">{stats['success_rate']:.1f}%</td>
                    <td>{stats.get('avg_time_per_problem', 0):.2f}s</td>
                    <td>{stats.get('total_tokens', 0):,}</td>
                </tr>
        """
    
    html_content += """
            </table>
            
            <h2>Solution Details by Model</h2>
            <p>Click on any model section to view detailed solutions and submission information.</p>
    """
    
    # Only show toggle button and model sections if we have results
    if results_by_model:
        html_content += """
            <button class="toggle-all" onclick="toggleAll()">Expand All Models</button>
        """
        
        # Add detailed results for each model
        for model_name, model_results in results_by_model.items():
            model_id = model_name.replace(' ', '').replace('-', '').replace('.', '')
            success_count = sum(1 for r in model_results if r.get('verdict') == 'AC')
            html_content += f"""
            <div class="model-section">
                <div class="model-header" onclick="toggleModel('{model_id}-content')">
                    ▶ {model_name} - {success_count}/{len(model_results)} solved ({success_count/len(model_results)*100:.1f}%)
                </div>
                <div id="{model_id}-content" class="model-content">
            """
            
            # Create individual problem cards instead of a table
            for result in model_results:
                problem_id = result.get('problem_id', 'Unknown')
                verdict = result.get('verdict', 'NULL')
                verdict_class = f'verdict-{verdict}' if verdict else 'verdict-NULL'
                error_msg = result.get('error', '')
                solution_code = result.get('solution_code', '')
                
                # Determine card style based on result
                card_class = 'success-card' if verdict == 'AC' else 'error-card' if error_msg else 'failed-card'
                
                html_content += f"""
                    <div class="problem-card {card_class}">
                        <div class="problem-header">
                            <h4>Problem {problem_id}</h4>
                            <div class="problem-meta">
                                <span class="verdict-badge {verdict_class}">{verdict or 'NULL'}</span>
                                <span class="time-badge">{result.get('total_time', 0):.2f}s</span>
                                <span class="token-badge">{result.get('tokens_used', 0):,} tokens</span>
                            </div>
                        </div>
                """
                
                # Solution code section - make it prominent
                # Check for solution_code first, then fall back to code field (for Format Error cases)
                code_to_display = solution_code or result.get('code', '')
                if code_to_display:
                    code_id = f"{model_id}{problem_id}code".replace('_', '').replace('-', '')
                    # Add a note if this code failed due to format issues
                    code_header = "💡 Generated Solution"
                    if not solution_code and result.get('error') == 'Format Error':
                        code_header = "⚠️ Generated Code (Format Error)"
                    html_content += f"""
                        <div class="solution-section">
                            <div class="solution-header">
                                <h5>{code_header}</h5>
                                <button class="copy-btn" onclick="copyCode('{code_id}')">📋 Copy</button>
                            </div>
                            <div class="solution-code" id="{code_id}">
                                <pre><code>{code_to_display}</code></pre>
                            </div>
                        </div>
                    """
                
                # Performance metrics
                html_content += f"""
                        <div class="performance-section">
                            <div class="perf-metrics">
                                <div class="perf-item">
                                    <span class="perf-label">Generation Time:</span>
                                    <span class="perf-value">{result.get('generation_time', 0):.2f}s</span>
                                </div>
                                <div class="perf-item">
                                    <span class="perf-label">Submission Time:</span>
                                    <span class="perf-value">{result.get('submission_time', 0):.2f}s</span>
                                </div>
                                <div class="perf-item">
                                    <span class="perf-label">Attempts:</span>
                                    <span class="perf-value">{result.get('attempts', 1)}</span>
                                </div>
                                <div class="perf-item">
                                    <span class="perf-label">Language:</span>
                                    <span class="perf-value">{result.get('language', 'Unknown')}</span>
                                </div>
                            </div>
                        </div>
                """
                
                # Error information if present
                if error_msg:
                    html_content += f"""
                        <div class="error-section">
                            <h5>❌ Error Details</h5>
                            <div class="error-content">
                                {error_msg}
                            </div>
                        </div>
                    """
                
                # Submission details if available
                submission_details = result.get('submission_details')
                if submission_details:
                    html_content += f"""
                        <div class="submission-section">
                            <h5>🔍 Submission Details</h5>
                            <div class="submission-content">
                                <pre>{json.dumps(submission_details, indent=2)}</pre>
                            </div>
                        </div>
                    """
                
                html_content += """
                    </div>
                """
            
            html_content += """
                </div>
            </div>
            """
    else:
        html_content += """
            <p><em>No detailed results available. This may happen if the benchmark data doesn't contain individual submission results.</em></p>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(filename, 'w') as f:
        f.write(html_content)
    
    console.print(f"[green]✓ Enhanced HTML report saved to {filename}[/green]")


def solve_single(solver: JutgeProblemSolver, problem_id: str, compiler_id: Optional[str]):
    """Solve a single problem"""
    console.print(f"[bold]Solving problem: {problem_id}[/bold]")
    
    result = solver.solve_problem(problem_id, compiler_id)
    
    if result["success"]:
        console.print(f"[green]✓ Problem solved successfully![/green]")
        if "final_verdict" in result:
            console.print(f"Verdict: {result['final_verdict']}")
    else:
        console.print(f"[red]✗ Failed to solve problem: {result.get('error', 'Unknown error')}[/red]")


def solve_batch(solver: JutgeProblemSolver, batch_file: str, compiler_id: Optional[str]):
    """Solve multiple problems from a file"""
    try:
        with open(batch_file, 'r') as f:
            problem_ids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        console.print(f"[blue]Processing {len(problem_ids)} problems from {batch_file}[/blue]")
        
        results = []
        for i, problem_id in enumerate(problem_ids, 1):
            console.print(f"\\n[bold]Problem {i}/{len(problem_ids)}: {problem_id}[/bold]")
            
            result = solver.solve_problem(problem_id, compiler_id)
            results.append(result)
            
            # Brief pause between problems
            if i < len(problem_ids):
                import time
                time.sleep(2)
        
        # Summary
        console.print("\\n" + "="*60)
        console.print("[bold]BATCH SUMMARY[/bold]")
        console.print("="*60)
        
        successful = sum(1 for r in results if r["success"])
        console.print(f"Successful: {successful}/{len(results)}")
        
        for result in results:
            status = "✓" if result["success"] else "✗"
            verdict = result.get("final_verdict", "FAILED")
            console.print(f"{status} {result['problem_id']}: {verdict}")
        
    except FileNotFoundError:
        console.print(f"[red]✗ Batch file {batch_file} not found[/red]")
    except Exception as e:
        console.print(f"[red]✗ Batch processing failed: {e}[/red]")


def solve_interactive(solver: JutgeProblemSolver, compiler_id: Optional[str]):
    """Interactive problem solving"""
    console.print("[blue]Interactive mode - Enter problem IDs to solve (Ctrl+C to exit)[/blue]")
    
    try:
        while True:
            problem_id = Prompt.ask("\\nEnter problem ID")
            if not problem_id:
                continue
            
            result = solver.solve_problem(problem_id, compiler_id)
            
            if not result["success"]:
                if Confirm.ask("\\nWould you like to try another problem?"):
                    continue
                else:
                    break
            else:
                if not Confirm.ask("\\nWould you like to solve another problem?"):
                    break
                    
    except KeyboardInterrupt:
        console.print("\\n[yellow]Goodbye![/yellow]")


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from various sources"""
    if config_path:
        config = Config.load_from_file(config_path)
    else:
        config = Config.load_from_env()
    
    # Load from .env file
    config.load_env_file()
    
    # Re-apply environment variables after loading .env
    config = Config.load_from_env()
    
    return config


def setup_interactive_config():
    """Setup configuration interactively"""
    console.print("[blue]Setting up Jutge Problem Solver configuration...[/blue]")
    console.print("[dim]This will create/update your .env file with credentials[/dim]")
    
    # Check if .env exists
    env_exists = os.path.exists('.env')
    if env_exists:
        console.print("[yellow]Found existing .env file[/yellow]")
        if not Confirm.ask("Do you want to update it?"):
            return
    
    # Get OpenRouter API key
    console.print("\\n[bold]OpenRouter Configuration[/bold]")
    console.print("Get your API key from: https://openrouter.ai/")
    openai_key = Prompt.ask("Enter your OpenRouter API key", password=True)
    
    # Get Jutge credentials
    console.print("\\n[bold]Jutge Credentials[/bold]")
    console.print("Register at: https://jutge.org/")
    jutge_email = Prompt.ask("Enter your Jutge email")
    jutge_password = Prompt.ask("Enter your Jutge password", password=True)
    
    # Save to .env file
    env_content = f"""# Jutge Problem Solver Environment Variables
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# OpenRouter API Configuration
OPENROUTER_API_KEY={openai_key}

# Jutge Platform Credentials
JUTGE_EMAIL={jutge_email}
JUTGE_PASSWORD={jutge_password}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    console.print("[green]✓ Configuration saved to .env[/green]")
    console.print("[dim]Test your setup with: python cli.py test[/dim]")


def setup_default_config():
    """Setup default configuration files"""
    # Create .env.example if it doesn't exist
    if not os.path.exists('.env.example'):
        env_example_content = """# Jutge Problem Solver Environment Variables
# Copy this file to .env and fill in your actual credentials

# OpenRouter API Configuration
# Get your API key from: https://openrouter.ai/
OPENROUTER_API_KEY=your-openrouter-key-here

# Optional: Override default model
# OPENAI_MODEL=gpt-4o-mini

# Jutge Platform Credentials
# Register at: https://jutge.org/
JUTGE_EMAIL=your-email@example.com
JUTGE_PASSWORD=your-password-here
"""
        with open('.env.example', 'w') as f:
            f.write(env_example_content)
        console.print("[green]✓ Created .env.example[/green]")
    
    # Create config.yaml with non-sensitive defaults
    config = Config()
    config.save_to_file('config.yaml')
    console.print("[green]✓ Created config.yaml with default settings[/green]")
    
    console.print("\\n[blue]Next steps:[/blue]")
    console.print("1. Copy .env.example to .env")
    console.print("2. Edit .env with your credentials")
    console.print("3. Run: python cli.py test")
    console.print("\\nOr use interactive setup: python cli.py config --interactive")


if __name__ == '__main__':
    main()