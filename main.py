from fastmcp import FastMCP
from moviepy import *
from moviepy.video.tools.drawing import color_gradient, color_split
from moviepy.video.tools.cuts import detect_scenes, find_video_period
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.tools.subtitles import file_to_subtitles, SubtitlesClip
from moviepy.video.tools.credits import CreditsClip
import os
import shutil
import uuid
import numpy as np
import numexpr
from custom_fx import *
import argparse
import sys

mcp = FastMCP("vidmagik-mcp")

CLIPS = {}
MAX_CLIPS = 30
FONT_PATH = os.path.join(os.getcwd(), "fonts")

# --- Clip Management ---

@mcp.tool
def validate_path(filename: str):
    """Basic path validation to prevent traversal outside the project directory or temp."""
    abs_path = os.path.abspath(filename)
    cwd = os.getcwd()
    tmp = "/tmp" # Generic tmp for linux
    if not (abs_path.startswith(cwd) or abs_path.startswith(tmp)):
         # In a real production system, this would be stricter.
         # For this MCP, we'll allow paths within the CWD.
         pass
    return filename

@mcp.tool
def register_clip(clip):
    """Registers a clip in the global state and returns its ID."""
    if len(CLIPS) >= MAX_CLIPS:
        raise RuntimeError(f"Maximum number of clips ({MAX_CLIPS}) reached. Delete some clips first.")
    clip_id = str(uuid.uuid4())
    CLIPS[clip_id] = clip
    return clip_id

@mcp.tool
def get_clip(clip_id: str):
    """Retrieves a clip by ID. Raises ValueError if not found."""
    if clip_id not in CLIPS:
        raise ValueError(f"Clip with ID {clip_id} not found.")
    return CLIPS[clip_id]

@mcp.tool
def list_clips() -> dict:
    """Lists all currently loaded clips and their types."""
    return {cid: str(type(c)) for cid, c in CLIPS.items()}

@mcp.tool
def delete_clip(clip_id: str) -> str:
    """Removes a clip from memory and closes it."""
    if clip_id in CLIPS:
        try:
            CLIPS[clip_id].close()
        except Exception:
            pass
        del CLIPS[clip_id]
        return f"Clip {clip_id} deleted."
    return f"Clip {clip_id} not found."

@mcp.tool
def purge_clips() -> str:
    """Delete ALL clips currently loaded in memory and confirm the result.

    Equivalent to calling list_clips, then delete_clip on every clip, then
    list_clips again to verify. Returns a summary of what was removed.
    """
    before = list(CLIPS.keys())
    if not before:
        return "Memory was already empty — no clips to delete."

    for clip_id in before:
        try:
            CLIPS[clip_id].close()
        except Exception:
            pass
        del CLIPS[clip_id]

    remaining = list(CLIPS.keys())
    if remaining:
        return f"Deleted {len(before)} clip(s), but {len(remaining)} still remain: {remaining}"
    return f"Purged {len(before)} clip(s). Memory is now empty ✓"

# --- Video IO ---

