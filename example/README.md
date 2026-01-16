# Comprehensive Example Project

This example demonstrates **all features** of digdag-viz including workflow visualization, data lineage tracking, and various operator types.

## 🚀 Quick Start

```bash
# From the repository root:
digdag-viz example --outdir example-output

# Open the result:
open example-output/index.html
```

## 📋 What's Included

### Workflows

1. **`etl_pipeline.dig`** - Scheduled Daily ETL Pipeline
   - **Schedule**: Daily at 2 AM PST
   - **Demonstrates**: Complete data pipeline with lineage, retries, error handling
   - **Operators**: `td>`, `sh>`, `echo>`, `http_call>`
   - **Data Flow**: Source → Staging → Golden
   
2. **`adhoc_analysis.dig`** - Unscheduled Analysis Workflow
   - **Schedule**: None (manual execution)
   - **Demonstrates**: Parallel execution, branching, Ruby and Python operators
   - **Operators**: `td>`, `py>`, `rb>`, `sh>`, `echo>`, `for_each>`, `if>`
   - **Features**: Parallel task execution, conditional publish
   
3. **`hourly_sync.dig`** - High-Frequency Data Sync
   - **Schedule**: Hourly
   - **Demonstrates**: Frequent updates, retries, loops
   - **Operators**: `td>`, `sh>`, `echo>`, `loop>`, `http_call>`
   - **Pattern**: Incremental data loading with polling

4. **`daily_processing.dig`** - Simple ETL (Original Example)
   - **Schedule**: Daily at 2 AM UTC
   - **Demonstrates**: Basic workflow structure with branching
   - **Operators**: `td>`, `sh>`, `echo>`, `if>`

5. **`orchestrator.dig`** - Weekly Orchestration
   - **Schedule**: Weekly (Mondays)
   - **Demonstrates**: Cross-workflow orchestration
   - **Operators**: `call>`, `require>`, `if>`, `sh>`, `echo>`

6. **`backfill_outliers.dig`** - Outliers and Backfills
   - **Schedule**: None (manual execution)
   - **Demonstrates**: `for_range>`, `for_each>`, inline SQL, `!include`
   - **Operators**: `td>`, `sh>`, `echo>`, `http_call>`, `for_range>`, `for_each>`

### Data Lineage

The example creates a complete data pipeline demonstrating lineage tracking:

```
Source Layer (src_raw)
  ├── events
  ├── users
  └── clickstream_events
       ↓
Staging Layer (staging)
  ├── events_cleaned
  ├── users_enriched
  ├── clickstream_aggregated
  ├── region_counts
  ├── backfill_partitions
  └── analysis_prep
       ↓
Golden Layer (golden)
  ├── user_activity_daily
  ├── segment_summary
  └── analysis_results
```

### SQL Queries

All SQL files are in the `queries/` directory:

**Source Extraction:**
- `extract_events.sql` - Extract raw events
- `extract_users.sql` - Extract user data
- `sync_clickstream.sql` - Hourly clickstream sync

**Staging Transformations:**
- `stage_events.sql` - Clean and standardize events
- `stage_users.sql` - Enrich user data
- `update_staging_clickstream.sql` - Aggregate clickstream
- `prepare_analysis.sql` - Prepare analysis data
- `backfill_partition.sql` - Backfill partitions

**Golden Tables:**
- `create_user_activity.sql` - Create user activity summary
- `consolidate.sql` - Consolidate analysis results
- `segment_analysis.sql` - Segment rollups

**Legacy:**
- `extract.sql` - Original extract query
- `transform.sql` - Original transform query

## 🎯 Expected Output

Running `digdag-viz example` will generate:

### Main Pages
- **`index.html`** - Dashboard with all workflows
- **`scheduled_workflows.html`** - Scheduled workflows (4 workflows)
- **`unscheduled_workflows.html`** - Unscheduled workflows (2 workflows)
- **`lineage.html`** - Data lineage overview
- **`context.json`** - AI context pack (JSON)
- **`context.toon`** - AI context pack (TOON)

### Workflow Graphs
- `etl_pipeline.html` - Interactive ETL pipeline graph
- `adhoc_analysis.html` - Analysis workflow with parallel tasks
- `hourly_sync.html` - Hourly sync workflow
- `daily_processing.html` - Simple ETL workflow
- `orchestrator.html` - Cross-workflow orchestration
- `backfill_outliers.html` - Backfills and outliers

