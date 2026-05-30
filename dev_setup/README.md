# Dev Setup – Shermes

This document describes the development tooling used in the Shermes project (PySide6 application). The goal is to ensure a consistent workflow for dependency management, running the project, linting, and code formatting.

---

# 1. uv

## Purpose

uv
`uv` is a fast Python package and environment manager. It replaces tools like pip, venv.

## Core commands

### Install a dependency

```bash id="uv1"
uv add <package>
```

### Install development dependency

```bash id="uv2"
uv add --dev <package>
```

### Sync environment

```bash id="uv3"
uv sync
```

### Run the project

```bash id="uv4"
uv run python main.py
```

### Run any tool inside the environment

```bash id="uv5"
uv run <command>
```

## When to use

* when adding new dependencies
* when running the project
* when executing tools (black, ruff, pytest)

---

# 2. Black

## Purpose

Black
Black automatically formats Python code according to a consistent, opinionated style.

## Core commands

### Format entire project

```bash id="bf1"
uv run black .
```

### Check entire project

```bash id="bf1"
uv run black . --check
```

### Format a single file

```bash id="bf2"
uv run black path/to/file.py
```

## When to use

* before committing code
* after significant code changes
* automatically on save in VSCode

---

# 3. Ruff

## Purpose

Ruff
Ruff is used for linting (code quality checks, import validation, style enforcement, and error detection).

## Core commands

### Check the project

```bash id="rf1"
uv run ruff check .
```

### Automatically fix issues

```bash id="rf2"
uv run ruff check . --fix
```

### Format code (if enabled)

```bash id="rf3"
uv run ruff format .
```

## When to use

* before committing code
* during refactoring
* when debugging style or import issues

---

# 4. Pylance

## Purpose

Pylance
Pylance provides IDE intelligence inside VSCode, including autocomplete, type checking, and real-time code analysis.

## Features

* intelligent autocomplete
* type inference and checking
* real-time error detection
* fast code navigation

## When to use

* always active inside VSCode
* runs in the background automatically
* no manual execution required

---

# 5. Linting (concept)

Linting is the automatic analysis of source code using specialized tools called linters. A static analyzer scans the code for syntax errors, potential bugs, security issues, and formatting inconsistencies (such as incorrect indentation or unused variables), before the application is even executed.

---

# 6. Recommended workflow

## Daily development

```bash id="wf1"
uv run python main.py
```

## Before committing code

```bash id="wf2"
uv run black .
uv run ruff check . --fix
```

## When adding dependencies

```bash id="wf3"
uv add <package>
uv sync
```

---

# 7. Project rule

Code must always pass:

1. formatting (black)
2. linting (ruff)
3. execution (uv)

without exceptions.

---

# Development Automation (Git Hooks & CI Tools)

## Git Hooks

Git hooks are scripts that Git automatically runs at specific points in the version control workflow (for example before a commit or before a push).

They are used to automatically execute checks such as code formatting, linting, or preventing commits that do not meet defined rules.

In this project, Git hooks are used to run code quality tools before each commit.

---

## Pre-commit Hook

A pre-commit hook is configured to automatically run code checks before every commit.

The hook runs:

- Ruff (linting and automatic fixes)
- Black (code formatting)

If issues are detected that cannot be fixed automatically, the commit will be blocked.

---

## Installation

```bash
uv add --dev pre-commit
uv run pre-commit install
```

## Manual execution

To run all pre-commit checks manually:

```bash
uv run pre-commit run --all-files
```

## Ruff

Ruff is a fast Python linter used to detect errors, unused imports, and style issues.

It can also automatically fix certain problems when run with the `--fix` option.

In this project, it runs automatically via Git hooks before commits.

---

## Black

Black is an automatic Python code formatter that enforces a consistent code style.

It reformats code automatically (indentation, spacing, line length) without requiring manual formatting decisions.

It is executed automatically before commits.

---

## GitHub Actions

GitHub Actions is a continuous integration (CI) system that runs automated checks in the remote repository after pushing code or creating pull requests.

In this project, GitHub Actions is used to:

- Run Ruff (linting)
- Run Black (format check)
- Validate code quality before merging changes

CI runs independently of the local development environment.