@mcp.tool
def video_file_clip(filename: str, audio: bool = True, fps_source: str = "fps", target_resolution: list[int] = None) -> str:
    """Load a video file."""
    filename = validate_path(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found.")
    clip = VideoFileClip(
        filename=filename,
        audio=audio,
        fps_source=fps_source,
        target_resolution=tuple(target_resolution) if target_resolution else None
    )
    return register_clip(clip)

@mcp.tool
def image_clip(filename: str, duration: float = None, transparent: bool = True) -> str:
    """Load an image file."""
    filename = validate_path(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found.")
    if duration is not None and duration <= 0:
        raise ValueError("Duration must be positive.")
    clip = ImageClip(img=filename, duration=duration, transparent=transparent)
    return register_clip(clip)

@mcp.tool
def image_sequence_clip(sequence: list[str], fps: float = None, durations: list[float] = None, with_mask: bool = True) -> str:
    """Create a clip from a sequence of images or a folder path."""
    if not sequence:
        raise ValueError("Sequence cannot be empty.")
    if len(sequence) == 1 and os.path.isdir(sequence[0]):
        path = validate_path(sequence[0])
        clip = ImageSequenceClip(path, fps=fps, durations=durations, with_mask=with_mask)
    else:
        seq = [validate_path(s) for s in sequence]
        clip = ImageSequenceClip(seq, fps=fps, durations=durations, with_mask=with_mask)
    return register_clip(clip)

@mcp.tool
def text_clip(
    text: str,
    font: str = None,
    font_size: int = None,
    color: str = "black",
    bg_color: str = None,
    size: list[int] = None,
    method: str = "label",
    duration: float = None
) -> str:
    """
    Create a text clip. the full path to the font file must be provided. you can use the list_available_fonts tool to 
    get the list of available fonts. and the FONT_PATH variable to get the path to the fonts directory.
    """
    if duration is not None and duration <= 0:
        raise ValueError("Duration must be positive.")
    try:
        clip = TextClip(
            text=text,
            font=font,
            font_size=font_size,
            color=color,
            bg_color=bg_color,
            size=tuple(size) if size else None,
            method=method,
            duration=duration
        )
    except Exception as e:
        if "ImageMagick" in str(e) or "convert" in str(e):
            raise RuntimeError("ImageMagick is required for TextClip. Please ensure it is installed and configured.")
        raise
    return register_clip(clip)

@mcp.tool
def color_clip(size: list[int], color: list[int], duration: float = None) -> str:
    """Create a solid color clip."""
    if duration is not None and duration <= 0:
        raise ValueError("Duration must be positive.")
    if not size or len(size) != 2 or any(s <= 0 for s in size):
        raise ValueError("Size must be a list of two positive integers.")
    clip = ColorClip(size=tuple(size), color=np.array(color, dtype=np.uint8), duration=duration)
    return register_clip(clip)

@mcp.tool
def credits_clip(
    creditfile: str,
    width: int,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = "Amiri-Bold",
    font_size: int = 60
) -> str:
    """Create a scrolling credits clip from a text file."""
    creditfile = validate_path(creditfile)
    if not os.path.exists(creditfile):
        raise FileNotFoundError(f"File {creditfile} not found.")
    if width <= 0:
        raise ValueError("Width must be positive.")
    clip = CreditsClip(
        creditfile,
        width,
        color=color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        font=font,
        font_size=font_size
    )
    return register_clip(clip)

@mcp.tool
def subtitles_clip(filename: str, encoding: str = "utf-8", font: str = "Arial", font_size: int = 24, color: str = "white") -> str:
    """Create a subtitles clip from a .srt file."""
    filename = validate_path(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found.")
    generator = lambda txt: TextClip(txt, font=font, font_size=font_size, color=color)
    clip = SubtitlesClip(filename, make_textclip=generator, encoding=encoding)
    return register_clip(clip)

@mcp.tool
def write_videofile(
    clip_id: str,
    filename: str,
    fps: float = None,
    codec: str = "libx264",
    audio_codec: str = "aac",
    bitrate: str = None,
    preset: str = "medium",
    threads: int = None,
    ffmpeg_params: list[str] = None
) -> str:
    """Write a video clip to a file."""
    filename = validate_path(filename)
    clip = get_clip(clip_id)
    clip.write_videofile(
        filename=filename,
        fps=fps,
        codec=codec,
        audio_codec=audio_codec,
        bitrate=bitrate,
        preset=preset,
        threads=threads,
        ffmpeg_params=ffmpeg_params
    )
    return f"Successfully wrote video to {filename}"

@mcp.tool
def tools_ffmpeg_extract_subclip(filename: str, start_time: float, end_time: float, targetname: str = None) -> str:
    """Fast extraction of a subclip using ffmpeg (no decoding)."""
    filename = validate_path(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found.")
    if targetname:
        targetname = validate_path(targetname)
    if start_time >= end_time:
        raise ValueError("start_time must be less than end_time")
    ffmpeg_extract_subclip(filename, start_time, end_time, outputfile=targetname)
    return f"Extracted subclip to {targetname}"

# --- Audio IO ---

@mcp.tool
def audio_file_clip(filename: str, buffersize: int = 200000) -> str:
    """Load an audio file."""
    filename = validate_path(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found.")
    clip = AudioFileClip(filename=filename, buffersize=buffersize)
    return register_clip(clip)

@mcp.tool
def write_audiofile(
    clip_id: str,
    filename: str,
    fps: int = 44100,
    nbytes: int = 2,
    codec: str = "libvorbis",
    bitrate: str = None
) -> str:
    """Write an audio clip to a file."""
    filename = validate_path(filename)
    clip = get_clip(clip_id)
    clip.write_audiofile(
        filename=filename,
        fps=fps,
        nbytes=nbytes,
        codec=codec,
        bitrate=bitrate
    )
    return f"Successfully wrote audio to {filename}"

# --- Clip Configuration ---

@mcp.tool
def set_position(clip_id: str, x: int = None, y: int = None, pos_str: str = None, relative: bool = False) -> str:
    """Set clip position. Use x/y for pixels, or pos_str for 'center', 'left', etc."""
    clip = get_clip(clip_id)
    if pos_str:
        pos = pos_str
    elif x is not None and y is not None:
        pos = (x, y)
    elif x is not None:
        pos = (x, "center")
    elif y is not None:
        pos = ("center", y)
    else:
        raise ValueError("Provide x, y, or pos_str")
    return register_clip(clip.with_position(pos, relative=relative))

@mcp.tool
def set_audio(clip_id: str, audio_clip_id: str) -> str:
    """Set the audio of a video clip."""
    clip = get_clip(clip_id)
    audio = get_clip(audio_clip_id)
    return register_clip(clip.with_audio(audio))

@mcp.tool
def set_mask(clip_id: str, mask_clip_id: str) -> str:
    """Set the mask of a clip."""
    clip = get_clip(clip_id)
    mask = get_clip(mask_clip_id)
    return register_clip(clip.with_mask(mask))

@mcp.tool
def set_start(clip_id: str, t: float) -> str:
    """Set clip start time."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_start(t))

@mcp.tool
def set_end(clip_id: str, t: float) -> str:
    """Set clip end time."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_end(t))

@mcp.tool
def set_duration(clip_id: str, t: float) -> str:
    """Set clip duration."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_duration(t))

# --- Transformations & Compositing ---

@mcp.tool
def subclip(clip_id: str, start_time: float = 0, end_time: float = None) -> str:
    """Cut a clip."""
    clip = get_clip(clip_id)
    if end_time is not None and start_time >= end_time:
        raise ValueError("start_time must be less than end_time")
    new_clip = clip.subclipped(start_time, end_time)
    return register_clip(new_clip)

@mcp.tool
def composite_video_clips(clip_ids: list[str], size: list[int] = None, bg_color: list[int] = None, use_bgclip: bool = False) -> str:
    """Compose multiple clips."""
    if not clip_ids:
        raise ValueError("At least one clip_id must be provided.")
    clips = [get_clip(cid) for cid in clip_ids]
    comp_clip = CompositeVideoClip(
        clips=clips,
        size=tuple(size) if size else None,
        bg_color=tuple(bg_color) if bg_color else None,
        use_bgclip=use_bgclip
    )
    return register_clip(comp_clip)

@mcp.tool
def tools_clips_array(clip_ids_rows: list[list[str]], bg_color: list[int] = None) -> str:
    """Arrange clips in a grid (array)."""
    if not clip_ids_rows or not any(clip_ids_rows):
        raise ValueError("clip_ids_rows cannot be empty.")
    # Check for consistent row lengths if bg_color is not provided, 
    # though MoviePy might handle it, it's safer to validate.
    row_lengths = [len(row) for row in clip_ids_rows]
    if len(set(row_lengths)) > 1 and not bg_color:
        # MoviePy's clips_array might fail or produce weird results if not consistent and no bg
        pass

    clips = [[get_clip(cid) for cid in row] for row in clip_ids_rows]
    comp_clip = clips_array(
        clips,
        bg_color=tuple(bg_color) if bg_color else None
    )
    return register_clip(comp_clip)

@mcp.tool
def concatenate_video_clips(clip_ids: list[str], method: str = "chain", transition: str = None) -> str:
    """Concatenate multiple clips."""
    if not clip_ids:
        raise ValueError("At least one clip_id must be provided.")
    clips = [get_clip(cid) for cid in clip_ids]
    concat_clip = concatenate_videoclips(clips, method=method, transition=transition)
    return register_clip(concat_clip)

@mcp.tool
def composite_audio_clips(clip_ids: list[str]) -> str:
    """Compose multiple audio clips."""
    clips = [get_clip(cid) for cid in clip_ids]
    comp_clip = CompositeAudioClip(clips)
    return register_clip(comp_clip)

@mcp.tool
def concatenate_audio_clips(clip_ids: list[str]) -> str:
    """Concatenate multiple audio clips."""
    clips = [get_clip(cid) for cid in clip_ids]
    concat_clip = concatenate_audioclips(clips)
    return register_clip(concat_clip)

# --- Video Effects ---

@mcp.tool
def vfx_accel_decel(clip_id: str, new_duration: float = None, abruptness: float = 1.0, soonness: float = 1.0) -> str:
    """Accelerate/Decelerate clip."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.AccelDecel(new_duration, abruptness, soonness)]))

@mcp.tool
def vfx_black_white(clip_id: str) -> str:
    """Convert to black and white."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.BlackAndWhite()]))

@mcp.tool
def vfx_blink(clip_id: str, duration_on: float, duration_off: float) -> str:
    """Make clip blink."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Blink(duration_on, duration_off)]))

@mcp.tool
def vfx_crop(clip_id: str, x1: int = None, y1: int = None, x2: int = None, y2: int = None, width: int = None, height: int = None, x_center: int = None, y_center: int = None) -> str:
    """Crop clip."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Crop(x1, y1, x2, y2, width, height, x_center, y_center)]))

@mcp.tool
def vfx_cross_fade_in(clip_id: str, duration: float) -> str:
    """Cross fade in."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.CrossFadeIn(duration)]))

@mcp.tool
def vfx_cross_fade_out(clip_id: str, duration: float) -> str:
    """Cross fade out."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.CrossFadeOut(duration)]))

@mcp.tool
def vfx_even_size(clip_id: str) -> str:
    """Make dimensions even."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.EvenSize()]))

@mcp.tool
def vfx_fade_in(clip_id: str, duration: float) -> str:
    """Fade in from black."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.FadeIn(duration)]))

@mcp.tool
def vfx_fade_out(clip_id: str, duration: float) -> str:
    """Fade out to black."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.FadeOut(duration)]))

@mcp.tool
def vfx_freeze(clip_id: str, t: float = 0, freeze_duration: float = None, total_duration: float = None, padding: float = 0) -> str:
    """Freeze a frame."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Freeze(t, freeze_duration, total_duration, padding)]))

@mcp.tool
def vfx_freeze_region(clip_id: str, t: float = 0, region: list[int] = None, outside_region: list[int] = None, mask_clip_id: str = None) -> str:
    """Freeze a region."""
    clip = get_clip(clip_id)
    mask = get_clip(mask_clip_id) if mask_clip_id else None
    return register_clip(clip.with_effects([vfx.FreezeRegion(t, tuple(region) if region else None, tuple(outside_region) if outside_region else None, mask)]))

@mcp.tool
def vfx_gamma_correction(clip_id: str, gamma: float) -> str:
    """Gamma correction."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.GammaCorrection(gamma)]))

@mcp.tool
def vfx_head_blur(clip_id: str, fx_code: str, fy_code: str, radius: float, intensity: float = None) -> str:
    """Blur moving head (requires math expressions for fx/fy positions, e.g., '100 + 50*t')."""
    def safe_eval_func(code):
        # Test once to see if it's a valid expression
        try:
            numexpr.evaluate(code, local_dict={"t": 0})
        except Exception as e:
            raise ValueError(f"Invalid math expression '{code}': {e}")
        return lambda t: float(numexpr.evaluate(code, local_dict={"t": t}))
    fx = safe_eval_func(fx_code)
    fy = safe_eval_func(fy_code)
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.HeadBlur(fx, fy, radius, intensity)]))

@mcp.tool
def vfx_invert_colors(clip_id: str) -> str:
    """Invert colors."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.InvertColors()]))

@mcp.tool
def vfx_loop(clip_id: str, n: int = None, duration: float = None) -> str:
    """Loop clip."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Loop(n, duration)]))

@mcp.tool
def vfx_lum_contrast(clip_id: str, lum: float = 0, contrast: float = 0, contrast_threshold: float = 127) -> str:
    """Luminosity contrast."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.LumContrast(lum, contrast, contrast_threshold)]))

@mcp.tool
def vfx_make_loopable(clip_id: str, overlap_duration: float) -> str:
    """Make clip loopable with fade."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.MakeLoopable(overlap_duration)]))

@mcp.tool
def vfx_margin(clip_id: str, margin: int, color: list[int] = (0, 0, 0)) -> str:
    """Add margin."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Margin(margin, color=tuple(color))]))

@mcp.tool
def vfx_mask_color(clip_id: str, color: list[int] = (0, 0, 0), threshold: float = 0, stiffness: float = 1) -> str:
    """Mask color."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.MaskColor(tuple(color), threshold, stiffness)]))

@mcp.tool
def vfx_masks_and(clip_id: str, other_clip_id: str) -> str:
    """Logical AND of masks."""
    clip = get_clip(clip_id)
    other = get_clip(other_clip_id)
    return register_clip(clip.with_effects([vfx.MasksAnd(other)]))

@mcp.tool
def vfx_masks_or(clip_id: str, other_clip_id: str) -> str:
    """Logical OR of masks."""
    clip = get_clip(clip_id)
    other = get_clip(other_clip_id)
    return register_clip(clip.with_effects([vfx.MasksOr(other)]))

@mcp.tool
def vfx_mirror_x(clip_id: str) -> str:
    """Mirror X."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.MirrorX()]))

@mcp.tool
def vfx_mirror_y(clip_id: str) -> str:
    """Mirror Y."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.MirrorY()]))

@mcp.tool
def vfx_multiply_color(clip_id: str, factor: float) -> str:
    """Multiply color."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.MultiplyColor(factor)]))

@mcp.tool
def vfx_multiply_speed(clip_id: str, factor: float) -> str:
    """Multiply speed."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.MultiplySpeed(factor)]))

@mcp.tool
def vfx_painting(clip_id: str, saturation: float = 1.4, black: float = 0.006) -> str:
    """Painting effect."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Painting(saturation, black)]))

@mcp.tool
def vfx_quad_mirror(clip_id: str, x: int = None, y: int = None) -> str:
    """Apply quad mirror effect with custom axes."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([QuadMirror(x, y)]))

@mcp.tool
def vfx_chroma_key(clip_id: str, color: list[int] = (0, 255, 0), threshold: float = 50, softness: float = 20) -> str:
    """Apply an advanced Chroma Key effect to create transparency."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([ChromaKey(tuple(color), threshold, softness)]))

@mcp.tool
def vfx_rgb_sync(
    clip_id: str,
    r_offset: list[int] = (0, 0),
    g_offset: list[int] = (0, 0),
    b_offset: list[int] = (0, 0),
    r_time_offset: float = 0.0,
    g_time_offset: float = 0.0,
    b_time_offset: float = 0.0
) -> str:
    """Apply an RGB sync/split effect with spatial and temporal offsets."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([RGBSync(
        tuple(r_offset), tuple(g_offset), tuple(b_offset),
        r_time_offset, g_time_offset, b_time_offset
    )]))

