# filemanager

> ⚠️ This project is currently under development and is not ready for use.

A Python library for safe file system operations within a root directory.

## Features

- List directory contents with metadata
- Safe path resolution (prevents path traversal attacks)
- Configurable date format and sortable fields
- Sortable results by any field, ascending or descending

## Installation

**From source (development):**
```bash
pip install -e .
```

## Usage

```python
from pathlib import Path
from filemanager import FileManager

fm = FileManager('/home/user/documents')

# List directory
fm.list_directory(Path('.'))

# List with ordering
fm.list_directory(Path('.'), order_by='name')
fm.list_directory(Path('.'), order_by='-size')
```

## Configuration

```python
fm = FileManager(
    root_dir='/home/user/documents',
    dt_template='%d/%m/%Y %H:%M:%S',  # custom date format
    valid_order_fields={'name', 'size'} # custom sortable fields
)
```

## Running Tests

```bash
pytest
```

### In Development
- [ ] `list_directory` - List directory contents with metadata ✅
- [ ] `search` - Search for files and directories by name
- [ ] `info` - Get detailed metadata of a file or directory
- [ ] `mkdir` - Create a new directory
- [ ] `delete` - Delete a file or directory
- [ ] `move` - Move or rename a file or directory
- [ ] `copy` - Copy a file or directory
- [ ] `upload` - Save a file from bytes
- [ ] `download` - Read and return file bytes

### Planned
- [ ] CLI interface via Click or Argparse

## License

MIT