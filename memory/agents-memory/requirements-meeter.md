# Requirements Meeter Output

## Zipsafe Decision
- **Result**: false
- **Reason**: Packages with data files — `certifi` ships `cacert.pem` (Mozilla CA bundle), a binary data file required at runtime for TLS verification

## CLI Tools
- None — the analysis specifies no CLI tool dependencies

## Python Dependencies
- certifi==2026.7.22 — Has data files (`cacert.pem` CA bundle used by `certifi.where()`)
- requests==2.34.2 — Pure Python (only `py.typed` marker, no runtime data files)
- tabulate==0.10.0 — Pure Python (no runtime data files)

## Setup.py Changes
- VENDOR_FOLDER added: no — already present in setup.py; no CLI binaries vendored so the vendor directory will not be created
- data_files updated: no — existing `zip_safe: False` branch in setup.py correctly handles the dep wheel and optional vendor folder without modification