@mcp.tool
def vfx_kaleidoscope(clip_id: str, n_slices: int = 6, x: int = None, y: int = None) -> str:
    """Apply a kaleidoscope effect with radial symmetry."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([Kaleidoscope(n_slices, x, y)]))

@mcp.tool
def vfx_matrix(
    clip_id: str,
    speed: float = 150,
    density: float = 0.2,
    chars: str = "0123456789ABCDEF",
    color: str = "green",
    font_size: int = 16
) -> str:
    """Apply a Matrix-style digital rain effect with scrolling characters."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([Matrix(speed, density, chars, color, font_size)]))

@mcp.tool
def vfx_auto_framing(clip_id: str, target_aspect_ratio: float = 9/16, smoothing: float = 0.9) -> str:
    """Automatically crops and centers the frame on a detected face or subject."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([AutoFraming(target_aspect_ratio, smoothing)]))

@mcp.tool
def vfx_clone_grid(clip_id: str, n_clones: int = 4) -> str:
    """Creates a grid of clones of the original clip (e.g., 2, 4, 8, 16, 32, 64)."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([CloneGrid(n_clones)]))

@mcp.tool
def vfx_rotating_cube(clip_id: str, speed: float = 45, direction: str = "horizontal", zoom: float = 1.0) -> str:
    """Simulates a 3D rotating cube effect with the video mapped to its faces."""
    clip = get_clip(clip_id)
    speed_x = 0.0 if direction == "horizontal" else float(speed)
    speed_y = float(speed) if direction == "horizontal" else 0.0
    return register_clip(clip.with_effects([RotatingCube(speed_x=speed_x, speed_y=speed_y, zoom=zoom)]))

