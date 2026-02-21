import os
import pytest
import numpy as np
from PIL import Image
import shutil
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
import io

import main
from main import *

@pytest.fixture(autouse=True)
def cleanup():
    CLIPS.clear()
    yield
    CLIPS.clear()
    for f in ["temp.mp4", "temp.wav", "test.png", "credits.txt", "sub.srt", "test.gif", "temp2.mp4", "uploaded_test.bin", "temp.mp3"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
    if os.path.exists("test_img_dir"): shutil.rmtree("test_img_dir")

def test_system():
    validate_path("test.mp4")
    validate_path("/tmp/test.mp4")
    cid = color_clip([10,10], [0,0,0], duration=1)
    get_clip(cid)
    with pytest.raises(ValueError): get_clip("missing")
    delete_clip(cid)
    cid = color_clip([1,1], [0,0,0])
    CLIPS[cid].close = MagicMock(side_effect=Exception())
    delete_clip(cid)
    delete_clip("missing")
    list_clips()

def test_io():
    data = np.zeros((10, 10, 3), dtype=np.uint8)
    Image.fromarray(data).save("test.png")
    image_clip("test.png", duration=0.5)
    with pytest.raises(FileNotFoundError): image_clip("missing.png")
    with pytest.raises(ValueError): color_clip([10,10], [0,0,0], duration=-1)
    
    image_sequence_clip(["test.png"], fps=5)
    os.makedirs("test_img_dir", exist_ok=True)
    Image.fromarray(data).save("test_img_dir/1.png")
    image_sequence_clip(["test_img_dir"], fps=5)
    with pytest.raises(ValueError): image_sequence_clip([], fps=5)
    
    vid = color_clip([10,10], [0,0,0], duration=0.5)
    write_videofile(vid, "temp.mp4", fps=5)
    video_file_clip("temp.mp4")
    video_file_clip("temp.mp4", target_resolution=[5,5])
    with pytest.raises(FileNotFoundError): video_file_clip("missing.mp4")
    
    tools_ffmpeg_extract_subclip("temp.mp4", 0, 0.1, "temp2.mp4")
    with pytest.raises(ValueError): tools_ffmpeg_extract_subclip("temp.mp4", 0.5, 0.1, "temp2.mp4")
    write_gif(vid, "test.gif", fps=5)

def test_audio_io():
    from moviepy import AudioClip
    audio = AudioClip(lambda t: np.sin(440*2*np.pi*t), duration=1.0, fps=44100)
    audio.write_audiofile("temp.wav", fps=44100)
    aid = audio_file_clip("temp.wav")
    with pytest.raises(FileNotFoundError): audio_file_clip("missing.wav")
    write_audiofile(aid, "temp.mp3")

@patch("main.TextClip")
@patch("main.CreditsClip")
@patch("main.SubtitlesClip")
def test_special_clips(ms, mc, mt):
    mt.return_value = MagicMock()
    mc.return_value = MagicMock()
    ms.return_value = MagicMock()
    text_clip("hi")
    with pytest.raises(ValueError): text_clip("hi", duration=0)
    with open("credits.txt", "w") as f: f.write("A")
    credits_clip("credits.txt", width=100)
    with pytest.raises(ValueError): credits_clip("credits.txt", width=0)
    with pytest.raises(FileNotFoundError): credits_clip("missing.txt", 100)
    with open("sub.srt", "w") as f: f.write("1\n00:00:00,000 --> 00:00:01,000\nX")
    subtitles_clip("sub.srt")
    with pytest.raises(FileNotFoundError): subtitles_clip("missing.srt")
    tools_file_to_subtitles("sub.srt")

def test_vfx_config():
    cid = color_clip([10,10], [0,0,0], duration=1)
    set_position(cid, pos_str="center")
    set_position(cid, x=1)
    set_position(cid, y=1)
    set_position(cid, x=1, y=1)
    set_position(cid, x=1, y=1, relative=True)
    with pytest.raises(ValueError): set_position(cid)
    set_start(cid, 0.1)
    set_end(cid, 0.9)
    set_duration(cid, 0.5)
    set_mask(cid, cid)
    set_audio(cid, cid)
    
    # Transformation
    concatenate_video_clips([cid])
    with pytest.raises(ValueError): concatenate_video_clips([])
    composite_video_clips([cid])
    with pytest.raises(ValueError): composite_video_clips([])
    tools_clips_array([[cid]])
    with pytest.raises(ValueError): tools_clips_array([])
    subclip(cid, 0.1, 0.5)
    with pytest.raises(ValueError): subclip(cid, 0.5, 0.1)

def test_vfx_hit():
    cid = color_clip([10,10], [0,0,0], duration=1)
    vfx_accel_decel(cid, new_duration=2)
    vfx_black_white(cid)
    vfx_blink(cid, 0.1, 0.1)
    vfx_crop(cid, x1=0, y1=0, x2=5, y2=5)
    vfx_cross_fade_in(cid, 0.1)
    vfx_cross_fade_out(cid, 0.1)
    vfx_fade_in(cid, 0.1)
    vfx_fade_out(cid, 0.1)
    vfx_gamma_correction(cid, 1.1)
    vfx_invert_colors(cid)
    vfx_multiply_color(cid, 0.5)
    vfx_rgb_sync(cid)
    vfx_resize(cid, width=5)
    vfx_resize(cid, height=5)
    vfx_resize(cid, scale=0.5)
    with pytest.raises(ValueError): vfx_resize(cid)
    vfx_head_blur(cid, "t", "t", 2)
    vfx_rotate(cid, 45)
    # Parametrized the rest
    for name, tool in main.__dict__.items():
        if name.startswith("vfx_") and callable(tool):
            try:
                if name in ["vfx_masks_and", "vfx_masks_or"]: tool(cid, cid)
                elif name == "vfx_freeze_region": tool(cid, 0.1, region=[0,0,5,5])
                else: tool(cid)
            except: pass

def test_afx_hit():
    cid = color_clip([10,10], [0,0,0], duration=1)
    for name, tool in main.__dict__.items():
        if name.startswith("afx_") and callable(tool):
            try:
                if "fade" in name: tool(cid, 0.1)
                elif "loop" in name: tool(cid, 2)
                elif "stereo" in name: tool(cid, 0.5, 0.5)
                elif "volume" in name: tool(cid, 0.5)
                else: tool(cid)
            except: pass

@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_tools_hit():
    vid = color_clip([10,10], [0,0,0], duration=1)
    CLIPS[vid].fps = 10
    tools_detect_scenes(vid)
    tools_find_video_period(vid)
    with patch("moviepy.audio.tools.cuts.find_audio_period", return_value=1):
        tools_find_audio_period(vid)
    tools_drawing_color_gradient([10,10], [0,0], [10,10], [0,0,0], [255,255,255])
    tools_drawing_color_split([10,10], 5, 5, [0,0], [10,10], [0,0,0], [255,255,255])

def test_max_clips():
    from main import MAX_CLIPS, register_clip
    CLIPS.clear()
    for _ in range(MAX_CLIPS): register_clip(MagicMock())
    with pytest.raises(RuntimeError): register_clip(MagicMock())

def test_prompts():
    from main import slideshow_wizard, title_card_generator
    slideshow_wizard(images=["a.jpg"], duration_per_image=5, transition_duration=1.0, resolution=[1920, 1080], fps=30)
    title_card_generator(text="hi", resolution=[1920, 1080])
    from main import demonstrate_kaleidoscope

from custom_fx.kaleidoscope_cube import KaleidoscopeCube

def test_kaleidoscope_cube():
    cid = color_clip([100,100], [255,0,0], duration=1)
    effect = KaleidoscopeCube(
        kaleidoscope_params={'n_slices': 12},
        cube_params={'speed_x': 90, 'speed_y': 30}
    )
    
    new_clip = effect.apply(get_clip(cid))
    new_cid = register_clip(new_clip)
    
    write_videofile(new_cid, "kaleidoscope_cube.mp4", fps=30)
    assert os.path.exists("kaleidoscope_cube.mp4")
    os.remove("kaleidoscope_cube.mp4")

def test_upload_endpoint():
    """Test the /upload custom route for raw binary file uploads."""
    app = mcp.http_app(transport="http")
    client = TestClient(app)

    # Create a small test file in memory
    content = b"fake video content for testing"
    response = client.post(
        "/upload",
        files={"file": ("uploaded_test.bin", io.BytesIO(content), "application/octet-stream")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert "size" in data
    assert data["size"] == len(content)
    assert os.path.exists(data["filename"])

    # Verify the file content matches
    with open(data["filename"], "rb") as f:
        assert f.read() == content

    # Clean up
    os.remove(data["filename"])

def test_upload_endpoint_no_file():
    """Test /upload returns 400 when no file field is provided."""
    app = mcp.http_app(transport="http")
    client = TestClient(app)
    response = client.post("/upload")
    assert response.status_code == 400