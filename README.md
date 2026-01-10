# AssetGuy

A practical asset-toolkit to help improve effectiveness when editing documentation, creating content, and managing project assets. Unified CLI tool for optimizing, converting, and managing image, GIF, and video assets.

## Who is AssetGuy for?

AssetGuy is designed for:

- **Developers** - Quickly optimize assets for documentation, README files, and project assets
- **Docs writers** - Streamline image and GIF optimization for technical documentation
- **Open-source maintainers** - Efficiently manage assets across repositories and documentation
- **Product makers** - Optimize assets for web, marketing materials, and product documentation

Whether you're writing technical docs, maintaining open-source projects, or creating product content, AssetGuy helps you focus on content creation rather than wrestling with asset optimization tools.

## Installation

```bash
pip install assetguy
```

## Quick Start

```bash
# Inspect an asset
assetguy inspect image.jpg

# Optimize with a preset
assetguy optimize demo.gif --preset docs

# Optimize with custom parameters
assetguy optimize logo.png --width 800

# Compare two assets
assetguy compare original.gif optimized.gif
```

> **Note:** For development documentation, see [DEVELOPMENT.md](DEVELOPMENT.md)

## Commands

### `inspect`

Display detailed information about an asset.

```bash
assetguy inspect <file> [--json]
```

**Examples:**
```bash
assetguy inspect demo.gif
assetguy inspect image.jpg --json
```

### `optimize`

Optimize GIFs and images with resizing, compression, and quality adjustments.

```bash
assetguy optimize <file> [OPTIONS]
```

**Options:**
- `--preset <name>` - Use preset (docs, web, marketing)
- `--width <pixels>` - Target width in pixels
- `--fps <number>` - Target FPS (GIFs only)
- `--colors <number>` - Number of colors (GIFs only)
- `--output, -o <path>` - Output file path
- `--overwrite` - Overwrite existing output file
- `--non-interactive` - Run without prompts
- `--json` - Output result in JSON format

**Examples:**
```bash
# Use preset
assetguy optimize demo.gif --preset docs

# Custom optimization
assetguy optimize image.jpg --width 1200 --non-interactive

# GIF optimization
assetguy optimize animation.gif --width 800 --fps 10 --colors 128
```

### `compare`

Compare two assets and show differences.

```bash
assetguy compare <file1> <file2> [--json]
```

**Example:**
```bash
assetguy compare original.jpg optimized.jpg
```

### `presets`

List available optimization presets.

```bash
assetguy presets
```

**Available presets:**
- `docs` - Optimized for documentation (800px, 10 FPS, 128 colors)
- `web` - Optimized for web use (1200px, 12 FPS, 256 colors)
- `marketing` - High quality for marketing (1920px, 15 FPS, 256 colors)

### `config`

Manage configuration settings.

```bash
assetguy config show
assetguy config set <key> <value>
assetguy config get <key>
assetguy config reset
```

## Supported Formats

- **Images:** PNG, JPEG, WebP, GIF, BMP, TIFF
- **GIFs:** Animated GIFs with frame manipulation
- **Videos:** Coming soon (v0.2)

## Requirements

- Python 3.7+
- ImageMagick (for GIF operations)
- Pillow (included)

## License

MIT License

## Philosophy

AssetGuy is a **practical asset-toolkit** that helps developers, docs writers, open-source maintainers, and product makers improve their effectiveness when working with assets. It's a policy + orchestration layer that integrates best-in-class tools (ImageMagick, FFmpeg, Pillow) with opinionated defaults, standardizing asset workflows without reinventing low-level media processing.

**Focus on what matters:** Spend less time optimizing assets and more time creating great content.

## Links

- **Homepage:** https://github.com/youyoubilly/assetguy
- **Repository:** https://github.com/youyoubilly/assetguy
- **Issues:** https://github.com/youyoubilly/assetguy/issues
- **Development Guide:** [DEVELOPMENT.md](DEVELOPMENT.md)