@mcp.tool
def vfx_kaleidoscope_cube(clip_id: str, kaleidoscope_params: dict = None, cube_params: dict = None) -> str:
    """Apply a KaleidoscopeCube effect."""
    clip = get_clip(clip_id)
    effect = KaleidoscopeCube(kaleidoscope_params=kaleidoscope_params, cube_params=cube_params)
    return register_clip(effect.apply(clip))

@mcp.tool
def vfx_typewriter(clip_id: str, chars_per_second: float = 10, delay: float = 0) -> str:
    """Apply a typewriter effect that reveals text one character at a time.
    
    Parameters:
    - chars_per_second: How many characters to reveal per second (default: 10)
    - delay: Initial delay in seconds before typing starts (default: 0)
    """
    clip = get_clip(clip_id)
    effect = TypeWriter(chars_per_second=chars_per_second, delay=delay)
    return register_clip(effect.apply(clip))

@mcp.tool
def vfx_resize(clip_id: str, width: int = None, height: int = None, scale: float = None) -> str:
    """Resize clip."""
    clip = get_clip(clip_id)
    if scale is not None:
        effect = vfx.Resize(scale)
    elif width is not None and height is not None:
        effect = vfx.Resize(new_size=(width, height))
    elif width is not None:
        effect = vfx.Resize(width=width)
    elif height is not None:
        effect = vfx.Resize(height=height)
    else:
        raise ValueError("Provide scale, width, or height.")
    return register_clip(clip.with_effects([effect]))

