# Development Guide

## Philosophy

AssetGuy is a **policy + orchestration layer** for asset optimization. It does not reinvent low-level tools but instead:

- Integrates best-in-class existing tools (ImageMagick, FFmpeg, Pillow)
- Applies opinionated but overridable defaults
- Standardizes workflows developers repeatedly struggle with
- Provides clarity over raw power

> Think "Prettier / ESLint for assets", not "FFmpeg replacement".

### Core Principles

1. **Do NOT reinvent low-level tools** - Orchestrate and standardize existing, battle-tested tools
2. **Flexible but guided** - Good defaults and presets, with override capability
3. **Assets, not formats** - Treat static images, animated images, and videos as assets in a pipeline
4. **Clarity over completeness** - Prefer defaults over configuration, wrapping tools over reimplementing

## Architecture

### High-Level Flow

```mermaid
flowchart TD
    A[User Intent] --> B{Preset or<br/>Custom Params?}
    B -->|Preset| C[Load Preset Config]
    B -->|Custom| D[Use CLI Flags]
    C --> E[Merge Parameters<br/>CLI overrides Preset]
    D --> E
    E --> F[Detect Asset Type]
    F --> G{Asset Type}
    G -->|GIF| H[GifAsset]
    G -->|Image| I[ImageAsset]
    G -->|Video| J[VideoAsset]
    H --> K[Tool Selection]
    I --> K
    J --> K
    K --> L{Required Tool}
    L -->|ImageMagick| M[ImageMagick Executor]
    L -->|Pillow| N[Pillow Operations]
    L -->|FFmpeg| O[FFmpeg Executor]
    M --> P[Execute Operation]
    N --> P
    O --> P
    P --> Q[Format Result]
    Q --> R[Human-readable Output]
    Q --> S[JSON Output]
```

### Package Structure

```mermaid
graph TB
    subgraph CLI["CLI Layer (cli.py)"]
        CLI_CMD[Commands: inspect, optimize, compare, config, presets]
    end
    
    subgraph OPS["Operations Layer (operations/)"]
        OPS_INSPECT[inspect.py<br/>Asset type detection & inspection]
        OPS_OPTIMIZE[optimize.py<br/>Optimization operations]
        OPS_COMPARE[compare.py<br/>Before/after comparison]
    end
    
    subgraph ASSETS["Asset Layer (assets/)"]
        ASSETS_BASE[base.py<br/>Base Asset class]
        ASSETS_GIF[gif.py<br/>GifAsset]
        ASSETS_IMAGE[image.py<br/>ImageAsset]
    end
    
    subgraph TOOLS["Tools Layer (tools/)"]
        TOOLS_DETECT[detector.py<br/>Tool availability detection]
        TOOLS_EXEC[executor.py<br/>Safe subprocess execution]
    end
    
    subgraph CONFIG["Config Layer (config/)"]
        CONFIG_MGR[manager.py<br/>Unified config management]
        CONFIG_PRESETS[presets.py<br/>Preset definitions]
    end
    
    subgraph UTILS["Utils Layer (utils/)"]
        UTILS_FMT[formatting.py<br/>File size, time formatting]
        UTILS_PATHS[paths.py<br/>Path handling]
    end
    
    CLI_CMD --> OPS_INSPECT
    CLI_CMD --> OPS_OPTIMIZE
    CLI_CMD --> OPS_COMPARE
    CLI_CMD --> CONFIG_MGR
    CLI_CMD --> CONFIG_PRESETS
    
    OPS_INSPECT --> ASSETS_GIF
    OPS_INSPECT --> ASSETS_IMAGE
    OPS_OPTIMIZE --> ASSETS_GIF
    OPS_OPTIMIZE --> ASSETS_IMAGE
    OPS_COMPARE --> ASSETS_GIF
    OPS_COMPARE --> ASSETS_IMAGE
    
    ASSETS_GIF --> ASSETS_BASE
    ASSETS_IMAGE --> ASSETS_BASE
    
    OPS_OPTIMIZE --> TOOLS_DETECT
    OPS_OPTIMIZE --> TOOLS_EXEC
    ASSETS_GIF --> TOOLS_DETECT
    ASSETS_GIF --> TOOLS_EXEC
    
    OPS_OPTIMIZE --> UTILS_FMT
    OPS_COMPARE --> UTILS_FMT
    CLI_CMD --> UTILS_PATHS
```

