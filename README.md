# vidMagik-mcp

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![MoviePy](https://img.shields.io/badge/MoviePy-2.2+-orange.svg)](https://zulko.github.io/moviepy/)
[![Deployed on Fly.io](https://img.shields.io/badge/Deployed%20on-Fly.io-blueviolet)](https://fly.io)

A Model Context Protocol (MCP) server that provides a comprehensive interface to [MoviePy](https://zulko.github.io/moviepy/) for AI-driven video editing. Hosted remotely on **Fly.io** using Streamable HTTP transport.

- **90 MCP tools** — clip management, effects, compositing, audio, analysis, file upload & download
- **8 prompt templates** — built-in workflow guides for common video editing tasks
- **3 HTTP endpoints** — file upload UI, binary upload receiver, file download

---

## Table of Contents

- [Deployment (Fly.io)](#deployment-flyio)
- [Local Development](#local-development)
- [MCP Client Configuration](#mcp-client-configuration)
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
- [Prompt Templates](#prompt-templates)
- [State Management](#state-management)

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
  auto_stop_machines = false   # keep alive; ephemeral storage clears on suspend/redeploy
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

> **Ephemeral storage** — uploaded files and rendered outputs live only in the container's filesystem. They are wiped on each `fly deploy` or when the machine suspends due to inactivity. Download your output files before redeploying.

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
uv run main.py --transport http --host 0.0.0.0 --port 8080

# SSE transport
uv run main.py --transport sse --host 0.0.0.0 --port 8080
```

### Docker

```bash
docker compose up --build
```

The `./media` directory is mounted to `/app/media` inside the container.

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

---

## File Upload & Download Flow

Because the server runs remotely on Fly.io, files must be transferred over HTTP. The recommended agent workflow:

### Upload

1. Call `request_file_upload()` → returns `{ session_id, upload_url }`
2. Open `upload_url` in the browser (agent uses its browser tool, or user opens manually)
3. Select or drag-and-drop the file — upload streams directly to the server
4. Call `get_uploaded_file(session_id)` → returns the absolute server-side path
5. Pass that path to `video_file_clip()`, `image_clip()`, etc.

### Render & Download

1. Call `write_videofile(clip_id, "/app/output.mp4")`
2. Call `get_download_url("/app/output.mp4")` → returns the full URL
3. Paste that URL into your browser — the file downloads automatically

> Files are wiped on the next `fly deploy` or after the machine suspends (~1 hour of inactivity).

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

---

## State Management

- **Clip IDs** — every tool that creates or modifies a clip returns a UUID string (`clip_id`)
- **Chaining** — pass `clip_id` to subsequent tools to build pipelines
- **Memory** — clips are stored in-memory on the server; max 30 clips per session
- **Cleanup** — use `delete_clip(clip_id)` to free a single clip, or `purge_clips()` to wipe all clips at once
- **Persistence** — no persistent storage; all clips and files are lost on redeploy or machine suspend

---

## License

MIT