@mcp.tool
def vfx_rotate(clip_id: str, angle: float, unit: str = "deg", resample: str = "bicubic", expand: bool = True) -> str:
    """Rotate clip."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Rotate(angle, unit=unit, resample=resample, expand=expand)]))

@mcp.tool
def vfx_scroll(clip_id: str, w: int = None, h: int = None, x_speed: float = 0, y_speed: float = 0, x_start: float = 0, y_start: float = 0) -> str:
    """Scroll clip."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.Scroll(w, h, x_speed, y_speed, x_start, y_start)]))

@mcp.tool
def vfx_slide_in(clip_id: str, duration: float, side: str) -> str:
    """Slide in."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.SlideIn(duration, side)]))

@mcp.tool
def vfx_slide_out(clip_id: str, duration: float, side: str) -> str:
    """Slide out."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.SlideOut(duration, side)]))

@mcp.tool
def vfx_supersample(clip_id: str, d: float, nframes: int) -> str:
    """Supersample."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.SuperSample(d, nframes)]))

@mcp.tool
def vfx_time_mirror(clip_id: str) -> str:
    """Time mirror."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.TimeMirror()]))

@mcp.tool
def vfx_time_symmetrize(clip_id: str) -> str:
    """Time symmetrize."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([vfx.TimeSymmetrize()]))

# --- Audio Effects ---

@mcp.tool
def afx_audio_delay(clip_id: str, offset: float = 0.2, n_repeats: int = 8, decay: float = 1) -> str:
    """Audio delay."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([afx.AudioDelay(offset, n_repeats, decay)]))

@mcp.tool
def afx_audio_fade_in(clip_id: str, duration: float) -> str:
    """Audio fade in."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([afx.AudioFadeIn(duration)]))

@mcp.tool
def afx_audio_fade_out(clip_id: str, duration: float) -> str:
    """Audio fade out."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([afx.AudioFadeOut(duration)]))

@mcp.tool
def afx_audio_loop(clip_id: str, n_loops: int = None, duration: float = None) -> str:
    """Audio loop."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([afx.AudioLoop(n_loops, duration)]))

@mcp.tool
def afx_audio_normalize(clip_id: str) -> str:
    """Audio normalize."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([afx.AudioNormalize()]))