### Lineage Graphs
- `lineage/full_lineage.html` - Complete data flow visualization
- `lineage/src_raw_events.html` - Individual table lineage
- `lineage/staging_events_cleaned.html` - Staging table lineage
- `lineage/golden_user_activity_daily.html` - Golden table lineage
- ... (one for each table)

### SQL Viewers
- `queries/extract_events.html` - Syntax-highlighted SQL
- `queries/stage_events.html` - SQL with lineage info
- ... (one for each SQL file)

## 🔍 Features to Explore

### 1. Workflow Visualization
- **Color-coded tasks** by operator type
- **Interactive graphs** with zoom and pan
- **Task dependencies** clearly shown
- **Parallel execution** visualization

### 2. Data Lineage
- **Left-to-right flow**: Source → Staging → Golden
- **Interactive highlighting**: Hover to see dependencies
- **Search functionality**: Filter by table name
- **Database filter**: View specific database tables
- **Clickable nodes**: Navigate to table details

### 3. Schedule Management
- **Scheduled workflows**: View cron schedules
- **Unscheduled workflows**: Manual execution workflows
- **Timezone display**: Clear schedule information

### 4. SQL Exploration
- **Syntax highlighting**: Easy-to-read SQL
- **Lineage tracking**: See source and target tables
- **Query organization**: Grouped by workflow

## 📊 Lineage Visualization Features

### Full Lineage Graph
- Multiple tables across all layers
- **Database filter dropdown** - Filter by `src_raw`, `staging`, or `golden`
- **Search box** - Find tables by name
- **Hover highlighting** - See upstream (red) and downstream (cyan) dependencies
- **Color coding**:
  - 🟠 Orange = Source tables
  - 🔵 Blue = Staging tables
  - 🟢 Green = Golden tables

### Individual Table Lineage
- Click any table to see its specific lineage
- View upstream sources and downstream consumers
- Navigate between related tables

## 🎨 Operator Types Demonstrated

| Operator | Example | Description |
|----------|---------|-------------|
| `td>` | Extract, transform, load | Treasure Data SQL queries |
| `sh>` | Export scripts | Shell commands |
| `py>` | Analysis scripts | Python functions |
| `rb>` | Cleanup scripts | Ruby scripts |
| `echo>` | Notifications | Simple messages |
| `call>` | Orchestration | Call workflows |
| `require>` | Dependencies | Require workflows |
| `for_each>` | Fan-out | Region or segment loops |
| `for_range>` | Backfills | Numeric loops |
| `if>` | Branching | Conditional steps |
| `loop>` | Polling | Loop with backoff |
| `http_call>` | Webhooks | HTTP notifications |

## 🔄 Workflow Patterns

### Sequential Execution
```yaml
+step1:
  td>: query1.sql
+step2:
  td>: query2.sql
```

### Parallel Execution
```yaml
+parallel_tasks:
  _parallel: true
  +task1:
    py>: script1
  +task2:
    py>: script2
```

### Data Pipeline
```yaml
+extract:
  td>: extract.sql
  create_table: src_raw.data
+transform:
  td>: transform.sql
  create_table: staging.data_clean
+load:
  td>: load.sql
  create_table: golden.data_final
```

## 🧪 Testing the Example

1. **Generate visualizations**:
   ```bash
   digdag-viz example --outdir example-output
   ```

2. **Open the dashboard**:
   ```bash
   open example-output/index.html
   ```

3. **Explore features**:
   - Click "🔗 Data Lineage" to see the full lineage graph
   - Try the database filter dropdown
   - Search for specific tables
   - Hover over tables to see dependencies
   - Click on workflows to see their graphs
   - View SQL queries with syntax highlighting

## 📝 Next Steps

After exploring this example:

1. **Try with your workflows**:
   ```bash
   digdag-viz /path/to/your/workflows --outdir output
   ```

2. **Customize templates** (optional):
   ```bash
   digdag-viz example --outdir output --template-dir custom_templates
   ```

3. **Set up CI/CD** - See [GitHub Actions Setup](../docs/github-actions.md)

## 💡 Tips

- **Large projects**: Use the database filter to focus on specific areas
- **Lineage debugging**: Hover over tables to trace data flow
- **Schedule planning**: Check the scheduled workflows page
- **SQL review**: Click on `td>` tasks to view queries

## 🐛 Troubleshooting

If lineage isn't showing:
- Ensure SQL files use `create_table` or `insert_into` parameters
- Check that table names follow `database.table` format
- Verify SQL queries reference source tables correctly

For more help, see the [main README](../README.md).
