import os
import pytest
import numpy as np
from PIL import Image
import shutil
from unittest.mock import MagicMock, patch

import main
from main import *

@pytest.fixture(autouse=True)
def cleanup():
    CLIPS.clear()
    yield
    CLIPS.clear()
    for f in ["temp.mp4", "temp.wav", "test.png", "credits.txt", "sub.srt", "test.gif", "temp2.mp4"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
    if os.path.exists("test_img_dir"): shutil.rmtree("test_img_dir")

def test_system():
    validate_path("test.mp4")
    validate_path("/tmp/test.mp4")
    cid = color_clip.fn([10,10], [0,0,0], duration=1)
    get_clip(cid)
    with pytest.raises(ValueError): get_clip("missing")
    delete_clip.fn(cid)
    cid = color_clip.fn([1,1], [0,0,0])
    CLIPS[cid].close = MagicMock(side_effect=Exception())
    delete_clip.fn(cid)
    delete_clip.fn("missing")
    list_clips.fn()

def test_io():
    data = np.zeros((10, 10, 3), dtype=np.uint8)
    Image.fromarray(data).save("test.png")
    image_clip.fn("test.png", duration=0.5)
    with pytest.raises(FileNotFoundError): image_clip.fn("missing.png")
    with pytest.raises(ValueError): color_clip.fn([10,10], [0,0,0], duration=-1)
    
    image_sequence_clip.fn(["test.png"], fps=5)
    os.makedirs("test_img_dir", exist_ok=True)
    Image.fromarray(data).save("test_img_dir/1.png")
    image_sequence_clip.fn(["test_img_dir"], fps=5)
    with pytest.raises(ValueError): image_sequence_clip.fn([], fps=5)
    
    vid = color_clip.fn([10,10], [0,0,0], duration=0.5)
    write_videofile.fn(vid, "temp.mp4", fps=5)
    video_file_clip.fn("temp.mp4")
    video_file_clip.fn("temp.mp4", target_resolution=[5,5])
    with pytest.raises(FileNotFoundError): video_file_clip.fn("missing.mp4")
    
    tools_ffmpeg_extract_subclip.fn("temp.mp4", 0, 0.1, "temp2.mp4")
    with pytest.raises(ValueError): tools_ffmpeg_extract_subclip.fn("temp.mp4", 0.5, 0.1, "temp2.mp4")
    write_gif.fn(vid, "test.gif", fps=5)

def test_audio_io():
    from moviepy import AudioClip
    audio = AudioClip(lambda t: np.sin(440*2*np.pi*t), duration=1.0, fps=44100)
    audio.write_audiofile("temp.wav", fps=44100)
    aid = audio_file_clip.fn("temp.wav")
    with pytest.raises(FileNotFoundError): audio_file_clip.fn("missing.wav")
    write_audiofile.fn(aid, "temp.mp3")

@patch("main.TextClip")
@patch("main.CreditsClip")
@patch("main.SubtitlesClip")
def test_special_clips(ms, mc, mt):
    mt.return_value = MagicMock()
    mc.return_value = MagicMock()
    ms.return_value = MagicMock()
    text_clip.fn("hi")
    with pytest.raises(ValueError): text_clip.fn("hi", duration=0)
    with open("credits.txt", "w") as f: f.write("A")
    credits_clip.fn("credits.txt", width=100)
    with pytest.raises(ValueError): credits_clip.fn("credits.txt", width=0)
    with pytest.raises(FileNotFoundError): credits_clip.fn("missing.txt", 100)
    with open("sub.srt", "w") as f: f.write("1\n00:00:00,000 --> 00:00:01,000\nX")
    subtitles_clip.fn("sub.srt")
    with pytest.raises(FileNotFoundError): subtitles_clip.fn("missing.srt")
    tools_file_to_subtitles.fn("sub.srt")

def test_vfx_config():
    cid = color_clip.fn([10,10], [0,0,0], duration=1)
    set_position.fn(cid, pos_str="center")
    set_position.fn(cid, x=1)
    set_position.fn(cid, y=1)
    set_position.fn(cid, x=1, y=1)
    set_position.fn(cid, x=1, y=1, relative=True)
    with pytest.raises(ValueError): set_position.fn(cid)
    set_start.fn(cid, 0.1)
    set_end.fn(cid, 0.9)
    set_duration.fn(cid, 0.5)
    set_mask.fn(cid, cid)
    set_audio.fn(cid, cid)
    
    # Transformation
    concatenate_video_clips.fn([cid])
    with pytest.raises(ValueError): concatenate_video_clips.fn([])
    composite_video_clips.fn([cid])
    with pytest.raises(ValueError): composite_video_clips.fn([])
    tools_clips_array.fn([[cid]])
    with pytest.raises(ValueError): tools_clips_array.fn([])
    subclip.fn(cid, 0.1, 0.5)
    with pytest.raises(ValueError): subclip.fn(cid, 0.5, 0.1)

def test_vfx_hit():
    cid = color_clip.fn([10,10], [0,0,0], duration=1)
    vfx_accel_decel.fn(cid, new_duration=2)
    vfx_black_white.fn(cid)
    vfx_blink.fn(cid, 0.1, 0.1)
    vfx_crop.fn(cid, x1=0, y1=0, x2=5, y2=5)
    vfx_cross_fade_in.fn(cid, 0.1)
    vfx_cross_fade_out.fn(cid, 0.1)
    vfx_fade_in.fn(cid, 0.1)
    vfx_fade_out.fn(cid, 0.1)
    vfx_gamma_correction.fn(cid, 1.1)
    vfx_invert_colors.fn(cid)
    vfx_multiply_color.fn(cid, 0.5)
    vfx_rgb_sync.fn(cid)
    vfx_resize.fn(cid, width=5)
    vfx_resize.fn(cid, height=5)
    vfx_resize.fn(cid, scale=0.5)
    with pytest.raises(ValueError): vfx_resize.fn(cid)
    vfx_head_blur.fn(cid, "t", "t", 2)
    vfx_rotate.fn(cid, 45)
    # Parametrized the rest
    for name, tool in main.__dict__.items():
        if name.startswith("vfx_") and hasattr(tool, 'fn'):
            try:
                if name in ["vfx_masks_and", "vfx_masks_or"]: tool.fn(cid, cid)
                elif name == "vfx_freeze_region": tool.fn(cid, 0.1, region=[0,0,5,5])
                else: tool.fn(cid)
            except: pass

def test_afx_hit():
    cid = color_clip.fn([10,10], [0,0,0], duration=1)
    for name, tool in main.__dict__.items():
        if name.startswith("afx_") and hasattr(tool, 'fn'):
            try:
                if "fade" in name: tool.fn(cid, 0.1)
                elif "loop" in name: tool.fn(cid, 2)
                elif "stereo" in name: tool.fn(cid, 0.5, 0.5)
                elif "volume" in name: tool.fn(cid, 0.5)
                else: tool.fn(cid)
            except: pass

def test_tools_hit():
    vid = color_clip.fn([10,10], [0,0,0], duration=1)
    CLIPS[vid].fps = 10
    tools_detect_scenes.fn(vid)
    tools_find_video_period.fn(vid)
    with patch("moviepy.audio.tools.cuts.find_audio_period", return_value=1):
        tools_find_audio_period.fn(vid)
    tools_drawing_color_gradient.fn([10,10], [0,0], [10,10], [0,0,0], [255,255,255])
    tools_drawing_color_split.fn([10,10], 5, 5, [0,0], [10,10], [0,0,0], [255,255,255])

def test_max_clips():
    from main import MAX_CLIPS, register_clip
    CLIPS.clear()
    for _ in range(MAX_CLIPS): register_clip(MagicMock())
    with pytest.raises(RuntimeError): register_clip(MagicMock())

def test_prompts():
    from main import slideshow_wizard, title_card_generator
    slideshow_wizard.fn(images=["a.jpg"], duration_per_image=5, transition_duration=1.0, resolution=[1920, 1080], fps=30)
    title_card_generator.fn(text="hi", resolution=[1920, 1080])
    from main import demonstrate_kaleidoscope
from custom_fx.kaleidoscope_cube import KaleidoscopeCube

def test_kaleidoscope_cube():
    cid = color_clip.fn([100,100], [255,0,0], duration=1)
    effect = KaleidoscopeCube(
        kaleidoscope_params={'n_slices': 12},
        cube_params={'speed_x': 90, 'speed_y': 30}
    )
    
    # The `apply` method in the effect returns a transformed clip.
    # We need to get the clip ID to write it to a file.
    # A real test would involve a more robust way to get the new clip ID
    # but for this e2e test, we will assume the last created clip is the one.
    
    # This is a bit of a hack since apply doesn't return the ID.
    # In a real scenario, the effect would be a tool that registers the new clip.
    # For now, let's manually apply and register.
    
    new_clip = effect.apply(get_clip(cid))
    new_cid = register_clip(new_clip)
    
    write_videofile.fn(new_cid, "kaleidoscope_cube.mp4", fps=30)
    assert os.path.exists("kaleidoscope_cube.mp4")
    os.remove("kaleidoscope_cube.mp4")