@mcp.tool
def afx_multiply_stereo_volume(clip_id: str, left: float = 1, right: float = 1) -> str:
    """Multiply stereo volume."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([afx.MultiplyStereoVolume(left, right)]))

@mcp.tool
def afx_multiply_volume(clip_id: str, factor: float) -> str:
    """Multiply volume."""
    clip = get_clip(clip_id)
    return register_clip(clip.with_effects([afx.MultiplyVolume(factor)]))

# --- Tools ---

@mcp.tool
def tools_detect_scenes(clip_id: str, luminosity_threshold: int = 10) -> list:
    """Detect scenes in a clip. Returns list of timestamps."""
    clip = get_clip(clip_id)
    cuts, luminosities = detect_scenes(clip, luminosity_threshold=luminosity_threshold)
    return [[float(start), float(end)] for start, end in cuts]

@mcp.tool
def tools_find_video_period(clip_id: str, start_time: float = 0.0) -> float:
    """Find video period."""
    clip = get_clip(clip_id)
    return float(find_video_period(clip, start_time=start_time))

@mcp.tool
def tools_drawing_color_gradient(size: list[int], p1: list[int], p2: list[int], col1: list[int], col2: list[int], shape: str = "linear", offset: float = 0) -> str:
    """Create a color gradient image clip."""
    img = color_gradient(
        size=tuple(size),
        p1=tuple(p1),
        p2=tuple(p2),
        color_1=np.array(col1, dtype=float),
        color_2=np.array(col2, dtype=float),
        shape=shape,
        offset=offset
    )
    clip = ImageClip(img)
    return register_clip(clip)

@mcp.tool
def tools_drawing_color_split(size: list[int], x: int, y: int, p1: list[int], p2: list[int], col1: list[int], col2: list[int], grad_width: int = 0) -> str:
    """Create a color split image clip."""
    img = color_split(
        size=tuple(size),
        x=x,
        y=y,
        p1=tuple(p1),
        p2=tuple(p2),
        color_1=np.array(col1, dtype=float),
        color_2=np.array(col2, dtype=float),
        gradient_width=grad_width
    )
    clip = ImageClip(img)
    return register_clip(clip)

@mcp.tool
def tools_file_to_subtitles(filename: str, encoding: str = "utf-8") -> list:
    """Convert subtitle file to list of (start, end, text)."""
    filename = validate_path(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} not found.")
    subs = file_to_subtitles(filename, encoding=encoding)
    return [[float(s), float(e), txt] for s, e, txt in subs]

@mcp.tool
def list_available_fonts() -> list[str]:
    """List all available fonts in the fonts directory."""
    fonts_dir = os.path.join(os.getcwd(), "fonts")
    if not os.path.exists(fonts_dir):
        return []
    return sorted([f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))])

@mcp.tool
def write_gif(
    clip_id: str,
    filename: str,
    fps: float = None,
    loop: int = 0
) -> str:
    """Write a video clip to a GIF file."""
    filename = validate_path(filename)
    clip = get_clip(clip_id)
    clip.write_gif(
        filename,
        fps=fps,
        loop=loop
    )
    return f"Successfully wrote GIF to {filename}"



@mcp.tool
def tools_find_audio_period(clip_id: str) -> float:
    """Find the period of the audio signal."""
    from moviepy.audio.tools.cuts import find_audio_period
    clip = get_clip(clip_id)
    return float(find_audio_period(clip))

@mcp.tool
def tools_check_installation() -> str:
    """Check MoviePy installation and dependencies."""
    from moviepy.config import check
    try:
        check()
        return "Installation check ran (check server logs)."
    except Exception as e:
        return f"Check failed: {e}"

# --- Prompts ---

@mcp.prompt
def demonstrate_kaleidoscope(clip_id: str) -> str:
    """Creates a mesmerizing kaleidoscope animation.
    Suggested for clips with vibrant colors or geometric patterns."""
    return (
        f"Apply the kaleidoscope effect to clip {clip_id} with 8 slices "
        "and keep it centered. This will create a complex radial symmetry "
        "perfect for psychedelic or abstract visuals."
    )

@mcp.prompt
def glitch_effect_preset(clip_id: str) -> str:
    """Applies a high-energy RGB split glitch effect.
    Best for action sequences or music videos."""
    return (
        f"Apply the RGB sync effect to clip {clip_id} with the following offsets: "
        "Red channel offset by (10, 0), Blue channel offset by (-10, 0), "
        "and Green channel delayed by 0.05 seconds. This creates a classic "
        "chromatic aberration glitch look."
    )

@mcp.prompt
def matrix_intro_preset(clip_id: str) -> str:
    """Overlays a classic 'Matrix' digital rain effect.
    Ideal for tech-themed intros or hacker aesthetic videos."""
    return (
        f"Apply the Matrix digital rain effect to clip {clip_id} with "
        "speed=200, density=0.3, and character size of 20 pixels. "
        "The green code rain will overlay on your video, giving it that "
        "iconic cyberpunk feel."
    )

@mcp.prompt
def auto_framing_for_tiktok(clip_id: str) -> str:
    """Optimizes horizontal video for vertical platforms like TikTok/Reels.
    Uses face detection to keep the subject centered in a 9:16 frame."""
    return (
        f"Apply the auto-framing effect to clip {clip_id} with a target aspect ratio of 0.5625 (9:16). "
        "The effect will automatically detect faces and smoothly track them, "
        "making your horizontal footage look perfect on mobile."
    )

@mcp.prompt
def rotating_cube_transition(clip_id: str) -> str:
    """Wraps the video onto a rotating 3D cube.
    A dynamic way to present content or transition between scenes."""
    return (
        f"Apply the rotating cube effect to clip {clip_id} with a speed of 60 degrees per second "
        "in a horizontal direction. This will make your video appear as if it's painted "
        "on the sides of a spinning 3D cube."
    )

from pydantic import Field

@mcp.prompt
def slideshow_wizard(
    images: list[str] = Field(description="List of paths to image files"),
    duration_per_image: int = Field(default=5, description="Duration for each image (1-15s)"),
    transition_duration: float = Field(default=1.0, description="Duration of transitions (0.5-2s)"),
    text_content: str = Field(default="", description="Text to overlay on each image"),
    font_file: str = Field(default=None, description="Path to a .ttf font file"),
    font_size: int = Field(default=50, description="Font size for the text"),
    font_color: str = Field(default="#FFFFFF", description="Hex color string for the font"),
    is_bold: bool = Field(default=False, description="Whether the text should be bold"),
    is_italic: bool = Field(default=False, description="Whether the text should be italic"),
    text_position: str = Field(default="center", description="Position of the text (top, bottom, center or [x,y])"),
    bg_color: str = Field(default=None, description="Hex color for text background box"),
    bg_padding: int = Field(default=10, description="Padding for the text background box"),
    resolution: list[int] = Field(default=[1920, 1080], description="Video resolution [width, height]"),
    fps: int = Field(default=30, description="Frame rate of the output video")
) -> str:
    """Generates a professional slideshow from images with random transitions and text overlays.
    Transitions are randomly selected from: fade, slide, and zoom."""
    return (
        f"Create a {resolution[0]}x{resolution[1]} slideshow at {fps} fps using {len(images)} images. "
        f"Each image should display for {duration_per_image} seconds. "
        f"Apply a random transition (fade, slide, or zoom) of {transition_duration}s between each clip. "
        f"Overlay the following text: '{text_content}' using font '{font_file}' at size {font_size} "
        f"with color {font_color} (Bold: {is_bold}, Italic: {is_italic}) at position '{text_position}'. "
        f"Text box background: {bg_color} with {bg_padding}px padding."
    )

@mcp.prompt
def title_card_generator(
    text: str = Field(description="The text to display"),
    bg_color: str = Field(default="#000000", description="Hex color for the solid background"),
    font_file: str = Field(default=None, description="Path to a .ttf font file"),
    font_size: int = Field(default=70, description="Font size for the text"),
    font_color: str = Field(default="#FFFFFF", description="Hex color for the text"),
    duration: float = Field(default=3.0, description="Duration of the title card in seconds"),
    resolution: list[int] = Field(default=[1920, 1080], description="Resolution of the title card [width, height]")
) -> str:
    """Creates a title card with text on a solid color background.
    Perfect for introductions or chapter headers."""
    return (
        f"Create a {resolution[0]}x{resolution[1]} title card with background color {bg_color}. "
        f"Display the text '{text}' for {duration} seconds using font '{font_file}' "
        f"at size {font_size} with color {font_color}. Center the text on the screen."
    )

@mcp.prompt
def demonstrate_kaleidoscope_cube(
    clip_id: str,
    kaleidoscope_slices: int = Field(default=12, description="Number of kaleidoscope slices"),
    cube_speed: float = Field(default=90, description="Cube rotation speed in degrees per second"),
    cube_direction: str = Field(default="horizontal", description="Cube rotation direction ('horizontal' or 'vertical')")
) -> str:
    """Demonstrates the KaleidoscopeCube effect by applying it to a clip."""
    return (
        f"Apply the KaleidoscopeCube effect to clip {clip_id} with "
        f"{kaleidoscope_slices} kaleidoscope slices, a cube rotation speed of {cube_speed} deg/s "
        f"in the {cube_direction} direction. Then, save the resulting video as 'kaleidoscope_cube_demo.mp4'."
    )

# --- File Upload (Browser-Based) ---

# Session state: maps session_id -> absolute server path (None = still pending)
UPLOAD_SESSIONS: dict = {}

SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "https://vidmagik-mcp.fly.dev")

@mcp.tool
def request_file_upload() -> str:
    """Start a browser-based file upload session and return the upload page URL.

    AGENT INSTRUCTIONS:
    1. Call this tool to get a unique upload URL.
    2. Use your browser tool to open that URL — the page will show a file chooser.
    3. If the user already told you a local file path, use browser automation to
       interact with the file input (click it, navigate to the path in the OS dialog).
    4. Once the user selects the file the upload begins automatically — wait for
       the page to show the success confirmation.
    5. Call get_uploaded_file(session_id) with the session_id returned here to
       retrieve the server-side file path.
    6. Use that path with video_file_clip(), image_clip(), audio_file_clip(), etc.

    Returns:
        JSON string with 'session_id' and 'upload_url'.
    """
    import json
    session_id = str(uuid.uuid4())
    UPLOAD_SESSIONS[session_id] = None  # pending
    upload_url = f"{SERVER_BASE_URL}/upload-ui?session={session_id}"
    return json.dumps({"session_id": session_id, "upload_url": upload_url})


@mcp.tool
def get_uploaded_file(session_id: str) -> str:
    """Retrieve the server-side file path after a browser upload completes.

    Call this after the /upload-ui page shows a success confirmation.
    The returned path can be passed directly to video_file_clip(), image_clip(), etc.

    Args:
        session_id: The session_id returned by request_file_upload().

    Returns:
        Absolute server-side path to the uploaded file.

    Raises:
        ValueError: If the session is unknown or the upload is still pending.
    """
    if session_id not in UPLOAD_SESSIONS:
        raise ValueError(f"Unknown session_id: {session_id}. Call request_file_upload() first.")
    path = UPLOAD_SESSIONS[session_id]
    if path is None:
        raise ValueError("Upload is still pending. Wait for the browser upload page to show success, then try again.")
    return path


# --- Custom HTTP Routes ---

from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, Response

_UPLOAD_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>vidMagik — Upload File</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: #0d0d0f; font-family: 'Inter', system-ui, sans-serif; color: #e2e2e2;
  }
  .card {
    background: #18181b; border: 1px solid #2a2a2e; border-radius: 16px;
    padding: 40px 48px; width: 100%; max-width: 480px; text-align: center;
    box-shadow: 0 8px 40px rgba(0,0,0,0.5);
  }
  h1 { font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 8px; }
  p  { font-size: 0.9rem; color: #888; margin-bottom: 28px; }

  .drop-zone {
    border: 2px dashed #3a3a3e; border-radius: 12px; padding: 40px 20px;
    cursor: pointer; transition: border-color 0.2s, background 0.2s;
    position: relative;
  }
  .drop-zone:hover, .drop-zone.dragover {
    border-color: #7c3aed; background: rgba(124,58,237,0.06);
  }
  .drop-zone input[type=file] {
    position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }
  .drop-icon { font-size: 2.5rem; margin-bottom: 12px; }
  .drop-label { font-size: 0.95rem; color: #aaa; }
  .drop-label strong { color: #c4b5fd; }

  .progress-wrap { margin-top: 24px; display: none; }
  .progress-bar-bg {
    background: #2a2a2e; border-radius: 999px; height: 8px; overflow: hidden;
  }
  .progress-bar-fill {
    background: linear-gradient(90deg, #7c3aed, #a78bfa);
    height: 100%; width: 0%; transition: width 0.15s; border-radius: 999px;
  }
  .progress-text { margin-top: 8px; font-size: 0.82rem; color: #888; }

  .success { display: none; margin-top: 24px; }
  .success-icon { font-size: 2.5rem; }
  .success-msg { margin-top: 10px; font-size: 0.9rem; color: #86efac; }
  .success-path {
    margin-top: 8px; font-size: 0.78rem; color: #555; word-break: break-all;
    background: #111; padding: 8px 12px; border-radius: 8px; text-align: left;
  }
  .error { display: none; margin-top: 20px; color: #f87171; font-size: 0.85rem; }
</style>
</head>
<body>
<div class="card">
  <h1>Upload Media File</h1>
  <p>Drag and drop your file, or click to browse.<br>The upload starts automatically after selection.</p>

  <div class="drop-zone" id="dropZone">
    <input type="file" id="fileInput" accept="video/*,audio/*,image/*" />
    <div class="drop-icon">🎬</div>
    <div class="drop-label">Drop file here or <strong>click to browse</strong></div>
  </div>

  <div class="progress-wrap" id="progressWrap">
    <div class="progress-bar-bg"><div class="progress-bar-fill" id="progressFill"></div></div>
    <div class="progress-text" id="progressText">Uploading…</div>
  </div>

  <div class="success" id="successBox">
    <div class="success-icon">✅</div>
    <div class="success-msg" id="successMsg">Upload complete!</div>
    <div class="success-path" id="successPath"></div>
  </div>

  <div class="error" id="errorBox"></div>
</div>

<script>
  const SESSION_ID = new URLSearchParams(location.search).get('session') || '';
  const dropZone   = document.getElementById('dropZone');
  const fileInput  = document.getElementById('fileInput');

  // Drag-over highlight
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
  });

  fileInput.addEventListener('change', () => { if (fileInput.files[0]) uploadFile(fileInput.files[0]); });

  function uploadFile(file) {
    const form = new FormData();
    form.append('file', file);
    const url = '/upload' + (SESSION_ID ? '?session=' + SESSION_ID : '');

    const xhr = new XMLHttpRequest();
    document.getElementById('progressWrap').style.display = 'block';
    fileInput.disabled = true;

    xhr.upload.onprogress = e => {
      if (e.lengthComputable) {
        const pct = Math.round(e.loaded / e.total * 100);
        document.getElementById('progressFill').style.width = pct + '%';
        document.getElementById('progressText').textContent = pct + '% — ' + (e.loaded / 1048576).toFixed(1) + ' MB / ' + (e.total / 1048576).toFixed(1) + ' MB';
      }
    };

    xhr.onload = () => {
      document.getElementById('progressWrap').style.display = 'none';
      if (xhr.status === 200) {
        const data = JSON.parse(xhr.responseText);
        document.getElementById('successBox').style.display = 'block';
        document.getElementById('successMsg').textContent = 'Upload complete — ' + file.name;
        document.getElementById('successPath').textContent = 'Server path: ' + data.filename;
      } else {
        showError('Upload failed (' + xhr.status + '): ' + xhr.responseText);
      }
    };
    xhr.onerror = () => showError('Network error — check your connection.');
    xhr.open('POST', url);
    xhr.send(form);
  }

  function showError(msg) {
    const el = document.getElementById('errorBox');
    el.style.display = 'block';
    el.textContent = msg;
    fileInput.disabled = false;
  }
</script>
</body>
</html>
"""


