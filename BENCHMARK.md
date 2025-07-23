# AI Model Benchmarking for Jutge Problems

The benchmark feature allows you to compare the performance of different AI models on solving Jutge programming problems.

## Quick Start

1. Install the benchmark dependencies:
```bash
uv sync --extra benchmark
```

2. Set up your API keys:
```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"  # Optional
export GOOGLE_API_KEY="your-google-key"        # Optional
```

3. Run a benchmark:
```bash
# Benchmark on hello_world problems
uv run python cli.py benchmark hello_world

# Benchmark specific models
uv run python cli.py benchmark basic_algorithms --models GPT-4o-mini GPT-4o

# Generate an HTML report
uv run python cli.py benchmark medium_problems --report html
```

## Configuration

The benchmark system uses a configuration file (`benchmark_config.yaml`) to define:
- Available AI models and their settings
- Problem sets for testing
- Benchmark parameters

### Default Problem Sets

- **hello_world**: Single problem to test basic functionality
- **basic_algorithms**: 5 simple algorithmic problems
- **medium_problems**: 10 problems of moderate difficulty
- **advanced_problems**: 10 challenging problems

### Adding New Models

Edit `benchmark_config.yaml` to add new AI models:

```yaml
models:
  - name: "Your-Model-Name"
    provider: "openai"  # or "anthropic", "google"
    model_id: "model-api-id"
    api_key: null  # Uses environment variable
    max_tokens: 2000
    temperature: 0.1
    timeout: 30
    enabled: true
```

### Custom Problem Sets

Add your own problem sets in `benchmark_config.yaml`:

```yaml
problem_sets:
  my_custom_set:
    - "P12345_en"  # Problem ID 1
    - "P67890_en"  # Problem ID 2
```

## Output

The benchmark generates:
- Console output with a summary table
- Detailed logs in `benchmark_YYYYMMDD_HHMMSS.log`
- Result files in JSON format
- Optional CSV or HTML reports

### Metrics Tracked

- **Success Rate**: Percentage of problems solved correctly (AC verdict)
- **Average Time**: Mean time per problem (generation + submission)
- **Token Usage**: Total tokens consumed by the model
- **Verdict Distribution**: Breakdown of all verdicts received

## Tips

1. Start with `hello_world` to verify your setup
2. Use `basic_algorithms` for a quick benchmark
3. The `medium_problems` set provides a good balance for comparison
4. Enable only the models you want to test to save time and API costs
5. Review the detailed logs for debugging failed solutions 