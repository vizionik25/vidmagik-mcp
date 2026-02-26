# Custom MoviePy Effects

This document provides documentation for the custom effects implemented in the `custom_fx/` directory of the `mcp-moviepy` project.

## Table of Contents
1. [Matrix Digital Rain](#matrix-digital-rain)
2. [Kaleidoscope](#kaleidoscope)
3. [RGB Sync (Glitch)](#rgb-sync-glitch)
4. [Chroma Key (Green Screen)](#chroma-key-green-screen)
5. [Auto Framing](#auto-framing)
6. [Clone Grid](#clone-grid)
7. [Quad Mirror](#quad-mirror)
8. [Typewriter](#typewriter)

---

## Matrix Digital Rain
**File:** `custom_fx/matrix.py`  
**Class:** `Matrix`

Overlays a "Matrix" style digital rain animation on the clip. The rain features falling characters with a bright leading edge and a fading trail.

### Parameters
- `speed` (float, default: `150`): Speed of falling characters in pixels per second.
- `density` (float, default: `0.2`): Probability (0.0 to 1.0) that a column will contain a falling drop.
- `chars` (str, default: `"0123456789ABCDEF"`): The character set used for the digital rain.
- `color` (str, default: `"green"`): Color of the rain. Supported options: `red`, `green`, `blue`, `white`.
- `font_size` (int, default: `16`): Size of the characters.

---

## Kaleidoscope
**File:** `custom_fx/kaleidoscope.py`  
**Class:** `Kaleidoscope`

Creates a radial symmetry effect by taking a wedge of the source image and mirroring/rotating it around a center point.

### Parameters
- `n_slices` (int, default: `6`): Number of radial slices. Even numbers are recommended for seamless mirroring.
- `x` (int, optional): Horizontal center of the effect. Defaults to the clip's center.
- `y` (int, optional): Vertical center of the effect. Defaults to the clip's center.

---

## RGB Sync (Glitch)
**File:** `custom_fx/rgb_sync.py`  
**Class:** `RGBSync`

Splits the RGB channels and applies spatial and/or temporal offsets to create a chromatic aberration or glitch effect.

### Parameters
- `r_offset`, `g_offset`, `b_offset` (tuple, default: `(0, 0)`): (x, y) pixel offsets for each channel.
- `r_time_offset`, `g_time_offset`, `b_time_offset` (float, default: `0.0`): Time offset in seconds for each channel.

---

## Chroma Key (Green Screen)
**File:** `custom_fx/chroma_key.py`  
**Class:** `ChromaKey`

An advanced chroma key effect that generates a transparency mask based on Euclidean distance from a target color.

### Parameters
- `color` (tuple, default: `(0, 255, 0)`): Target RGB color to remove.
- `threshold` (float, default: `50`): Distance threshold below which pixels are fully transparent.
- `softness` (float, default: `20`): Range over which pixels transition from transparent to opaque.

---

## Auto Framing
**File:** `custom_fx/auto_framing.py`  
**Class:** `AutoFraming`

Automatically crops and centers the frame on a detected face or subject. This is particularly useful for converting horizontal (16:9) video to vertical (9:16) for social media while ensuring the speaker remains in frame. 
It uses Haar Cascades for face detection and applies exponential smoothing to prevent jumpy camera movements.

### Parameters
- `target_aspect_ratio` (float, default: `0.5625` (9/16)): The desired aspect ratio of the output.
- `smoothing` (float, default: `0.9`): Smoothing factor (0.0 to 1.0). Higher values result in smoother, slower camera tracking.
- `focus_func` (callable, optional): A custom function to determine the focus point if face detection is not desired or sufficient.

---

## Clone Grid
**File:** `custom_fx/clone_grid.py`  
**Class:** `CloneGrid`

Creates a grid of clones of the original clip. The effect automatically determines the optimal number of rows and columns to fit the requested number of clones into the original frame dimensions.

### Parameters
- `n_clones` (int, default: `4`): The number of clones to display. Recommended values are powers of 2 (2, 4, 8, 16, 32, 64).

---

## Rotating Cube
**File:** `custom_fx/rotating_cube.py`  
**Class:** `RotatingCube`

Simulates a 3D rotating cube effect with the video mapped to all six faces. This enhanced version supports simultaneous multi-axis rotation, optional quad-mirroring, and dynamic motion paths.

### Parameters
- `speed_x` (float, default: `45`): Rotation speed around the horizontal X-axis in degrees per second.
- `speed_y` (float, default: `30`): Rotation speed around the vertical Y-axis in degrees per second.
- `zoom` (float, default: `1.0`): Perspective zoom factor.
- `mirror` (bool, default: `True`): Whether to apply a quad-mirror symmetry effect to the video before mapping it to the cube faces.
- `motion_radius` (float, default: `0.1`): Radius of the circular/elliptical motion path (as a fraction of screen size).
- `motion_speed` (float, default: `20`): Speed of the cube's motion along the path in degrees per second.

---

## Quad Mirror
**File:** `custom_fx/quad_mirror.py`  
**Class:** `QuadMirror`

Mirrors the clip both horizontally and vertically based on a custom center point, effectively creating four mirrored versions of the source quadrant.

### Parameters
- `x` (int, optional): Horizontal axis for mirroring. Defaults to the clip's center.
- `y` (int, optional): Vertical axis for mirroring. Defaults to the clip's center.

---

## Typewriter
**File:** `custom_fx/typewriter.py`  
**Class:** `TypeWriter`

A typewriter effect that progressively reveals text one character at a time, simulating the appearance of text being typed on screen. This effect works by creating text clips for each progressive state of the text and compositing them with precise timing. Perfect for creating engaging text animations, subtitles, or on-screen messages.

### Parameters
- `chars_per_second` (float, default: `10`): The speed of typing in characters per second. Higher values make the text appear faster.
- `delay` (float, default: `0`): Initial delay in seconds before the typing animation begins. Useful for synchronizing with other events in your video.

### Usage Example
```python
# Create a text clip
text_clip = text_clip("Hello, World!", font="Arial", font_size=50, color="white", duration=5)

# Apply typewriter effect
typewriter_clip = vfx_typewriter(text_clip_id, chars_per_second=8, delay=0.5)

# The text will start appearing after 0.5 seconds, with each character appearing in ~0.125 seconds
```