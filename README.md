# Jutge Problem Solver

An automated system that reads programming problems from Jutge, generates solutions using OpenAI API, submits them, and retrieves verdicts.

## Features

- 🤖 **AI-Powered**: Uses OpenAI GPT models to generate solutions
- 🔄 **Full Workflow**: Read problem → Generate solution → Submit → Get verdict
- 🌍 **Multi-Language**: Supports Python, C++, Java, and more
- 📊 **Batch Processing**: Solve multiple problems automatically
- 🎯 **Smart Analysis**: Analyzes problems to suggest optimal approaches
- 📈 **Progress Tracking**: Comprehensive logging and progress reports

## Quick Start

### 1. Installation

```bash
# Clone and install dependencies
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configuration

#### Option A: Interactive Setup (Recommended)
```bash
uv run python cli.py config --interactive
```

#### Option B: Manual .env Setup
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add your credentials to `.env`:
```bash
# OpenAI API Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Jutge Credentials
JUTGE_EMAIL=your-email@example.com
JUTGE_PASSWORD=your-password
```

#### Option C: Default Files
```bash
# Create example files and config template
uv run python cli.py config
```

### 3. Get Your API Keys

- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Jutge Account**: Register at [Jutge.org](https://jutge.org/)

### 4. Test the Setup

```bash
uv run python test_system.py
```

### 5. Solve Your First Problem

```bash
# Solve the Hello World problem
uv run python cli.py solve P68688_en

# Use a specific compiler
uv run python cli.py solve P68688_en --compiler G++17

# Interactive mode
uv run python cli.py solve
```

## Usage Examples

### Single Problem
```bash
uv run python cli.py solve P68688_en
```

### Batch Processing
Create a file `problems.txt`:
```
P68688_en
P12345_en
P67890_ca
```

Then run:
```bash
uv run python cli.py solve --batch problems.txt
```

### Test System
```bash
uv run python cli.py test
```

## Supported Compilers

- **Python3**: Python 3 (recommended for beginners)
- **G++17**: C++17 compiler
- **JDK**: Java OpenJDK
- **And many more** (see `uv run python examples/list_available_compilers.py`)

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Problem Analyzer│    │ Solution Generator│
│                 │────│                  │────│                 │
│ • Single solve  │    │ • Parse problems │    │ • OpenAI prompts │
│ • Batch process │    │ • Extract info   │    │ • Code generation│
│ • Configuration │    │ • Suggest approach│    │ • Multi-language │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                  │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Verdict Manager │────│   Main Solver    │────│ Jutge API Client│
│                 │    │                  │    │                 │
│ • Poll verdicts │    │ • Orchestrate    │    │ • Authentication │
│ • Interpret     │    │ • Error handling │    │ • Submit code   │
│ • Retry logic   │    │ • Logging        │    │ • Get problems  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Configuration Options

### Credentials (.env file)
All sensitive credentials are stored in `.env` file:
- `OPENAI_API_KEY`: Your OpenAI API key
- `JUTGE_EMAIL`: Your Jutge account email  
- `JUTGE_PASSWORD`: Your Jutge account password
- `OPENAI_MODEL`: (Optional) Override default model

### Non-sensitive Settings (config.yaml)
Optional configuration file for non-sensitive settings:

**OpenAI Settings**
- `model`: GPT model to use (`gpt-4o-mini` for cost-effective, `gpt-4o` for best results)
- `max_tokens`: Maximum tokens per response
- `temperature`: Creativity level (0.0-1.0, lower = more deterministic)

**Jutge Settings**
- `default_compiler`: Default programming language
- `submission_timeout`: How long to wait for verdicts
- `max_retries`: Retry attempts for failed operations

**Solver Settings**
- `preferred_languages`: Languages to try in order
- `max_generation_attempts`: Solution generation retries
- `log_level`: Logging verbosity

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check your Jutge credentials in `.env`
   - Verify your account works on jutge.org

2. **OpenAI API Errors**
   - Verify your API key is correct
   - Check your OpenAI account has sufficient credits
   - Ensure API key has proper permissions

3. **Solution Generation Issues**
   - Try different GPT models
   - Adjust temperature settings
   - Check problem statement parsing

### Getting Help

1. Run system test: `uv run python test_system.py`
2. Check logs for detailed error messages
3. Verify configuration with `uv run python cli.py test`

## Cost Considerations

- **GPT-4o-mini**: ~$0.01-0.05 per problem (recommended)
- **GPT-4o**: ~$0.10-0.50 per problem (better accuracy)
- Costs vary based on problem complexity and solution length

## Examples

See the `examples/` folder for individual API usage examples that were used to build this system.

## Contributing

This is a demonstration project showing how to integrate OpenAI with competitive programming platforms. Feel free to extend and improve it!

## Security & Best Practices

### Credential Management
- **Never commit `.env` file** to version control
- Store all sensitive data in `.env` file only
- Use `.env.example` as a template for others
- Non-sensitive settings can go in `config.yaml`

### API Key Security
- Keep OpenAI API keys secure and rotate them regularly
- Monitor API usage and set billing limits
- Use separate API keys for different projects

## Legal & Ethics

- Only use on problems you're allowed to solve with AI assistance
- Respect platform terms of service  
- Use for learning and legitimate practice
- Don't violate academic integrity policies

## License

MIT License - see LICENSE file for details