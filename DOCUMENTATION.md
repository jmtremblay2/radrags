# Python Documentation Strategy: MkDocs + mkdocstrings

## Philosophy
- Write documentation ONCE, as docstrings inline in your source code.
- Never mirror documentation in the README.
- README is for: project summary, install instructions, quick example, and a link to full docs.
- All API reference is auto-generated from docstrings.
- Narrative/guide docs are hand-written Markdown files in docs/.

---

## Docstring Format: Google Style
Use Google-style docstrings throughout the codebase.

Example:
    def fetch_data(url: str, timeout: int = 30) -> dict:
        """Fetch JSON data from a remote URL.

        Args:
            url: The endpoint to call.
            timeout: Request timeout in seconds.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            ValueError: If the URL is malformed.
            TimeoutError: If the request exceeds `timeout`.
        """

Apply this format to: modules, classes, methods, and functions.

---

## Dependencies
pip install mkdocs mkdocstrings[python] mkdocs-material

---

## Project Structure
my-project/
├── README.md                  # Short: what it does, install, quick example, link to docs
├── mkdocs.yml                 # MkDocs configuration
├── docs/
│   ├── index.md               # Getting started (can symlink README.md here)
│   ├── guide/
│   │   └── usage.md           # Hand-written narrative documentation
│   └── api/
│       └── reference.md       # API reference — uses ::: directives (auto-generated)
└── mypackage/
    └── module.py              # Docstrings live here — single source of truth

---

## mkdocs.yml Configuration
site_name: My Project
theme:
  name: material

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google

---

## How to Reference Docstrings in Markdown
In any .md file under docs/, use the ::: directive to inject a module, class, or function:

Inject an entire module:
    ::: mypackage.mymodule

Inject a specific class:
    ::: mypackage.mymodule.MyClass

Inject a specific function:
    ::: mypackage.mymodule.my_function

mkdocstrings will automatically render the docstring, parameters, return types, and exceptions.

---

## Building and Previewing
# Live preview (localhost:8000)
mkdocs serve

# Build static output to site/
mkdocs build

---

## Publishing to GitHub Pages (optional)
mkdocs gh-deploy --force

Or via GitHub Actions:
    - name: Deploy docs
      run: mkdocs gh-deploy --force

---

## Rules for the Agent
1. All modules, classes, methods, and functions MUST have Google-style docstrings.
2. Do NOT put API documentation in README.md.
3. README.md must stay short: description, install, one usage example, link to docs.
4. For every public module or class, add a corresponding ::: directive in docs/api/reference.md.
5. Hand-written explanations, tutorials, or guides go in docs/guide/ as plain Markdown.
6. mkdocs.yml must always include the mkdocstrings plugin with docstring_style: google.
7. Type hints in function signatures are encouraged — mkdocstrings will render them automatically.
