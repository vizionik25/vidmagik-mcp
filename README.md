# vidMagik-mcp

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![MoviePy](https://img.shields.io/badge/MoviePy-2.2+-orange.svg)](https://zulko.github.io/moviepy/)

A Model Context Protocol (MCP) server that provides a comprehensive interface to [MoviePy](https://zulko.github.io/moviepy/) for video editing. Uses **stdio** transport by default for seamless integration with MCP clients.

Exposes **70+ tools** for professional-grade video editing, compositing, effects, and audio processing.

## Features

### IO & Creation
- **Load**: `video_file_clip`, `audio_file_clip`, `image_clip`, `image_sequence_clip`
- **Generate**: `text_clip`, `color_clip`, `credits_clip`, `subtitles_clip`, `tools_drawing_color_gradient`, `tools_drawing_color_split`
- **Export**: `write_videofile`, `write_audiofile`, `write_gif`
- **Fast Tools**: `tools_ffmpeg_extract_subclip` (lossless trimming)

### Compositing & Transformation
- **Combine**: `composite_video_clips`, `concatenate_video_clips`, `tools_clips_array`, `composite_audio_clips`, `concatenate_audio_clips`
- **Refine**: `subclip`, `vfx_resize`, `vfx_crop`, `vfx_rotate`
- **Configure**: `set_position`, `set_audio`, `set_mask`, `set_start`, `set_end`, `set_duration`

### Video Effects (vfx)
- **Time**: `vfx_freeze`, `vfx_freeze_region`, `vfx_multiply_speed`, `vfx_time_mirror`, `vfx_time_symmetrize`, `vfx_loop`, `vfx_make_loopable`, `vfx_accel_decel`
- **Color**: `vfx_black_white`, `vfx_invert_colors`, `vfx_fade_in`, `vfx_fade_out`, `vfx_gamma_correction`, `vfx_lum_contrast`, `vfx_multiply_color`, `vfx_painting`, `vfx_blink`
- **Geometry**: `vfx_mirror_x`, `vfx_mirror_y`, `vfx_even_size`, `vfx_margin`, `vfx_scroll`, `vfx_supersample`
- **Motion**: `vfx_slide_in`, `vfx_slide_out`, `vfx_head_blur`
- **Masking**: `vfx_mask_color`, `vfx_masks_and`, `vfx_masks_or`

### Custom Advanced Effects
- **`vfx_matrix`** — Classic "Matrix" digital rain overlay
- **`vfx_kaleidoscope`** — Radial symmetry with custom slices
- **`vfx_rgb_sync`** — Chromatic aberration / glitch with temporal offsets
- **`vfx_chroma_key`** — Green screen removal with threshold and softness
- **`vfx_auto_framing`** — Face/subject tracking and cropping for vertical video
- **`vfx_clone_grid`** — Multi-clone grid layout (2x2, 4x4, etc.)
- **`vfx_rotating_cube`** — 3D perspective cube mapping
- **`vfx_quad_mirror`** — Four-way mirror symmetry
- **`vfx_kaleidoscope_cube`** — Radial symmetry combined with 3D rotation

### Audio Effects (afx)
- `afx_multiply_volume`, `afx_multiply_stereo_volume`, `afx_audio_fade_in`, `afx_audio_fade_out`, `afx_audio_delay`, `afx_audio_loop`, `afx_audio_normalize`

### Analysis & Utilities
- `tools_detect_scenes` — Automatic scene cut detection
- `tools_find_video_period` — Frequency analysis for repetitive motion
- `tools_find_audio_period` — Tempo/period detection for audio
- `tools_file_to_subtitles` — Parse subtitle files
- `tools_check_installation` — Verify MoviePy and dependencies

## Prerequisites

- **Python 3.12+**
- **FFmpeg** — Required by MoviePy for video processing
- **ImageMagick** — Required for `text_clip` and `credits_clip`
- **uv** — Python package manager

## Installation

```bash
git clone https://github.com/vizionik25/vidMagik-mcp.git
cd vidMagik-mcp
uv sync
```

## Running the Server

The server uses **stdio** transport by default:

```bash
uv run main.py
```

To use HTTP or SSE transport instead:

```bash
uv run main.py --transport http --host 0.0.0.0 --port 8080
uv run main.py --transport sse --host 0.0.0.0 --port 8080
```

### MCP Client Configuration

Add this to your MCP client config (e.g. Claude Desktop, Cursor, etc.):

```json
{
  "mcpServers": {
    "vidMagik-mcp": {
      "command": "uv",
      "args": ["run", "main.py"],
      "cwd": "/path/to/vidMagik-mcp"
    }
  }
}
```

## Docker

Docker is the recommended approach — it bundles FFmpeg, ImageMagick, and all system dependencies automatically.

### Quick Start

```bash
docker compose up --build
```

This builds the image and starts the server with stdio transport.

### Media Directory

The `./media` directory on your host is mounted to `/app/media` inside the container. Use it as the workspace for all input and output files:

```bash
mkdir -p media
# Place your source videos, images, and audio in ./media
```

When using MCP tools, reference files as `media/filename.mp4`. Output files written to `media/` will appear on your host.

### Docker MCP Client Configuration

To use the Docker container as an MCP server:

```json
{
  "mcpServers": {
    "moviepy": {
      "command": "docker",
      "args": ["compose", "run", "--rm", "-i", "mcp-moviepy"],
      "cwd": "/path/to/mcp-moviepy"
    }
  }
}
```

### Manual Docker Build & Run

```bash
docker build -t mcp-moviepy .
docker run -i -v $(pwd)/media:/app/media mcp-moviepy
```

## State Management

The server maintains clips in memory:

1. **Clip IDs** — Tools that create or modify clips return a `clip_id` (UUID string)
2. **Chaining** — Pass `clip_id` to subsequent tools for further operations
3. **Management** — Use `list_clips` to view active clips and `delete_clip` to free memory
4. **Limits** — Auto memory cleanup with file count and total size limits to prevent OOM

## Prompt Templates

Built-in prompts guide the LLM through complex workflows:

- `slideshow_wizard` — Professional slideshow from images with transitions
- `title_card_generator` — Title cards with text on solid backgrounds
- `glitch_effect_preset` — High-energy RGB split glitch aesthetic
- `auto_framing_for_tiktok` — Convert horizontal video to 9:16 vertical
- `matrix_intro_preset` — Classic code-rain overlay
- `rotating_cube_transition` — 3D spinning cube effect
- `demonstrate_kaleidoscope` — Mesmerizing radial symmetry animation
- `demonstrate_kaleidoscope_cube` — Hybrid kaleidoscope + 3D cube

## Development

Run tests:

```bash
uv run pytest tests/test_e2e.py
```

## License

MIT
