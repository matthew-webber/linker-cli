**_ NOTE: the below is a bunch of AI slop that I didn't fully read _**

# Linker CLI

A command-line tool for analyzing and migrating web page content, designed to help with website migrations by extracting links, PDFs, and embedded content from pages.

## Features

- 📊 Load URLs from Excel spreadsheets (DSM files)
- 🔍 Extract and analyze links, PDFs, and Vimeo embeds from web pages
- 📋 Cache analysis results for later review
- 🎯 Use CSS selectors to target specific page sections
- 🔄 Generate migration hierarchies for Sitecore
- 🐛 Debug mode for troubleshooting

## Quick Start

### Prerequisites

- Python 3.7 or higher
- Internet connection (for analyzing web pages)

### Installation

1. **Clone or download this repository**

   ```bash
   cd /path/to/your/projects
   git clone <repository-url>
   cd linker-cli
   # Create a virtual environment (optional but recommended)
   python -m venv venv  # Create a virtual environment
   source venv/bin/activate  # Activate the virtual environment (Linux/Mac)
   ```

2. **Install required Python packages**

   ```bash
   pip install -r requirements.txt
   ```

   If you don't have pip installed, see the [Python installation guide](https://docs.python.org/3/using/index.html).

3. **Verify installation**

   ```bash
   python run.sh --help
   ```

   You should see help text for the Linker CLI.

### First Run

Start the interactive CLI:

```bash
python run.sh
# or
chmod +x run.sh  # Make the script executable
./run.sh
```

You'll see a prompt like:

```
🔗 Welcome to Linker CLI v2.0 - State-based Framework
💡 Type 'help' for available commands
linker (no url) >
```

## Basic Usage

### Analyzing a Single URL

1. **Set a URL to analyze:**

   ```
   set URL https://example.com/page
   ```

2. **Check the page:**

   ```
   check
   ```

3. **View the results:**
   ```
   show page
   ```

### Working with Excel Spreadsheets (DSM Files)

**_IMPORTANT: This feature requires an Excel file with a specific format. Always ensure your DSM file is correctly formatted and up-to-date, otherwise the CLI may not function as expected._**

If you have a DSM (Data Source Mapping) Excel file:

1. **Place your DSM file in the project directory** (named like `dsm-0630.xlsx`)

2. **Load a specific page from the spreadsheet:**

   ```
   load enterprise 15
   ```

   This loads row 15 from the "Enterprise" sheet.

3. **Check the loaded page:**

   ```
   check
   ```

4. **Generate migration hierarchy:**
   ```
   migrate
   ```

## Commands Reference

### Essential Commands

| Command               | Description                           | Example                       |
| --------------------- | ------------------------------------- | ----------------------------- |
| `set <VAR> <value>`   | Set a variable                        | `set URL https://example.com` |
| `show [target]`       | Show variables, domains, or page data | `show vars`, `show page`      |
| `load <domain> <row>` | Load URL from spreadsheet             | `load enterprise 15`          |
| `check`               | Analyze the current URL               | `check`                       |
| `migrate`             | Generate migration hierarchy          | `migrate`                     |
| `help`                | Show help information                 | `help`                        |

### Utility Commands

| Command           | Description          |
| ----------------- | -------------------- |
| `debug [on\|off]` | Toggle debug output  |
| `clear`           | Clear the screen     |
| `exit` or `quit`  | Exit the application |

## Variables

The CLI uses these variables to track state:

| Variable        | Description                | Example                    |
| --------------- | -------------------------- | -------------------------- |
| `URL`           | Target URL to analyze      | `https://example.com/page` |
| `DOMAIN`        | Current spreadsheet domain | `Enterprise`               |
| `ROW`           | Current spreadsheet row    | `15`                       |
| `SELECTOR`      | CSS selector for content   | `#main`, `.content`        |
| `DSM_FILE`      | Path to Excel file         | `dsm-0630.xlsx`            |
| `PROPOSED_PATH` | New URL path for migration | `about/team`               |

## Example Workflows

### Workflow 1: Quick Page Analysis

```bash
# Start the CLI
python run.sh

# Set URL and analyze
set URL https://education.musc.edu/students/ose/team
check
show page
```

### Workflow 2: Spreadsheet-Based Analysis

```bash
# Start the CLI
python run.sh

# Load from spreadsheet (case-insensitive domain names)
load education 23
check
show page
migrate
```

### Workflow 3: Custom CSS Selector

```bash
# Target specific page section
set URL https://example.com
set SELECTOR .main-content
check
show page
```

## Understanding Output

### Page Analysis Results

When you run `show page`, you'll see:

- **🔗 LINKS FOUND**: Regular hyperlinks with status codes
- **📄 PDF FILES**: Direct links to PDF documents
- **🎬 VIMEO EMBEDS**: Embedded Vimeo videos

Status codes:

- ✅ `2xx` - Link works
- ❌ `4xx/5xx` - Link broken
- ⚠️ `0` - Couldn't check (mailto, tel, etc.)

### Migration Hierarchy

The `migrate` command shows how the page would be organized in Sitecore:

```
Existing directory hierarchy:
Education (Sites)
 > students
 > ose
 > team

Proposed directory hierarchy:
Education (Sites)
 > about
 > staff
```

## Working with DSM Files

### DSM File Format

DSM files should be Excel files with:

- Filename pattern: `dsm-MMDD.xlsx` (e.g., `dsm-0630.xlsx`)
- Multiple sheets named after domains (Enterprise, Education, etc.)
- Headers on row 4 (zero-indexed row 3)
- Columns: "Existing URL", "Proposed URL"

### Supported Domains

The CLI recognizes these domain sheet names (case-insensitive):

- Enterprise
- Adult Health
- Hollings Cancer
- Education
- Research
- Childrens Health
- CDM, CGS, CHP, COM, CON, COP
- MUSC Giving

## Troubleshooting

### Common Issues

**"No DSM file found"**

- Ensure your Excel file is named `dsm-MMDD.xlsx`
- Place it in the same directory as `run.sh`
- Or manually set: `set DSM_FILE path/to/your/file.xlsx`

**"Domain not found"**

- Domain names are case-insensitive: `load ENTERPRISE 15` works
- Use `show domains` to see available domains
- Check your Excel file has the expected sheet names

**"Could not find URL for row X"**

- Verify the row number exists in the Excel sheet
- Check that the "Existing URL" column has data
- Remember: Excel row numbers start at 1

**SSL/Certificate errors**

- Some sites may have SSL issues
- The tool will still attempt to analyze the page
- Check debug output with `debug on`

### Debug Mode

Enable detailed logging:

```bash
debug on
```

This shows:

- HTTP requests and responses
- Excel file parsing details
- CSS selector matching
- Variable changes

## File Structure

```
linker-cli/
├── run.sh                 # Main CLI application
├── migrate_hierarchy.py   # Migration hierarchy logic
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── dsm-*.xlsx            # Your DSM files (not in git)
├── migration_cache/      # Cached analysis results
└── link_extractor/       # Standalone link extraction tool
```

## Advanced Usage

### Custom CSS Selectors

Target specific page sections:

```bash
set SELECTOR .main-content    # Class selector
set SELECTOR #article        # ID selector
set SELECTOR article         # Tag selector
set SELECTOR .content .body  # Nested selector
```

### Caching

Analysis results are automatically cached in `migration_cache/`. Files are named based on the source (URL or spreadsheet location).

### Legacy Mode

Access the original workflow interface:

```bash
legacy
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues or questions:

1. Check this README first
2. Enable debug mode: `debug on`
3. [Add your contact/issue reporting information]
