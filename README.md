# Digdag Viz

**Turn your Treasure Data workflows into beautiful, interactive visualizations in seconds.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

![Workflow Visualization Example](docs/example-graph.png)

## Why Use This Tool?

- 📊 **Understand Complex Workflows**: See the entire workflow structure at a glance
- 🔍 **Debug Faster**: Identify task dependencies and execution flow visually
- 📝 **Auto-Documentation**: Generate always-up-to-date workflow documentation
- 🎨 **Interactive UI**: Click tasks to view SQL queries, parameters, and schedules
- 🚀 **Zero Configuration**: Works out of the box with your existing `.dig` files

## Quick Start (30 Seconds)

```bash
# 1. Install
git clone https://github.com/yourname/digdag-viz.git
cd digdag-viz
pip install -e .

# 2. Visualize your workflows
digdag-viz /path/to/your/workflows --outdir output

# 3. Open the result
open output/index.html
```

That's it! You'll see an interactive dashboard with all your workflows.

## What You Get

### 📊 Interactive Workflow Graphs
- **Interactive Visualization**: Pan, zoom, and explore complex workflow graphs.
- **Data Lineage (Experimental)**: Trace table dependencies across your entire data pipeline. [Learn more](wiki/Data-Lineage.md).
- **Search & Filter**: Instantly find tasks and filter by status or name.
- Color-coded tasks by operator type (`td>`, `sh>`, `py>`, etc.)
- Click any task to see details: SQL queries, parameters, schedules
- Hover to highlight dependencies (upstream/downstream)
- Search and filter tasks
- Deep links to focused nodes (Copy Link) and a guided tour (beta)

### 📅 Schedule Overview
- All scheduled workflows in one table
- Filter by project, search by name
- See cron schedules and timezones at a glance

### 🔗 SQL Query Viewer
- Syntax-highlighted SQL with proper formatting (offline-friendly)
- Direct links from workflow tasks to query files
- "Back to workflow" navigation

### 🧠 AI Context Pack
- **context.json** for tooling and programmatic use
- **context.toon** for LLM-friendly ingestion (token-efficient, tabular)
- Includes workflows, schedules, lineage tables, SQL paths, and unresolved template warnings

### 📴 Offline-Ready
- All HTML artifacts are self-contained (no external assets)

### 📁 Project Organization
- Supports single projects or workspace with multiple projects
- Automatic project detection and grouping
- Separate pages for scheduled vs. unscheduled workflows

## Installation

### Prerequisites
```bash
# Install Graphviz (required for graph rendering)
# macOS:
brew install graphviz

# Ubuntu/Debian:
sudo apt-get install graphviz

# Windows:
# Download from https://graphviz.org/download/
```

### Option 1: Install from Source (Recommended)
```bash
git clone https://github.com/yourname/digdag-viz.git
cd digdag-viz
pip install -e .
```

### Option 2: Install Dependencies Only
```bash
git clone https://github.com/yourname/digdag-viz.git
cd digdag-viz
pip install -r requirements.txt
```

### Verify Installation
```bash
# Check version
digdag-viz --version

# Run example
digdag-viz example --outdir output
open output/index.html
```

## Usage Examples

### Visualize a Single Project
```bash
python digdag-viz ./my-project --outdir graphs
```

### Visualize Multiple Projects (Workspace)
```bash
python digdag-viz ./projects --outdir graphs
# Automatically detects all projects in subdirectories
```

### Custom Output Format
```bash
# Generate PNG images instead of SVG
python digdag-viz ./workflows --outdir graphs --format png
```

### Exclude Test Workflows
```bash
python digdag-viz ./workflows --outdir graphs \
  --exclude "**/test_*.dig" \
  --exclude "**/.archive/**"
```

### Verbose Output (for debugging)
```bash
python digdag-viz ./workflows --outdir graphs --verbose
```

## Command-Line Options

```
usage: digdag-viz [-h] [--outdir OUTDIR] [--format {svg,png,pdf}]
                    [--config CONFIG] [--no-schedule]
                    [--exclude EXCLUDE_PATTERNS] [--include-only INCLUDE_PATTERNS]
                    [--direction {LR,TB,RL,BT}] [--max-depth MAX_DEPTH]
                    [--template-dir TEMPLATE_DIR] [--verbose] [--quiet]
                    path

positional arguments:
  path                  Path to .dig file or directory containing workflows

optional arguments:
  --outdir OUTDIR       Output directory (default: graphs)
  --format {svg,png,pdf}
                        Graph output format (default: svg)
  --config CONFIG       Path to configuration file (.digdag-graph.yml)
  --no-schedule         Skip schedule page generation
  --exclude EXCLUDE_PATTERNS
                        Exclude patterns (glob format, can be used multiple times)
  --include-only INCLUDE_PATTERNS
                        Include only matching patterns
  --direction {LR,TB,RL,BT}
                        Graph direction: LR=Left-Right, TB=Top-Bottom (default: LR)
  --max-depth MAX_DEPTH
                        Maximum task nesting depth to visualize
  --template-dir TEMPLATE_DIR
                        Custom template directory for HTML pages
  --verbose, -v         Verbose output for debugging
  --quiet, -q           Minimal output (errors only)
```

