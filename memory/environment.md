# Universal Extension Development Environment

**Generated:** 2026-08-27 08:12:02

## UIP Template Information

This extension was bootstrapped using the following UIP template:

- **Template Name:** `ue-task-ca`
- **Description:** Standard Template for non-monitor based extensions.
- **Type:** standard

---

## Overview

This workspace contains a complete development environment for a Universal Extension (UE) for Stonebranch Universal Automation Center (UAC).
This document provides critical information about the workspace structure, configuration, and development workflow.

---

## Workspace Structure

```
ue-oracle-analytics-publisher/
├── acceptance_testing/         # Testing artifacts like sample test task definitions
├── memory/                     # Context files used by AI assistants
│   └── environment.md          # This file
├── .env                        # Environment variables for UIP integration
├── ue-dev-env/                 # Python virtual environment
│   ├── bin/                    # Python executables and CLI tools
│   ├── lib/                    # Python packages
│   └── requirements_dev.txt    # Development environment dependencies
└── extension-code/             # Universal Extension source code directory tree
    ├── .uip/                   # UIP CLI configuration directory
    │   └── config/
    │       └── uip.yml         # Extension build and deployment configuration
    ├── 3pp/                    # Third-party packages (dependencies not available via pip)
    ├── build/                  # Build artifacts (generated during packaging)
    │   ├── bdist.linux-x86_64/ # Platform-specific build files
    │   └── lib/                # Compiled extension modules
    ├── dist/                   # Distribution packages (final output)
    │   └── extension_build/    # Built extension ZIP files ready for deployment
    ├── src/                    # Extension source code
    │   ├── extension.py        # Main extension logic
    │   ├── extension.yml       # Extension metadata and configuration
    │   ├── templates/          # Universal Template definitions
    │   │   └── template.json   # Task template JSON specification
    │   └── *.egg-info/         # Python package metadata (generated)
    ├── temp/                   # Temporary files (used during build process)
    ├── __pycache__/            # Python bytecode cache
    ├── __init__.py             # Python package initializer
    ├── requirements.txt        # Extension runtime dependencies
    ├── setup.cfg               # Setup configuration
    └── setup.py                # Extension package configuration
```

---

## Configuration Details

## Build Platform

- **OS**: Linux
- **Architecture**: x86_64


### Extension Information

- **Extension Name:** `ue-oracle-analytics-publisher`
- **Template Name:** `Ue Oracle Analytics Publisher`
- **Owner:** `ISS`
- **Organization:** `Stonebranch`
- **API Level:** `1.6.0`
- **Python Version:** `>= 3.11`


### UIP Configuration

The `.env` file in the workspace root contains the following UIP connection parameters:

- **UIP_USERID:** `len`
- **UIP_URL:** `https://ps1.stonebranchdev.cloud`
- **UIP_PASSWORD:** *(configured)*

**Security Note:** The `.env` file contains sensitive credentials. Ensure it is:
- Added to `.gitignore` (never committed to version control)
- Properly secured with appropriate file permissions (`chmod 600 .env`)


---

## Development Workflow

### 1. Activate Virtual Environment

Before working with the extension, activate the Python virtual environment:

```bash
source ue-dev-env/bin/activate
```

### 2. Navigate to Extension Directory

```bash
cd extension-code
```

### 3. Common Development Tasks

#### Build the Extension

```bash
uip build
```

This validates the extension structure and creates a distributable package in the `dist/` directory.

#### Push to UAC Controller

```bash
quip push using quip-cli    
uip push using uip-cli
```

Uploads the extension to the configured UAC controller

#### Build and Push in One Command

```bash
quip push -a using quip-cli
uip push -a using uip-cli
```

The `-a` flag automatically builds before pushing.

#### Pull Template from Controller

```bash
quip pull
uip pull 
```

Synchronizes the extension template from the UAC controller.

---

## Directory Purposes

### `acceptance_testing/`

This directory is designated for:
- Test scripts and validation procedures
- Test data and fixtures

Use this directory to organize all testing artifacts related to validating the Universal Extension functionality.

### `memory/`

This directory serves as:
- A knowledge base for the development environment
- Storage for context and documentation files
- Notes and guidance for coding assistants
- Development logs and decision records

Files in this directory help maintain context across development sessions and provide guidance for AI-assisted development.

### `ue-dev-env/`

The Python virtual environment containing:
- **wheel** (version 0.45.1) - Python wheel packaging standard
- **uip-cli** - Universal Integration Platform command-line interface (includes setuptools)
- **quip-cli** - CLI tool for managing uip-cli with fields.yml configuration for build and deployment
- **keyrings.alt** - Alternative keyring backend for secure credential storage
- All Python dependencies isolated from system Python

**Important:** Always activate this virtual environment before running UIP commands or working with the extension.

---

*This document was automatically generated by ue-init. Update it as your development environment evolves.*
