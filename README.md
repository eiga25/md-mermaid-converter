# MD Mermaid Converter

A powerful tool to convert Mermaid diagrams in Markdown files to PNG/SVG images, with both CLI and GUI interfaces.

## Features

- 🎨 Render Mermaid code blocks to PNG/SVG images
- 🖥️ Both command-line and graphical interfaces
- 🌐 Bilingual GUI support (Chinese/English)
- 📁 Flexible output: per-file or centralized image storage
- 🔄 Smart caching: only re-renders changed diagrams (content-based hashing)
- 💾 Three rendering modes:
  - **Export**: Generate images without modifying Markdown
  - **Render**: Replace Mermaid blocks with image links
  - **Render-Keep**: Append images while keeping source code
- 🛡️ Automatic backup support before modifying files
- 📋 Profile management for frequently used configurations

## Prerequisites

Install Mermaid CLI:

```bash
npm install -g @mermaid-js/mermaid-cli
```

## Quick Start

### GUI Interface

```bash
python converter_gui.py
```

The GUI provides:
- Profile management (save/load/delete configurations)
- Visual path selection (folder or multiple files)
- Real-time output log
- Dry-run mode for testing
- Language toggle (中文/English)

### CLI Interface

**Basic usage** (append images, keep source):
```bash
python convert_mermaid.py -i document.md --render --keep-source
```

**Replace code blocks** with images:
```bash
python convert_mermaid.py -i document.md --render
```

**Export only** (no Markdown modification):
```bash
python convert_mermaid.py -i docs --recursive --export --format svg
```

**Recursive processing** with per-file images:
```bash
python convert_mermaid.py -i docs --recursive --render --keep-source --images-dir per-file
```

## Output Options

### Centralized Storage
Use `--out-dir` to place all images in a single folder:
```bash
python convert_mermaid.py -i docs --out-dir images/mermaid
```

### Per-File Storage
Use `--images-dir` for per-file image folders:
- `--images-dir per-file`: Creates `[filename]_images` next to each Markdown
- `--images-dir .`: Saves images in the same directory
- `--images-dir images`: Creates an `images` subfolder next to each file

## CLI Options

```
-i, --input PATH          Input Markdown file or folder (required)
-r, --recursive           Recurse into subfolders
-o, --out-dir PATH        Central output directory for images
--images-dir DIR          Per-file images directory (relative to each MD file)
-f, --format FORMAT       Output format: png (default) or svg
--render                  Update Markdown with image links
--export                  Export images only, don't modify Markdown
--keep-source             Keep Mermaid source when rendering (append mode)
--backup                  Create timestamped backup before modifying files
--force                   Force re-render even if images exist
--dry-run                 Show planned actions without executing
```

## Project Structure

```
md-mermaid-converter/
├── convert_mermaid.py   # CLI implementation
├── converter_gui.py     # GUI implementation
├── profiles.json        # Saved GUI profiles
├── i18n.json           # Internationalization strings
├── settings.json       # User preferences (language)
└── examples/           # Example files and demo folders
    ├── test_diagrams.md
    └── demo_tree/
```

## Examples

### Example 1: Documentation Project
```bash
# Process all docs, keep source, use per-file image folders
python convert_mermaid.py -i docs --recursive --render --keep-source --images-dir per-file --backup
```

### Example 2: Export for External Use
```bash
# Export all diagrams as SVG to a central folder
python convert_mermaid.py -i notes --recursive --export --format svg --out-dir output/diagrams
```

### Example 3: Clean Documentation
```bash
# Replace all Mermaid blocks with images (cleaner docs)
python convert_mermaid.py -i README.md --render --format png --backup
```

## GUI Profiles

The project includes two preconfigured profiles:

- **default**: Single file processing with inline images
- **demo**: Recursive processing of demo_tree folder

You can save your own profiles in the GUI for quick reuse.

## Troubleshooting

**mmdc not found on Windows:**
- Ensure `%APPDATA%\npm` is in your PATH
- Or set environment variable: `MERMAID_CLI=C:\path\to\mmdc.cmd`

**Diagram rendering fails:**
- Check Mermaid syntax in the error log
- Test the diagram on [Mermaid Live Editor](https://mermaid.live)
- Update mermaid-cli: `npm update -g @mermaid-js/mermaid-cli`

**Images not updating:**
- Use `--force` flag to bypass cache and re-render

## Technical Highlights

- ✅ Full type hints throughout codebase
- ✅ Comprehensive docstrings (Google style)
- ✅ Smart error handling with specific exceptions
- ✅ Cross-platform path handling
- ✅ Content-based caching (SHA-1 hashing)
- ✅ Modular design with clear separation of concerns

## License

MIT

## Version

1.0.0 - Initial Release