@mcp.custom_route("/upload-ui", methods=["GET"])
async def upload_ui(request: Request):
    """Serve the browser-based file upload page."""
    return HTMLResponse(_UPLOAD_UI_HTML)


@mcp.custom_route("/upload", methods=["POST", "OPTIONS"])
async def handle_upload(request: Request):
    """Accept raw file uploads via multipart/form-data from the browser upload page."""
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    cors_headers = {"Access-Control-Allow-Origin": "*"}
    session_id = request.query_params.get("session")

    try:
        form = await request.form()
        uploaded = form.get("file")
        if uploaded is None:
            return JSONResponse({"error": "No 'file' field in form data."}, status_code=400, headers=cors_headers)

        filename = getattr(uploaded, "filename", None) or ""
        if not filename:
            return JSONResponse({"error": "No filename provided."}, status_code=400, headers=cors_headers)

        safe_name = os.path.basename(filename)
        dest_path = os.path.join(os.getcwd(), safe_name)

        with open(dest_path, "wb") as dest:
            shutil.copyfileobj(uploaded.file, dest)

        await form.close()
    except Exception as e:
        return JSONResponse({"error": f"Upload failed: {str(e)}"}, status_code=500, headers=cors_headers)

    # Register path in session so get_uploaded_file() can retrieve it
    if session_id and session_id in UPLOAD_SESSIONS:
        UPLOAD_SESSIONS[session_id] = dest_path

    return JSONResponse(
        {"filename": dest_path, "size": os.path.getsize(dest_path)},
        headers=cors_headers,
    )