### Data Flow: Optimize Command

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Ops
    participant Asset
    participant Tools
    participant Executor
    
    User->>CLI: optimize file.gif --preset docs
    CLI->>Ops: detect_asset_type(file)
    Ops-->>CLI: 'gif'
    CLI->>CLI: Load preset 'docs'
    CLI->>CLI: Merge params (CLI overrides preset)
    CLI->>Asset: GifAsset(file)
    Asset->>Asset: get_info()
    Asset->>Tools: get_imagemagick_command()
    Tools-->>Asset: 'magick' or 'convert'
    Asset-->>CLI: GIF metadata
    CLI->>Ops: optimize_gif(gif_asset, params)
    Ops->>Tools: get_imagemagick_command()
    Tools-->>Ops: ImageMagick command
    Ops->>Executor: run([magick, ...])
    Executor->>Executor: subprocess execution
    Executor-->>Ops: Success
    Ops->>Ops: format_optimization_result()
    Ops-->>CLI: Result dict
    CLI->>User: Print formatted result
```

## Module Responsibilities

### `cli.py`
- Command-line interface using Click
- Parameter parsing and validation
- Interactive vs non-interactive mode handling
- Output formatting (human-readable vs JSON)

### `operations/`
- **`inspect.py`**: Unified asset inspection across all types
- **`optimize.py`**: Core optimization logic for GIFs and images
- **`compare.py`**: Before/after comparison utilities

### `assets/`
- **`base.py`**: Base `Asset` class with common functionality
- **`gif.py`**: `GifAsset` class for GIF-specific operations
- **`image.py`**: `ImageAsset` class for static image operations

### `tools/`
- **`detector.py`**: Detects availability of external tools (ImageMagick, FFmpeg)
- **`executor.py`**: Safe subprocess execution wrapper

### `config/`
- **`manager.py`**: Unified configuration management (`~/.assetguy/config.yaml`)
- **`presets.py`**: Preset definitions (docs, web, marketing)

### `utils/`
- **`formatting.py`**: File size and time formatting utilities
- **`paths.py`**: Path handling (quote stripping, expansion)

## Tool Dependencies

AssetGuy relies on external tools and gracefully handles their absence:

| Tool | Purpose | Required For | Detection |
|------|---------|--------------|-----------|
| ImageMagick | GIF manipulation, inspection | GIF operations | `tools/detector.py` |
| Pillow | Image processing | Image operations | Python package |
| FFmpeg | Video processing | Video operations (v0.2) | `tools/detector.py` |

## Preset System

Presets are experience-backed policies, not magic. They define:

- Target dimensions (width)
- FPS caps (for GIFs)
- Color limits (for GIFs)
- Quality settings

**Priority order:**
1. CLI flags (highest)
2. Preset values
3. Interactive prompts (if interactive mode)
4. Defaults (lowest)

## Adding New Features

### Adding a New Asset Type

1. Create asset class in `assets/` (e.g., `assets/video.py`)
2. Extend `operations/inspect.py` to detect and handle new type
3. Add optimization logic in `operations/optimize.py` if needed
4. Update `cli.py` to support new type in commands

### Adding a New Operation

1. Add function to appropriate `operations/` module
2. Export from `operations/__init__.py`
3. Add CLI command in `cli.py`
4. Update tests

### Adding a New Preset

1. Add preset definition to `config/presets.py`
2. Document in README.md
3. Test with various asset types

## Testing

Test files are located in `test-files/` (excluded from git).

**Test coverage:**
- GIF optimization with various parameters
- Image optimization with presets
- Format detection and inspection
- Comparison operations
- JSON output format

## Development Workflow

1. **Setup:**
   ```bash
   pip install -e .
   ```

2. **Run tests:**
   ```bash
   python -m assetguy.cli inspect test-files/demo.gif
   python -m assetguy.cli optimize test-files/demo.gif --preset docs
   ```

3. **Check tool availability:**
   ```bash
   python -c "from assetguy.tools.detector import get_imagemagick_command; print(get_imagemagick_command())"
   ```

## Design Guardrails

When adding features, follow these principles:

- ✅ Prefer clarity over completeness
- ✅ Prefer defaults over configuration
- ✅ Prefer wrapping tools over reimplementing
- ✅ Avoid plugin systems until proven necessary
- ✅ Avoid "AI magic" or opaque heuristics
- ❌ Don't reimplement codecs or encoders
- ❌ Don't expose excessive low-level flags
- ❌ Don't hide what the tool is doing

## Roadmap

**v0.1** (Current)
- ✅ Package structure
- ✅ GIF optimization
- ✅ Image optimization
- ✅ Presets
- ✅ Interactive CLI

**v0.2** (Next)
- GIF → WebP conversion
- Video → GIF/WebP
- Duration trimming
- FFmpeg integration

**v0.3** (Future)
- Static image compression (pngquant, mozjpeg)
- Batch processing
- CI templates / GitHub Actions

## Contributing

1. Follow the architecture patterns above
2. Keep operations modular and testable
3. Maintain backward compatibility
4. Update documentation for user-facing changes
5. Test with real assets from `test-files/`
