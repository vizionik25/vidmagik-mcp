# vidMagik-mcp

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![MoviePy](https://img.shields.io/badge/MoviePy-2.2+-orange.svg)](https://zulko.github.io/moviepy/)
[![Deployed on Fly.io](https://img.shields.io/badge/Deployed%20on-Fly.io-blueviolet)](https://fly.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A powerful Model Context Protocol (MCP) server providing a comprehensive interface to [MoviePy](https://zulko.github.io/moviepy/) for AI-driven video editing. Hosted remotely on **Fly.io** using Streamable HTTP transport, enabling seamless integration with AI agents and video editing workflows.

## Features

- **90+ MCP tools** — clip management, effects, compositing, audio processing, analysis, and file I/O
- **8 prompt templates** — built-in workflow guides for common video editing tasks
- **11 custom effects** — Matrix rain, kaleidoscope, chroma key, auto-framing, glitch effects, and more
- **3 HTTP endpoints** — browser-based file upload UI, binary upload receiver, and file download
- **GitHub OAuth authentication** — secure remote access with GitHub credentials
- **Fly.io deployment** — production-ready hosting with session persistence and automatic scaling
- **Full FFmpeg integration** — high-quality video encoding and audio processing
- **Memory-efficient** — max 30 clips per session with stash/unstash for large projects

---

## Table of Contents

- [Quick Start](#quick-start)
- [Deployment (Fly.io)](#deployment-flyio)
- [Local Development](#local-development)
- [Environment Configuration](#environment-configuration)
- [MCP Client Configuration](#mcp-client-configuration)
- [Architecture & State Management](#architecture--state-management)
- [File Upload & Download Flow](#file-upload--download-flow)
- [HTTP Endpoints](#http-endpoints)
- [Tools Reference](#tools-reference)
  - [Clip Management](#clip-management)
  - [IO & Creation](#io--creation)
  - [Compositing & Layout](#compositing--layout)
  - [Clip Configuration](#clip-configuration)
  - [Video Effects (vfx)](#video-effects-vfx)
  - [Audio Effects (afx)](#audio-effects-afx)
  - [Analysis & Utilities](#analysis--utilities)
  - [File Upload & Download](#file-upload--download)
- [Custom Effects](#custom-effects)
- [Prompt Templates](#prompt-templates)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

### For AI Agents (Remote)

```json
// Add to your MCP client config (e.g. Claude.app/cline)
{
  "mcpServers": {
    "vidmagik": {
      "serverUrl": "https://vidmagik-mcp.fly.dev/mcp"
    }
  }
}
```

**Proper workflow to prompt the agent:**
> "Use the vidmagik tools to create a glitch effect on my video located at /abs/path/to/local/file"

The agent flow:
1. Use browser control tool to open the MCP file picker page
2. Select the video file from your local system (agent gets absolute path)
3. Pass the path to vidmagik tools to process
4. Tools automatically fetch download URL after rendering
5. Agent provides download link for you to retrieve the processed video

### For Local Development

```bash
git clone https://github.com/vizionik25/vidmagik-mcp.git
cd vidmagik-mcp
uv sync
uv run main.py
```

Your local server runs at `http://localhost:8000` (stdio transport by default).

### Docker

```bash
docker compose up --build
```

Files in `./media/` are accessible at `/app/media` inside the container.

---

## Deployment (Fly.io)

The server runs as a single Fly.io machine using Streamable HTTP transport. **Always deploy with `--ha=false`** to prevent Fly.io from spinning up a second machine during rolling updates — Streamable HTTP sessions are in-memory per machine, so two machines would cause session-not-found errors.

### First-time setup

```bash
fly launch          # creates fly.toml and provisions the app
fly deploy --ha=false
```

### Subsequent deploys

```bash
fly deploy --ha=false
```

### Scaling

The app must stay at exactly **1 machine**:

```bash
fly scale count 1 --app vidmagik-mcp
```

### Live URL

```
https://vidmagik-mcp.fly.dev/mcp
```

### fly.toml highlights

```toml
[http_service]
  internal_port = 8080
  auto_stop_machines = false   # keep alive; ephemeral storage clears on redeploy
  min_machines_running = 1

  [http_service.http_options]
    response_timeout = 300
    idle_timeout = 300

  [[http_service.http_options.replay_cache]]
    path_prefix = "/mcp"
    ttl_seconds = 3600
    type = "header"
    name = "mcp-session-id"   # pins sessions to the same machine via fly-replay caching
```

> **Ephemeral storage** — uploaded files and rendered outputs live only in the container's filesystem. They are wiped on each `fly deploy` when the server updates. Download your output files before redeploying.

---

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- FFmpeg (`brew install ffmpeg` / `apt install ffmpeg`)
- ImageMagick (`brew install imagemagick` / `apt install imagemagick`)

### Setup
#### Create a fork of this repository

```bash
git clone https://github.com/your-username/your-app-name.git
cd your-app-name
uv sync
```

### Running locally

```bash
# stdio (default, for local MCP clients)
uv run main.py

# HTTP transport
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

> **Note:** SSE transport is only used automatically as a fallback if HTTP connection fails. It is never directly invoked by the user.

### Docker

```bash
docker compose up --build
```

The `./media` directory is mounted to `/app/media` inside the container.

---

## Environment Configuration

The server requires the following environment variables:

### Required

- **`GITHUB_CLIENT_ID`** — GitHub OAuth application ID  
  Get from [github.com/settings/developers](https://github.com/settings/developers)
- **`GITHUB_CLIENT_SECRET`** — GitHub OAuth application secret

### Optional

- **`SERVER_BASE_URL`** — Base URL for OAuth redirects (default: `http://localhost:8000`)  
  Example: `https://vidmagik-mcp.fly.dev`

### Setup GitHub OAuth (Local & Remote)

1. Go to [github.com/settings/developers](https://github.com/settings/app-manifests) → **New OAuth App**
2. Fill in:
   - Application name: `vidmagik-mcp`
   - Homepage URL: `http://localhost:8000` (or your Fly.io URL)
   - Authorization callback URL: `http://localhost:8000/mcp/auth-callback` (or Fly.io equivalent)
3. Copy **Client ID** and **Client Secret**
4. Create a `.env` file in the project root:

```env
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
SERVER_BASE_URL=http://localhost:8000
```

For **Fly.io**, set secrets via:

```bash
fly secrets set GITHUB_CLIENT_ID=xxx GITHUB_CLIENT_SECRET=yyy SERVER_BASE_URL=https://vidmagik-mcp.fly.dev
```

---

## MCP Client Configuration

### Remote (Fly.io — Streamable HTTP)

```json
{
  "mcpServers": {
    "your-app-name": {
      "serverUrl": "https://your-app-name.fly.dev/mcp"
    }
  }
}
```

### Local (stdio)

```json
{
  "mcpServers": {
    "your-app-name": {
      "command": "uv",
      "args": ["run", "main.py"],
      "cwd": "/path/to/your-app-name"
    }
  }
}
```

### Docker Container (stdio)

For running vidmagik-mcp in a Docker container:

```json
{
  "mcpServers": {
    "vidmagik-docker": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v", "/path/to/local/media:/app/media",
        "-e", "GITHUB_CLIENT_ID=your_client_id",
        "-e", "GITHUB_CLIENT_SECRET=your_client_secret",
        "-e", "SERVER_BASE_URL=http://localhost:8000",
        "vidmagik-mcp:latest"
      ]
    }
  }
}
```

**Explanation:**
- `"command": "docker"` — Use Docker CLI to launch the container
- `"--rm"` — Automatically remove container when it exits
- `"-i"` — Keep stdin open for stdio communication
- `"-v"` — Mount local media directory so agent can access files
- `"-e"` — Pass GitHub OAuth **user authentication** credentials (not API credentials). Users sign in with their GitHub accounts to access the MCP server
- `"vidmagik-mcp:latest"` — Image name (build with `docker compose build`)

**Prerequisites:**
1. Build the image: `docker compose build`
2. Set your GitHub OAuth credentials in the config
3. Ensure local media directory exists: `mkdir -p /path/to/local/media`

---

## Architecture & State Management

### Clip Lifecycle

1. **Create** — Load a file or render content
   ```
   video_file_clip(filename) → clip_id
   ```

2. **Modify** — Apply effects, resize, crop, etc.
   ```
   vfx_fade_in(clip_id, duration=1) → clip_id  (returns modified clip)
   ```

3. **Compose** — Layer or concatenate clips
   ```
   composite_video_clips([clip_id1, clip_id2]) → composite_clip_id
   ```

4. **Output** — Render to file
   ```
   write_videofile(clip_id, "/app/output.mp4") → filename
   ```

5. **Fetch Download URL** — Get link for user (automatically called after write_videofile)
   ```
   get_download_url("/app/output.mp4") → https://vidmagik-mcp.fly.dev/download?file=output.mp4
   ```

### Memory Management

- **Max clips per session**: 30  
- **Stash/Unstash**: Move clips to disk to free RAM, restore later
- **Session isolation**: Each MCP client gets its own in-memory CLIPS dict
- **Ephemeral storage**: Files are lost on `fly deploy` (server updates)

### Clip Types

- `VideoFileClip` — video file (mp4, webm, etc.)
- `ImageClip` — single image or sequence
- `AudioFileClip` — audio track
- `TextClip` — rendered text (requires ImageMagick)
- `ColorClip` — solid color background
- `CompositeVideoClip` — layered clips
- `ConcatenateVideoClip` — joined clips

---

## File Upload & Download Flow

Because the server runs remotely on Fly.io, files must be transferred over HTTP. The recommended agent workflow:

### Agent-Driven File Upload & Processing

1. Agent uses **browser control tool** to open the file picker page at the MCP server URL
2. Agent selects file from local filesystem → receives absolute path
3. Agent passes path to processing tools:
   ```
   video_id = video_file_clip("/abs/path/to/video.mp4")
   glitched = vfx_rgb_sync(video_id, r_offset=(5,0), g_offset=(-5,0))
   output_path = write_videofile(glitched, "/app/output.mp4")
   ```
4. **Automatic** — tools immediately call `get_download_url(output_path)` and provide the HTTPS link to agent
5. Agent shares download link with user

### Manual Upload (if browser tool unavailable)

1. Call `request_file_upload()` → returns `{ session_id, upload_url }`
2. Open `upload_url` in the browser manually
3. Select or drag-and-drop the file — upload streams directly to the server
4. Call `get_uploaded_file(session_id)` → returns the absolute server-side path
5. Pass that path to `video_file_clip()`, `image_clip()`, etc.

### Output & Download

- When `write_videofile()` completes, it automatically provides the download URL
- Agent can immediately pass this to user or embed in a message
- User downloads file directly from the link (valid ~1 hour)

> **Note:** Files are wiped on the next `fly deploy` when the server updates. Download your files before redeploying.

---

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/upload-ui?session=<id>` | Browser-based file upload page (dark-themed, drag-and-drop, real-time progress) |
| `POST` | `/upload?session=<id>` | Binary multipart/form-data upload receiver. Returns `{ filename, size }` |
| `GET` | `/download?file=<filename>` | Serves a file from `/app/` as a browser download (`Content-Disposition: attachment`) |

---

## Tools Reference

All tools return a `clip_id` (UUID string) unless otherwise noted. Pass `clip_id` values between tools to chain operations.

---

### Clip Management

| Tool | Description |
|------|-------------|
| `register_clip(clip)` | Register a clip object and return its ID |
| `get_clip(clip_id)` | Retrieve metadata for a clip by ID |
| `list_clips()` | List all clips currently loaded in memory with their types |
| `delete_clip(clip_id)` | Close and remove a single clip from memory |
| `purge_clips()` | Delete **all** clips in memory in one call. Returns a count confirmation |

---

### IO & Creation

| Tool | Description |
|------|-------------|
| `video_file_clip(filename, audio, fps_source, target_resolution)` | Load a video file |
| `image_clip(filename, duration, transparent)` | Load an image as a clip |
| `image_sequence_clip(sequence, fps, durations, with_mask)` | Create a clip from a list of image paths |
| `text_clip(text, font, font_size, color, ...)` | Render text as a clip (requires ImageMagick) |
| `color_clip(size, color, duration)` | Create a solid color clip |
| `credits_clip(credits_file, width, ...)` | Scrolling credits from a text file |
| `subtitles_clip(filename, encoding, font, font_size, color)` | Render subtitles from an SRT/VTT file |
| `audio_file_clip(filename, buffersize)` | Load an audio file |
| `write_videofile(clip_id, filename, fps, codec, audio_codec, preset, bitrate, threads, ffmpeg_params)` | Render and save a clip as a video file |
| `write_audiofile(clip_id, filename, fps, nbytes, buffersize, codec, bitrate, ffmpeg_params)` | Render and save audio |
| `tools_ffmpeg_extract_subclip(filename, start_time, end_time, targetname)` | Fast lossless trim using ffmpeg directly (no re-encode) |

---

### Compositing & Layout

| Tool | Description |
|------|-------------|
| `composite_video_clips(clip_ids, size, bg_color, use_bgclip)` | Layer multiple clips on top of each other |
| `concatenate_video_clips(clip_ids, method, transition)` | Join clips end-to-end |
| `tools_clips_array(clip_ids_rows, bg_color)` | Arrange clips in a grid. Pass a 2D list of clip IDs (rows × columns) |
| `composite_audio_clips(clip_ids)` | Mix multiple audio clips together |
| `concatenate_audio_clips(clip_ids)` | Join audio clips end-to-end |

---

### Clip Configuration

| Tool | Description |
|------|-------------|
| `subclip(clip_id, start_time, end_time)` | Trim a clip to a time range |
| `set_position(clip_id, x, y, pos_str, relative)` | Set position for compositing (`pos_str`: `"center"`, `"left"`, etc.) |
| `set_audio(clip_id, audio_clip_id)` | Attach an audio clip to a video clip |
| `set_mask(clip_id, mask_clip_id)` | Apply a mask clip |
| `set_start(clip_id, t)` | Set the start time offset |
| `set_end(clip_id, t)` | Set the end time |
| `set_duration(clip_id, t)` | Set the duration |

---

### Video Effects (vfx)

#### Color & Tone
| Tool | Description |
|------|-------------|
| `vfx_black_white(clip_id)` | Convert to grayscale |
| `vfx_invert_colors(clip_id)` | Invert all colors |
| `vfx_gamma_correction(clip_id, gamma)` | Adjust gamma (>1 = brighter, <1 = darker) |
| `vfx_lum_contrast(clip_id, lum, contrast, contrast_threshold)` | Adjust luminosity and contrast |
| `vfx_multiply_color(clip_id, factor)` | Multiply RGB values by a factor |
| `vfx_painting(clip_id, saturation, black)` | Oil-painting style effect |

#### Transitions & Fades
| Tool | Description |
|------|-------------|
| `vfx_fade_in(clip_id, duration)` | Fade in from black |
| `vfx_fade_out(clip_id, duration)` | Fade out to black |
| `vfx_cross_fade_in(clip_id, duration)` | Cross-fade in |
| `vfx_cross_fade_out(clip_id, duration)` | Cross-fade out |
| `vfx_blink(clip_id, duration_on, duration_off)` | Rhythmic on/off blink |
| `vfx_slide_in(clip_id, duration, side)` | Slide in from a screen edge |
| `vfx_slide_out(clip_id, duration, side)` | Slide out to a screen edge |

#### Geometry & Layout
| Tool | Description |
|------|-------------|
| `vfx_resize(clip_id, width, height, scale)` | Resize clip |
| `vfx_crop(clip_id, x1, y1, x2, y2, width, height, x_center, y_center)` | Crop to region |
| `vfx_rotate(clip_id, angle, unit, resample, expand)` | Rotate clip |
| `vfx_mirror_x(clip_id)` | Flip horizontally |
| `vfx_mirror_y(clip_id)` | Flip vertically |
| `vfx_even_size(clip_id)` | Round dimensions to nearest even number (required by some codecs) |
| `vfx_margin(clip_id, margin, color)` | Add a colored border |
| `vfx_scroll(clip_id, w, h, x_speed, y_speed, x_start, y_start)` | Scrolling/panning effect |

#### Time Manipulation
| Tool | Description |
|------|-------------|
| `vfx_multiply_speed(clip_id, factor)` | Speed up or slow down (>1 fast, <1 slow) |
| `vfx_freeze(clip_id, t, freeze_duration, total_duration, padding)` | Freeze a frame |
| `vfx_freeze_region(clip_id, t, region, outside_region, mask_clip_id)` | Freeze a region of the frame |
| `vfx_loop(clip_id, n, duration)` | Loop a clip n times or to a target duration |
| `vfx_make_loopable(clip_id, overlap_duration)` | Blend start and end for seamless looping |
| `vfx_time_mirror(clip_id)` | Reverse the clip |
| `vfx_time_symmetrize(clip_id)` | Play forward then backward |
| `vfx_accel_decel(clip_id, new_duration, abruptness, soonness)` | Ease-in / ease-out speed ramping |
| `vfx_supersample(clip_id, d, nframes)` | Motion blur via temporal supersampling |

#### Masking
| Tool | Description |
|------|-------------|
| `vfx_mask_color(clip_id, color, threshold, stiffness)` | Mask out a color (alpha by proximity to target color) |
| `vfx_masks_and(clip_id, other_clip_id)` | Logical AND of two masks |
| `vfx_masks_or(clip_id, other_clip_id)` | Logical OR of two masks |

#### Custom / Advanced Effects
| Tool | Description |
|------|-------------|
| `vfx_matrix(clip_id, color, density, speed, font_size, chars)` | Matrix-style digital rain overlay |
| `vfx_kaleidoscope(clip_id, n_slices, x, y)` | Radial symmetry kaleidoscope |
| `vfx_kaleidoscope_cube(clip_id, kaleidoscope_params, cube_params)` | Kaleidoscope combined with 3D cube rotation |
| `vfx_rgb_sync(clip_id, r_offset, g_offset, b_offset, r_time_offset, g_time_offset, b_time_offset)` | Chromatic aberration / RGB glitch split |
| `vfx_chroma_key(clip_id, color, threshold, softness)` | Green screen / chroma key removal |
| `vfx_auto_framing(clip_id, target_aspect_ratio, smoothing)` | Face/subject tracking auto-crop for vertical video |
| `vfx_clone_grid(clip_id, n_clones)` | Tile the clip into a grid of clones (2, 4, 8, 16…) |
| `vfx_rotating_cube(clip_id, direction, speed, zoom)` | 3D perspective rotating cube with video mapped to faces |
| `vfx_quad_mirror(clip_id, x, y)` | Four-way mirror symmetry around a centre point |
| `vfx_head_blur(clip_id, fx_code, fy_code, radius, intensity)` | Animated blur following a moving point (math expressions for position) |

---

### Audio Effects (afx)

| Tool | Description |
|------|-------------|
| `afx_multiply_volume(clip_id, factor)` | Scale overall volume |
| `afx_multiply_stereo_volume(clip_id, left_factor, right_factor)` | Scale left/right channels independently |
| `afx_audio_fade_in(clip_id, duration)` | Fade audio in |
| `afx_audio_fade_out(clip_id, duration)` | Fade audio out |
| `afx_audio_delay(clip_id, delay, n_repeats)` | Add echo/delay |
| `afx_audio_loop(clip_id, n, duration)` | Loop audio n times or to duration |
| `afx_audio_normalize(clip_id)` | Normalize audio to peak level |

---

### Analysis & Utilities

| Tool | Description |
|------|-------------|
| `tools_detect_scenes(clip_id, threshold)` | Detect scene cuts, returns list of timestamps |
| `tools_find_video_period(clip_id, fps, start_time, end_time, ...)` | Frequency analysis for repetitive motion patterns |
| `tools_find_audio_period(clip_id, start_time, end_time, ...)` | Tempo/period detection for audio |
| `tools_file_to_subtitles(filename, encoding, fps, ...)` | Parse SRT/VTT subtitle files |
| `tools_check_installation()` | Verify MoviePy, FFmpeg, and ImageMagick are working |
| `tools_drawing_color_gradient(size, color1, color2, ...)` | Generate a gradient image clip |
| `tools_drawing_color_split(size, color1, color2, ...)` | Generate a split-color image clip |

---

### File Upload & Download

| Tool | Description |
|------|-------------|
| `request_file_upload()` | Create an upload session. Returns `{ session_id, upload_url }`. Open `upload_url` in the browser to upload a file |
| `get_uploaded_file(session_id)` | Returns the server-side absolute path once the browser upload completes. Raises if still pending |
| `get_download_url(filename)` | Returns the full HTTPS download URL for a file on the server (e.g. after `write_videofile`). Paste into browser to download |

---

## Custom Effects

vidmagik includes **11 custom video effects** built on MoviePy  for the rendering then uses libraries like numpy and opencv for advanced complex mapping and tracking logic. See [CUSTOM_FX.md](CUSTOM_FX.md) for detailed documentation.

### Built-in Custom FX Tools

| Effect | Tool | Description |
|--------|------|-------------|
| **Matrix Digital Rain** | `vfx_matrix()` | Green/colored character rain overlay with customizable speed, density,charecter color and charecters used |
| **Kaleidoscope** | `vfx_kaleidoscope()` | Radial symmetry mirror effect with adjustable center and slice count |
| **Kaleidoscope + Cube** | `vfx_kaleidoscope_cube()` | Combines kaleidoscope with 3D-Like rotating cube for hybrid effect |
| **RGB Glitch Split** | `vfx_rgb_sync()` | Chromatic aberration via RGB channel offsets (spatial & temporal) |
| **Chroma Key** | `vfx_chroma_key()` | Advanced green screen with threshold and softness for transparency and key color selection |
| **Auto Framing** | `vfx_auto_framing()` | Face/subject tracking auto-crop; converts 16:9 to 9:16 vertical video and tracks the focal point to ensure it stays in frame |
| **Clone Grid** | `vfx_clone_grid()` | Tile clip into 2, 4, 8, 16, 32 or 64 grid of clones |
| **Rotating Cube** | `vfx_rotating_cube()` | 3D-Like perspective cube with video on all six faces that has a figure 8 path of motion and adjustable speed and zoom and an interior point of view |
| **Quad Mirror** | `vfx_quad_mirror()` | Four-way mirror symmetry using an x axis and y axis resulting in thre intersection to be the center point. creating a horizontal mirror that is then vertically mirrored |
| **Typewriter** | `TypeWriter` | Sequential character reveal animation to bve used on text_clips only where each charecter is displayed one after another in sequence as though they were being typed out in real time  |
| **Head Blur** | `vfx_head_blur()` | Animated blur tracking a path defined by math expressions this is the effect to use to blur or obscure a particular portion of a video like someones face it uses mathematical expressions to pinpoint the blur on the image and opencv to track its movements within the frame |

---

## Prompt Templates

8 built-in prompts guide the agent through common workflows:

| Prompt | Description |
|--------|-------------|
| `slideshow_wizard` | Build a professional slideshow from images with transitions |
| `title_card_generator` | Generate title cards with text on solid color backgrounds |
| `glitch_effect_preset` | High-energy RGB split / chromatic aberration glitch aesthetic |
| `auto_framing_for_tiktok` | Convert horizontal 16:9 video to 9:16 vertical with face tracking |
| `matrix_intro_preset` | Classic Matrix code-rain intro overlay |
| `rotating_cube_transition` | 3D spinning cube transition effect |
| `demonstrate_kaleidoscope` | Radial symmetry kaleidoscope animation |
| `demonstrate_kaleidoscope_cube` | Hybrid kaleidoscope + 3D cube combined effect |

### Using Prompts

Prompts are available to LLM clients and guide the agent through structured workflows. Example:

```
// Agent sees this when you ask about TikTok vertical video
Prompt: auto_framing_for_tiktok
Description: Convert horizontal 16:9 video to 9:16 vertical with face tracking
→ Tool: vfx_auto_framing(target_aspect_ratio=0.5625, smoothing=0.9)
```

---

## Project Structure

```
vidmagik-mcp/
├── main.py                      # FastMCP server, all 90+ tools, HTTP routes
├── pyproject.toml              # Python dependencies (moviepy, fastmcp, etc.)
├── Dockerfile                  # Production image build
├── docker-compose.yml          # Local development docker setup
├── fly.toml                    # Fly.io deployment config (16GB 8-core machine)
│
├── custom_fx/                  # 11 custom video effects
│   ├── __init__.py
│   ├── matrix.py              # Digital rain overlay
│   ├── kaleidoscope.py        # Radial symmetry
│   ├── kaleidoscope_cube.py   # Kaleidoscope + 3D cube
│   ├── rgb_sync.py            # Glitch / chromatic aberration
│   ├── chroma_key.py          # Green screen
│   ├── auto_framing.py        # Face tracking & vertical crop
│   ├── clone_grid.py          # Grid clones
│   ├── rotating_cube.py       # 3D cube effect
│   ├── quad_mirror.py         # Four-way mirror
│   └── typewriter.py          # Text reveal animation
│
├── fonts/                      # Font files for text rendering
├── tests/
│   └── test_e2e.py            # ~1100 line end-to-end test suite
├── CUSTOM_FX.md               # Detailed effect documentation
├── README.md                  # This file
└── LICENSE                    # MIT
```

---

## Troubleshooting

### `ImportError: No module named 'moviepy'`

Install dependencies:
```bash
uv sync
```

### `MoviePy error: MOVIEPY_FFMPEG_PATH not found`

Ensure FFmpeg is installed:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt install ffmpeg

# Verify
ffmpeg -version
```

### TextClip or text rendering fails

ImageMagick must be installed and properly configured:

```bash
# macOS
brew install imagemagick

# Ubuntu/Debian
apt install imagemagick

# Diagnose
convert -version
```

If ImageMagick policy blocks text operations:
```bash
# Fix policy.xml (Linux)
sed -i 's/domain="path" rights="none"/domain="path" rights="read|write"/g' /etc/ImageMagick-6/policy.xml
```

The Dockerfile includes this fix automatically.

### `RuntimeError: Maximum number of clips (30) reached`

Clips are stored in memory. Free space:
```
delete_clip(clip_id)        # Free one specific clip
purge_clips()               # Clear all clips

stash_clip(clip_id)         # Move to disk temporarily
unstash_clip(stash_id)      # Restore from disk
```

### Files disappear after deploying to Fly.io

Storage is ephemeral (container-local). **Download files before redeploying:**

```python
write_videofile(clip_id, "/app/output.mp4")
url = get_download_url("/app/output.mp4")
# → Paste URL in browser to download immediately
```

### Session not found (Fly.io)

The server must run on exactly **1 machine**. Check:
```bash
fly scale count 1 --app vidmagik-mcp
```

If scaling up, session IDs won't persist across machines (Streamable HTTP is per-machine).

### GitHub OAuth fails

1. Verify environment variables:
   ```bash
   fly secrets list
   # Should show GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, SERVER_BASE_URL
   ```

2. Check redirect URL in [github.com/settings/developers](https://github.com/settings/developers):
   - Should match `SERVER_BASE_URL + /mcp/auth-callback`
   - Example: `https://vidmagik-mcp.fly.dev/mcp/auth-callback`

3. Test locally:
   ```bash
   export GITHUB_CLIENT_ID=xxx
   export GITHUB_CLIENT_SECRET=yyy
   uv run main.py
   ```

---

## Contributing

### Running Tests

```bash
pytest tests/test_e2e.py -v
```

### Adding a Custom Effect

1. Create a new effect class in `custom_fx/new_effect.py`. Refer to existing effects in `custom_fx/` (e.g., `matrix.py`, `kaleidoscope.py`) as implementation examples.

2. Export in `custom_fx/__init__.py`:
   ```python
   from .new_effect import MyEffect
   ```

3. Add a wrapper tool in `main.py`:
   ```python
   @mcp.tool
   def vfx_my_effect(clip_id: str, param1, param2):
       """Description of my effect."""
       clip = get_clip(clip_id)
       effect = MyEffect(clip, param1, param2)
       return register_clip(effect)
   ```

4. Add tests in `tests/test_e2e.py` (see existing custom FX tests).

5. Document in [CUSTOM_FX.md](CUSTOM_FX.md).

### Deployment Checklist

Before `fly launch`:

- [ ] All tests pass: `pytest tests/test_e2e.py`
- [ ] No untracked files: `git status`
- [ ] Secrets set: `fly secrets list` includes `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `SERVER_BASE_URL`
- [ ] Machine count verified: `fly scale count 1`

It's Best Practice to use checklist before re-deploy also. Remember everytime you deploy to use the '--ha=false'
flag or Fly will spin up 2 machines and when you try to refresh youll get an error about non-matching sessions.
this is due to moviepy only renders from within emphereal storage (memory) and since this is deployed remotely and not meant for storing our files only workaround to this is not feasiable due resource costs unless you were build something with the intentions of offering as part of some SaaS or Hosted Agent/s Product.

---

## License

MIT — See [LICENSE](LICENSE) for details.