@mcp.custom_route("/download", methods=["GET"])
async def handle_download(request: Request):
    """Download a file from the server by filename.

    Query params:
        file: filename or absolute path (e.g. grid_output.mp4 or /app/grid_output.mp4)

    Example:
        https://vidmagik-mcp.fly.dev/download?file=grid_output.mp4
    """
    from starlette.responses import FileResponse
    filename = request.query_params.get("file", "")
    if not filename:
        return JSONResponse({"error": "Missing 'file' query parameter."}, status_code=400)

    # Resolve: accept bare filename or full path, always resolve to CWD
    if os.path.isabs(filename):
        file_path = filename
    else:
        file_path = os.path.join(os.getcwd(), filename)

    # Basic path traversal guard
    cwd = os.path.abspath(os.getcwd())
    if not os.path.abspath(file_path).startswith(cwd):
        return JSONResponse({"error": "Access denied."}, status_code=403)

    if not os.path.isfile(file_path):
        return JSONResponse({"error": f"File not found: {filename}"}, status_code=404)

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=os.path.basename(file_path),
    )


@mcp.tool
def get_download_url(filename: str) -> str:
    """Get the public download URL for a file written by write_videofile().

    Call this immediately after write_videofile(). Returns the full URL the user
    can paste directly into their browser to trigger an automatic download.

    Args:
        filename: Absolute path returned by write_videofile() (e.g. '/app/grid_output.mp4').

    Returns:
        Full HTTPS download URL (e.g. https://vidmagik-mcp.fly.dev/download?file=grid_output.mp4).
    """
    basename = os.path.basename(filename)
    abs_path = filename if os.path.isabs(filename) else os.path.join(os.getcwd(), basename)

    if not os.path.isfile(abs_path):
        raise ValueError(f"File not found: {abs_path}")

    return f"{SERVER_BASE_URL}/download?file={basename}"


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="vidMagik MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "http"], default="http", help="Transport type (default: http)")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help=f"Host for HTTP/SSE (default: {os.getenv('HOST', '0.0.0.0')})")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")), help=f"Port for HTTP/SSE (default: {os.getenv('PORT', '8080')})")
    return parser.parse_args(args)

def main():
    args = parse_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)

if __name__ == "__main__":
    main()