## Configuration File

Create `.digdag-graph.yml` in your project root for persistent settings:

```yaml
output:
  directory: graphs
  format: svg

graph:
  direction: LR
  max_depth: 5
  include_schedule: true

filters:
  exclude_patterns:
    - "**/test_*.dig"
    - "**/.archive/**"
    - "**/.backup/**"

styling:
  node_colors:
    default: "#e8f0fe"
    td>: "#b2dfdb"
    sh>: "#bbdefb"
    py>: "#ffccbc"
```

Then simply run:
```bash
python digdag-viz ./workflows
```

## Documentation

For detailed guides, see:

- **[Configuration Guide](docs/configuration.md)** - Complete configuration options, environment variables, and examples
- **[GitHub Actions Integration](docs/github-actions.md)** - Step-by-step guide for CI/CD integration with examples

## Supported Digdag Operators

✅ **Fully Supported:**
- `td>` - Treasure Data queries (with SQL viewer)
- `sh>` - Shell commands
- `py>` - Python scripts
- `rb>` - Ruby scripts
- `echo>` - Echo operator
- `call>` - Call other workflows (with navigation links)
- `require>` - Require workflows
- `loop>`, `for_each>`, `for_range>` - Loop constructs
- `if>` - Conditional execution
- `_parallel` - Parallel task execution

## Troubleshooting

### "Command not found: graphviz"
**Solution**: Install Graphviz system dependency (see Installation section)

### "No workflow documents found"
**Solution**: Ensure you're pointing to a directory containing `.dig` files
```bash
# Check if .dig files exist
find /path/to/workflows -name "*.dig"
```

### "Failed to render graph"
**Solution**: Run with `--verbose` to see detailed error messages
```bash
python digdag-viz ./workflows --outdir graphs --verbose
```

### Workflows not showing in scheduled page
**Solution**: Ensure your workflow has a `_schedule` section:
```yaml
_schedule:
  cron: "0 0 * * *"
  timezone: UTC
```

## Advanced Features

### CI/CD Integration
 
 #### GitHub Actions
 
 **Option 1: Use the Action (Recommended)**
 ```yaml
 name: Visualize Workflows
 
 on:
   push:
     paths: ['**/*.dig']
 
 jobs:
   visualize:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       
       - name: Generate workflow graphs
         uses: yourname/digdag-viz@v2
         with:
           workflow-path: '.'
           output-dir: 'docs/graphs'
       
       - name: Deploy to GitHub Pages
         uses: peaceiris/actions-gh-pages@v3
         with:
           github_token: ${{ secrets.GITHUB_TOKEN }}
           publish_dir: ./docs/graphs
 ```
 
 **Option 2: Manual Installation**
 ```yaml
 - name: Set up Python
   uses: actions/setup-python@v4
   with:
     python-version: '3.11'
 
 - name: Install Graphviz
   run: sudo apt-get install -y graphviz
 
 - name: Install digdag-viz
   run: pip install .
 
 - name: Generate graphs
   run: digdag-viz . --outdir docs/graphs
 ```
 
 #### GitLab CI
 
 Add to `.gitlab-ci.yml`:
 ```yaml
 visualize:
   image: python:3.11-slim
   before_script:
     - apt-get update && apt-get install -y graphviz
     - pip install .
   script:
     - digdag-viz . --outdir public
   artifacts:
     paths:
       - public
 ```
 
 ### Docker Support
 
 ```bash
 # Build image
 docker build -t digdag-viz .
 
 # Run
 docker run -v $(pwd)/workflows:/workflows -v $(pwd)/graphs:/output \
   digdag-viz /workflows --outdir /output
 ```

## Project Structure

```
your-project/
├── workflows/              # Your .dig files
│   ├── daily_import.dig
│   ├── weekly_report.dig
│   └── queries/
│       ├── import.sql
│       └── report.sql
└── graphs/                 # Generated output
    ├── index.html          # Main dashboard
    ├── scheduled_workflows.html
    ├── unscheduled_workflows.html
    ├── daily_import.html   # Interactive graph
    ├── weekly_report.html
    ├── context.json        # AI context pack (JSON)
    ├── context.toon        # AI context pack (TOON)
    └── queries/            # SQL viewers
        ├── import.html
        └── report.html
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourname/digdag-viz/issues)
- **Documentation**: [Wiki](https://github.com/yourname/digdag-viz/wiki)
- **Treasure Data Support**: Contact your account team

## Acknowledgments

- Original inspiration: [y-abe/digdag-graph](https://github.com/y-abe/digdag-graph)
- Built for [Treasure Data](https://www.treasuredata.com/) customers
- Powered by [Graphviz](https://graphviz.org/) and vanilla JS for interaction
