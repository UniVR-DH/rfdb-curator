# RFDBTools Developer Guide

## Summary
RFDBTools is a Python toolkit for managing RDF data and SHACL shapes for Russian theatrical works. It provides utilities for validating RDF data, generating Excel workbooks from SHACL shapes, and enforces code quality via pre-commit hooks and CI/CD.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Dependency Management](#dependency-management)
3. [Pre-commit Hooks](#pre-commit-hooks)
4. [Static Code Analysis](#static-code-analysis)
5. [Validation & Build Workflow](#validation--build-workflow)
6. [CI/CD Integration](#cicd-integration)
7. [Extending the Project](#extending-the-project)
8. [Troubleshooting](#troubleshooting)
9. [Contributing Workflow](#contributing-workflow)
10. [References](#references)

---

## 1. Getting Started

1. **Sync root dependencies with uv (rfdbtools environment):**
   ```bash
   uv sync --all-extras --dev
   source .venv/bin/activate
   ```
2. **Use the root `.venv` for all Python commands, including editor/backend work.**
3. **Set up pre-commit hooks for linting and formatting**:
   ```bash
   uv tool install pre-commit
   pre-commit install
   ```

---

## 2. Dependency Management

Dependencies are managed with [uv](https://github.com/astral-sh/uv) for speed and reproducibility, with exact version pins in each project `pyproject.toml`.

---

## 3. Pre-commit Hooks

Pre-commit hooks are configured in `.pre-commit-config.yaml` to ensure code quality and consistent formatting before every commit.

**Configured hooks:**

- **pre-commit-hooks** ([repo](https://github.com/pre-commit/pre-commit-hooks)):
  - `check-case-conflict`: Prevents files with the same name differing only in case.
  - `check-merge-conflict`: Blocks commits with unresolved merge conflict markers.
  - `check-toml`: Validates TOML files (e.g., `pyproject.toml`).
  - `check-yaml`: Validates YAML files (e.g., configs).
  - `check-json`: Validates JSON files (excluding `.devcontainer/devcontainer.json`).
  - `pretty-format-json`: Auto-formats JSON files (excluding `.devcontainer/devcontainer.json`).
  - `end-of-file-fixer`: Ensures files end with a newline.
  - `trailing-whitespace`: Removes trailing whitespace from files.
- **ruff-pre-commit** ([repo](https://github.com/astral-sh/ruff-pre-commit)):
  - `ruff`: Fast Python linter (replaces flake8).
  - `ruff-format`: Fast Python code formatter.

**Note:** API documentation generation with pdoc is NOT part of pre-commit hooks. Docs are generated manually (see section 4).

---

## 3b. Static Code Analysis

The project uses a **lightweight, multi-tool approach** for code quality checks:

### Tools

| Language | Tools | Config |
|----------|-------|--------|
| JavaScript/React | ESLint, Prettier | `.eslintrc.json`, `.prettierrc.json` |
| Python | Ruff (linting + formatting) | `pyproject.toml`, `.ruffignore` |
| JSON/YAML | pre-commit hooks | `.pre-commit-config.yaml` |

### Make Commands

```bash
make check       # Run all static analysis (linting + Python validation)
make lint        # Run ESLint on JavaScript files only
make lint-fix    # Auto-fix linting issues
make format      # Format code with Prettier
```

### Automatic Checks

- **On commit**: Pre-commit hooks run ESLint, Prettier, and Ruff automatically
- **Performance**: ~1 second total (ESLint ~500ms, Prettier ~200ms, Ruff ~50ms)
- **Auto-fixes**: Minor issues (formatting, unused imports) are automatically corrected

### Manual Checking

Before committing, you can run checks manually:

```bash
make lint-fix    # Fix JavaScript linting issues
make format      # Format all code
git add .
git commit -m "..."  # Pre-commit will run final checks
```

### Configuration Files

- **`eslint.config.js`** - Root ESLint config (flat config format for ESLint v9)
- **`.prettierrc.json`** - Code formatting (semicolons, line width, indentation)
- **`.ruffignore`** - Python files to skip during analysis
- **`.prettierignore`** - JavaScript/CSS files to skip during formatting

---

## 4. Validation & Build Workflow

The project uses a **Makefile** to orchestrate the complete workflow. See the Makefile itself for comprehensive documentation of all targets.

### Quick Commands

```bash
make all                  # Run full pipeline: docs + validation
make download-ontologies  # Download external ontologies from @prefix URIs
make convert-ontologies   # Convert all ontologies to Turtle format
make validate-ontologies  # Validate RDFS/OWL consistency
make validate-data        # Complete validation: download → convert → validate
make docs                 # Generate API documentation
make clean                # Remove generated files
```

### SHACL Validation
Validate RDF data before committing changes:
```bash
python -m rfdbtools.validator --data data/data.ttl --schema schema/schema.ttl
```
Or from Python:
```python
from rfdbtools import validate
conforms, report_path = validate("data/data.ttl", "schema/schema.ttl")
```
- Exit code 0: data conforms
- Exit code 1: data does not conform (see printed report)

### Ontology Management

External ontologies are automatically downloaded and converted via the Makefile workflow.

**Workflow:**
```bash
make download-ontologies  # Downloads from @prefix URIs in data/data.ttl
make convert-ontologies   # Converts all formats (RDF/XML, N-Triples, etc.) to Turtle
```

Ontologies are stored in `.ontologies/` (gitignored). The `python -m rfdbtools.convert_ontologies` script automatically handles all RDF format conversions.

**Note:** If you need to manually download a specific ontology, request Turtle format:
```bash
curl -L -H 'Accept: text/turtle' -o .ontologies/mm.ttl https://w3id.org/polifonia/ontology/music-meta
```

### Excel Workbook Generation (optional)
Generate a data-entry workbook from SHACL shapes:
```python
from rfdbtools import generate_excel_from_shacl
generate_excel_from_shacl("schema/schema.ttl", "data_entry_workbook.xlsx")
```

### Documentation Generation
API docs are generated manually with pdoc:
```bash
make docs
# or
source .venv/bin/activate && python -m pdoc --output-dir docs rfdbtools
```
Only commit docs when you intentionally regenerate them (e.g., before a release).
See `docs/DOCS_WORKFLOW.md` for details.

---

## 5. CI/CD Integration

GitHub Actions (`.github/workflows/ci.yml`) runs on every commit or pull request:
- Installs Python dependencies
- Lints code with ruff
- Runs Python tests in `tests/`
- Validates RDF data with SHACL
- Auto-generates docs with pdoc

If validation fails, the workflow fails and blocks merges.

---

## 6. Extending the Project

- To add new SHACL shapes, edit `schema/schema.ttl` and group by entity.
- To add new data, edit `data/data.ttl` and follow current patterns.
- For new tools, add to `rfdbtools/` and update the CLI in `rfdbtools/__main__.py` if needed.

---

## 7. Troubleshooting

- If you see `ImportError: pyshacl must be installed`, ensure dependencies are installed as above.
- If validation fails, check cardinalities, datatypes, and required fields in your data.
- If docs are not updating, check `.pre-commit-config.yaml` and run `pre-commit run --all-files`.

---


## 8. References

- See `README.md` for generator details and API usage.
- See `Makefile` for comprehensive workflow orchestration and target documentation.
- See `.github/copilot-instructions.md` for AI agent and commit policy.
- See `.pre-commit-config.yaml` for hook configuration.
- See `eslint.config.js` and `.prettierrc.json` for JavaScript code quality rules.
- See `.github/workflows/ci.yml` for CI/CD details.
- See `docs/DOCS_WORKFLOW.md` for documentation generation workflow.

---

## 9. Contributing Workflow


Follow these steps to contribute to this repository:

1. **Fork the repository** on GitHub and clone your fork:
   ```bash
   git clone https://github.com/<your-username>/RossijskijFeatrDB.git
   cd RossijskijFeatrDB
   ```

2. **Sync root dependencies with uv (rfdbtools environment):**
   ```bash
   uv sync --all-extras --dev
   source .venv/bin/activate
   ```

3. **Use the root `.venv` for all Python commands, including editor/backend work.**

4. **Set up pre-commit hooks:**
   ```bash
   uv tool install pre-commit
   pre-commit install
   ```


5. **Edit code or data as needed.**
   - `rfdbtools/`: Python code for SHACL validation, Excel generation, and utilities.
   - `schema/schema.ttl`: SHACL NodeShapes for core entities (edit/add shapes here).
   - `data/data.ttl`: Example RDF dataset (add/edit data instances here).
   - `README.md`, `DEV.md`, `docs/`: Documentation and workflow instructions.
   - `.pre-commit-config.yaml`, `Makefile`, `.github/`: CI/CD, hooks, and workflow config.

   **Validate RDF data:**
   Before committing, validate your RDF data:
   ```bash
   python -m rfdbtools.validator --data data/data.ttl --schema schema/schema.ttl
   ```

   **(Optional) Generate API documentation:**
   If you have made changes to the Python code and want to update the API docs:
   ```bash
   make docs
   # or
   source .venv/bin/activate && python -m pdoc --output-dir docs rfdbtools
   ```
   **Reminder:** Only regenerate and commit docs when needed (e.g., before a release or after major code changes).


7. **Commit your changes:**
   - When you commit, pre-commit will automatically lint and format your code and data files.
   - Optionally, run `pre-commit run --all-files` to check all files before committing.
   ```bash
   git add .
   git commit -m "Describe your changes [BOT]"
   git push origin <your-branch>
   ```

10. **Submit a pull request** from your fork to the main repository.

---
