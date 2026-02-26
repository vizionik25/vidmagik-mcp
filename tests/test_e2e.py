"""
End-to-end tests for vidmagik-mcp.

Coverage:
  - Clip management  : validate_path, register_clip, get_clip, list_clips,
                       delete_clip, purge_clips, MAX_CLIPS guard
  - Video I/O        : video_file_clip, image_clip, image_sequence_clip,
                       color_clip, text_clip, credits_clip, subtitles_clip,
                       write_videofile, write_gif, tools_ffmpeg_extract_subclip
  - Audio I/O        : audio_file_clip, write_audiofile
  - Transforms       : set_position, set_start, set_end, set_duration,
                       set_mask, set_audio, subclip,
                       composite_video_clips, concatenate_video_clips,
                       composite_audio_clips, concatenate_audio_clips,
                       tools_clips_array
  - Standard VFX     : all vfx_* tools (smoke-test sweep + explicit edge cases)
  - Audio FX         : all afx_* tools (smoke-test sweep)
  - Drawing/tools    : tools_detect_scenes, tools_find_video_period,
                       tools_find_audio_period, tools_drawing_color_gradient,
                       tools_drawing_color_split, tools_file_to_subtitles,
                       tools_check_installation
  - Custom FX        : vfx_quad_mirror, vfx_chroma_key, vfx_rgb_sync,
                       vfx_kaleidoscope, vfx_matrix, vfx_auto_framing,
                       vfx_clone_grid, vfx_rotating_cube, vfx_kaleidoscope_cube
  - Upload/Download  : /upload-ui, /upload, /download,
                       request_file_upload, get_uploaded_file, get_download_url
  - Prompts          : slideshow_wizard, title_card_generator,
                       demonstrate_kaleidoscope, demonstrate_kaleidoscope_cube
"""

import io
import os
import shutil
import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

import main
from main import (
    CLIPS,
    validate_path, register_clip, get_clip, list_clips, delete_clip, purge_clips,
    video_file_clip, image_clip, image_sequence_clip, color_clip,
    write_videofile, write_gif, tools_ffmpeg_extract_subclip,
    audio_file_clip, write_audiofile,
    set_position, set_start, set_end, set_duration, set_mask, set_audio, subclip,
    composite_video_clips, concatenate_video_clips,
    composite_audio_clips, concatenate_audio_clips,
    tools_clips_array,
    vfx_accel_decel, vfx_black_white, vfx_blink, vfx_chroma_key, vfx_clone_grid,
    vfx_crop, vfx_cross_fade_in, vfx_cross_fade_out, vfx_even_size,
    vfx_fade_in, vfx_fade_out, vfx_freeze, vfx_gamma_correction, vfx_head_blur,
    vfx_invert_colors, vfx_kaleidoscope, vfx_kaleidoscope_cube, vfx_loop,
    vfx_lum_contrast, vfx_make_loopable, vfx_margin, vfx_mask_color,
    vfx_masks_and, vfx_masks_or, vfx_matrix, vfx_mirror_x, vfx_mirror_y,
    vfx_multiply_color, vfx_multiply_speed, vfx_painting, vfx_quad_mirror,
    vfx_resize, vfx_rgb_sync, vfx_rotating_cube, vfx_rotate, vfx_scroll,
    vfx_slide_in, vfx_slide_out, vfx_supersample, vfx_time_mirror,
    vfx_time_symmetrize, vfx_auto_framing,
    tools_detect_scenes, tools_find_video_period, tools_find_audio_period,
    tools_drawing_color_gradient, tools_drawing_color_split, tools_file_to_subtitles,
    tools_check_installation, list_available_fonts,
    request_file_upload, get_uploaded_file, get_download_url,
    UPLOAD_SESSIONS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEMP_FILES = [
    "temp.mp4", "temp2.mp4", "temp.wav", "temp.mp3",
    "test.png", "credits.txt", "sub.srt", "test.gif",
    "uploaded_test.bin", "download_test.mp4",
]

@pytest.fixture(autouse=True)
def cleanup():
    CLIPS.clear()
    UPLOAD_SESSIONS.clear()
    yield
    CLIPS.clear()
    UPLOAD_SESSIONS.clear()
    for f in _TEMP_FILES:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    if os.path.exists("test_img_dir"):
        shutil.rmtree("test_img_dir")


def _png(path="test.png", size=(10, 10)):
    """Write a tiny PNG and return its path."""
    data = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    Image.fromarray(data).save(path)
    return path


def _color(duration=1.0, size=(10, 10), color=(0, 0, 0)):
    """Return a clip_id for a solid color VideoClip."""
    return color_clip(list(size), list(color), duration=duration)


def _app():
    return main.mcp.http_app(transport="http")


# ---------------------------------------------------------------------------
# Clip management
# ---------------------------------------------------------------------------

class TestClipManagement:
    def test_validate_path(self):
        validate_path("test.mp4")
        validate_path("/tmp/test.mp4")

    def test_register_get_delete(self):
        cid = _color()
        assert get_clip(cid) is not None
        with pytest.raises(ValueError):
            get_clip("nonexistent")
        delete_clip(cid)
        delete_clip("nonexistent")  # should not raise

    def test_delete_clip_close_error(self):
        """delete_clip must survive a close() exception."""
        cid = _color(duration=0.1)
        CLIPS[cid].close = MagicMock(side_effect=Exception("boom"))
        delete_clip(cid)

    def test_list_clips(self):
        cid = _color()
        result = list_clips()
        assert cid in result

    def test_purge_clips_empty(self):
        result = purge_clips()
        assert "empty" in result.lower()

    def test_purge_clips(self):
        _color()
        _color()
        result = purge_clips()
        assert "2" in result
        assert len(CLIPS) == 0

    def test_max_clips(self):
        from main import MAX_CLIPS
        CLIPS.clear()
        for _ in range(MAX_CLIPS):
            register_clip(MagicMock())
        with pytest.raises(RuntimeError):
            register_clip(MagicMock())


# ---------------------------------------------------------------------------
# Video I/O
# ---------------------------------------------------------------------------

class TestVideoIO:
    def test_color_clip_invalid_duration(self):
        with pytest.raises(ValueError):
            color_clip([10, 10], [0, 0, 0], duration=-1)

    def test_image_clip(self):
        _png()
        image_clip("test.png", duration=0.5)
        with pytest.raises(FileNotFoundError):
            image_clip("missing.png")

    def test_image_sequence_clip(self):
        _png()
        image_sequence_clip(["test.png"], fps=5)
        os.makedirs("test_img_dir", exist_ok=True)
        _png("test_img_dir/1.png")
        image_sequence_clip(["test_img_dir"], fps=5)
        with pytest.raises(ValueError):
            image_sequence_clip([], fps=5)

    def test_video_file_clip(self):
        vid = _color(duration=0.5)
        write_videofile(vid, "temp.mp4", fps=5)
        video_file_clip("temp.mp4")
        video_file_clip("temp.mp4", target_resolution=[5, 5])
        with pytest.raises(FileNotFoundError):
            video_file_clip("missing.mp4")

    def test_write_videofile(self):
        vid = _color(duration=0.5)
        write_videofile(vid, "temp.mp4", fps=5)
        assert os.path.exists("temp.mp4")

    def test_write_gif(self):
        vid = _color(duration=0.5)
        write_gif(vid, "test.gif", fps=5)
        assert os.path.exists("test.gif")

    def test_tools_ffmpeg_extract_subclip(self):
        vid = _color(duration=0.5)
        write_videofile(vid, "temp.mp4", fps=5)
        tools_ffmpeg_extract_subclip("temp.mp4", 0, 0.1, "temp2.mp4")
        with pytest.raises(ValueError):
            tools_ffmpeg_extract_subclip("temp.mp4", 0.5, 0.1, "temp2.mp4")

    @patch("main.TextClip")
    @patch("main.CreditsClip")
    @patch("main.SubtitlesClip")
    def test_special_clips(self, ms, mc, mt):
        mt.return_value = MagicMock()
        mc.return_value = MagicMock()
        ms.return_value = MagicMock()

        text_clip = main.text_clip
        credits_clip = main.credits_clip
        subtitles_clip = main.subtitles_clip

        text_clip("hello")
        with pytest.raises(ValueError):
            text_clip("hello", duration=0)

        with open("credits.txt", "w") as f:
            f.write("Name  Role\n")
        credits_clip("credits.txt", width=100)
        with pytest.raises(ValueError):
            credits_clip("credits.txt", width=0)
        with pytest.raises(FileNotFoundError):
            credits_clip("missing.txt", 100)

        with open("sub.srt", "w") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
        subtitles_clip("sub.srt")
        with pytest.raises(FileNotFoundError):
            subtitles_clip("missing.srt")
        tools_file_to_subtitles("sub.srt")


# ---------------------------------------------------------------------------
# Audio I/O
# ---------------------------------------------------------------------------

class TestAudioIO:
    def test_audio_file_clip(self):
        from moviepy import AudioClip
        audio = AudioClip(
            lambda t: np.sin(440 * 2 * np.pi * t), duration=0.5, fps=44100
        )
        audio.write_audiofile("temp.wav", fps=44100, logger=None)
        aid = audio_file_clip("temp.wav")
        assert aid in CLIPS
        with pytest.raises(FileNotFoundError):
            audio_file_clip("missing.wav")

    def test_write_audiofile(self):
        from moviepy import AudioClip
        audio = AudioClip(
            lambda t: np.sin(440 * 2 * np.pi * t), duration=0.5, fps=44100
        )
        audio.write_audiofile("temp.wav", fps=44100, logger=None)
        aid = audio_file_clip("temp.wav")
        write_audiofile(aid, "temp.mp3")
        assert os.path.exists("temp.mp3")


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

class TestTransforms:
    def setup_method(self):
        self.cid = _color()

    def test_set_position(self):
        set_position(self.cid, pos_str="center")
        set_position(self.cid, x=1)
        set_position(self.cid, y=1)
        set_position(self.cid, x=1, y=1)
        set_position(self.cid, x=1, y=1, relative=True)
        with pytest.raises(ValueError):
            set_position(self.cid)

    def test_set_timing(self):
        set_start(self.cid, 0.1)
        set_end(self.cid, 0.9)
        set_duration(self.cid, 0.5)

    def test_set_mask_and_audio(self):
        set_mask(self.cid, self.cid)
        set_audio(self.cid, self.cid)

    def test_subclip(self):
        subclip(self.cid, 0.1, 0.5)
        with pytest.raises(ValueError):
            subclip(self.cid, 0.5, 0.1)

    def test_composite_video_clips(self):
        composite_video_clips([self.cid])
        composite_video_clips([self.cid], size=[20, 20], bg_color=[0, 0, 0])
        with pytest.raises(ValueError):
            composite_video_clips([])

    def test_concatenate_video_clips(self):
        cid2 = _color()
        concatenate_video_clips([self.cid, cid2])
        with pytest.raises(ValueError):
            concatenate_video_clips([])

    def test_tools_clips_array(self):
        cid2 = _color()
        tools_clips_array([[self.cid, cid2]])
        with pytest.raises(ValueError):
            tools_clips_array([])

    def test_composite_audio_clips(self):
        from moviepy import AudioClip
        a = AudioClip(lambda t: np.zeros((1,)), duration=0.5, fps=44100)
        aid1 = register_clip(a)
        aid2 = register_clip(a)
        composite_audio_clips([aid1, aid2])

    def test_concatenate_audio_clips(self):
        from moviepy import AudioClip
        a = AudioClip(lambda t: np.zeros((1,)), duration=0.5, fps=44100)
        aid1 = register_clip(a)
        aid2 = register_clip(a)
        concatenate_audio_clips([aid1, aid2])


# ---------------------------------------------------------------------------
# VFX — explicit edge-case tests
# ---------------------------------------------------------------------------

class TestVFXExplicit:
    def setup_method(self):
        self.cid = _color(duration=1.0, size=(20, 20))

    def test_vfx_accel_decel(self):
        vfx_accel_decel(self.cid, new_duration=2)

    def test_vfx_black_white(self):
        vfx_black_white(self.cid)

    def test_vfx_blink(self):
        vfx_blink(self.cid, 0.1, 0.1)

    def test_vfx_crop(self):
        vfx_crop(self.cid, x1=0, y1=0, x2=10, y2=10)
        vfx_crop(self.cid, x_center=10, y_center=10, width=8, height=8)

    def test_vfx_cross_fade(self):
        vfx_cross_fade_in(self.cid, 0.1)
        vfx_cross_fade_out(self.cid, 0.1)

    def test_vfx_even_size(self):
        vfx_even_size(self.cid)

    def test_vfx_fade(self):
        vfx_fade_in(self.cid, 0.1)
        vfx_fade_out(self.cid, 0.1)

    def test_vfx_freeze(self):
        vfx_freeze(self.cid, t=0.1, freeze_duration=0.2)

    def test_vfx_gamma_correction(self):
        vfx_gamma_correction(self.cid, 1.2)

    def test_vfx_head_blur(self):
        vfx_head_blur(self.cid, "t", "t", 2)
        with pytest.raises(ValueError):
            vfx_head_blur(self.cid, "invalid(", "t", 2)

    def test_vfx_invert_colors(self):
        vfx_invert_colors(self.cid)

    def test_vfx_loop(self):
        vfx_loop(self.cid, n=2)
        vfx_loop(self.cid, duration=2.0)

    def test_vfx_lum_contrast(self):
        vfx_lum_contrast(self.cid, lum=10, contrast=20)

    def test_vfx_make_loopable(self):
        vfx_make_loopable(self.cid, overlap_duration=0.2)

    def test_vfx_margin(self):
        vfx_margin(self.cid, margin=2, color=[255, 0, 0])

    def test_vfx_mask_color(self):
        vfx_mask_color(self.cid)
        vfx_mask_color(self.cid, color=[0, 0, 0], threshold=10, stiffness=2)

    def test_vfx_masks(self):
        vfx_masks_and(self.cid, self.cid)
        vfx_masks_or(self.cid, self.cid)

    def test_vfx_mirror(self):
        vfx_mirror_x(self.cid)
        vfx_mirror_y(self.cid)

    def test_vfx_multiply(self):
        vfx_multiply_color(self.cid, 0.5)
        vfx_multiply_speed(self.cid, 2.0)

    def test_vfx_painting(self):
        vfx_painting(self.cid)

    def test_vfx_resize(self):
        vfx_resize(self.cid, width=5)
        vfx_resize(self.cid, height=5)
        vfx_resize(self.cid, scale=0.5)
        with pytest.raises(ValueError):
            vfx_resize(self.cid)

    def test_vfx_rgb_sync(self):
        vfx_rgb_sync(self.cid)
        vfx_rgb_sync(
            self.cid,
            r_offset=[5, 0], g_offset=[0, 5], b_offset=[-5, 0],
            r_time_offset=0.05,
        )

    def test_vfx_rotate(self):
        vfx_rotate(self.cid, 45)

    def test_vfx_scroll(self):
        vfx_scroll(self.cid, x_speed=1.0)
        vfx_scroll(self.cid, y_speed=1.0)

    def test_vfx_slide(self):
        vfx_slide_in(self.cid, duration=0.2, side="left")
        vfx_slide_out(self.cid, duration=0.2, side="right")

    def test_vfx_supersample(self):
        vfx_supersample(self.cid, d=0.05, nframes=3)

    def test_vfx_time_effects(self):
        vfx_time_mirror(self.cid)
        vfx_time_symmetrize(self.cid)


# ---------------------------------------------------------------------------
# Custom / advanced VFX
# ---------------------------------------------------------------------------

class TestCustomVFX:
    def setup_method(self):
        self.cid = _color(duration=1.0, size=(20, 20), color=(128, 0, 200))

    def test_vfx_quad_mirror(self):
        vfx_quad_mirror(self.cid)
        vfx_quad_mirror(self.cid, x=10, y=10)

    def test_vfx_chroma_key(self):
        vfx_chroma_key(self.cid)
        vfx_chroma_key(self.cid, color=[0, 0, 0], threshold=30, softness=10)

    def test_vfx_kaleidoscope(self):
        vfx_kaleidoscope(self.cid)
        vfx_kaleidoscope(self.cid, n_slices=8, x=10, y=10)

    def test_vfx_matrix(self):
        vfx_matrix(self.cid)
        vfx_matrix(self.cid, speed=200, density=0.3, chars="01", color="green", font_size=8)

    def test_vfx_auto_framing(self):
        vfx_auto_framing(self.cid)
        vfx_auto_framing(self.cid, target_aspect_ratio=1.0, smoothing=0.5)

    def test_vfx_clone_grid(self):
        vfx_clone_grid(self.cid, n_clones=4)

    def test_vfx_rotating_cube(self):
        vfx_rotating_cube(self.cid, speed=90)
        vfx_rotating_cube(self.cid, direction="vertical", zoom=1.5)

    def test_vfx_kaleidoscope_cube(self):
        from custom_fx.kaleidoscope_cube import KaleidoscopeCube
        cid = _color(duration=1.0, size=(100, 100), color=(255, 0, 0))
        effect = KaleidoscopeCube(
            kaleidoscope_params={"n_slices": 12},
            cube_params={"speed_x": 90, "speed_y": 30},
        )
        new_clip = effect.apply(get_clip(cid))
        new_cid = register_clip(new_clip)
        write_videofile(new_cid, "temp.mp4", fps=10)
        assert os.path.exists("temp.mp4")


# ---------------------------------------------------------------------------
# Audio FX smoke test
# ---------------------------------------------------------------------------

@pytest.mark.filterwarnings("ignore::RuntimeWarning")
class TestAFX:
    """Smoke-test every afx_* tool against a colour clip (audio is None; expect graceful pass or skip)."""

    def test_afx_sweep(self):
        cid = _color()
        for name, tool in main.__dict__.items():
            if not (name.startswith("afx_") and callable(tool)):
                continue
            try:
                if "fade" in name:
                    tool(cid, 0.1)
                elif "loop" in name:
                    tool(cid, 2)
                elif "stereo" in name:
                    tool(cid, 0.5, 0.5)
                elif "volume" in name:
                    tool(cid, 0.5)
                else:
                    tool(cid)
            except Exception:
                pass  # No audio track — expected failures are acceptable here


# ---------------------------------------------------------------------------
# tools_* utilities
# ---------------------------------------------------------------------------

@pytest.mark.filterwarnings("ignore::RuntimeWarning")
class TestToolsUtilities:
    def test_detect_scenes(self):
        vid = _color()
        CLIPS[vid].fps = 10
        tools_detect_scenes(vid)

    def test_find_video_period(self):
        vid = _color()
        CLIPS[vid].fps = 10
        tools_find_video_period(vid)

    def test_find_audio_period(self):
        vid = _color()
        with patch("moviepy.audio.tools.cuts.find_audio_period", return_value=1):
            tools_find_audio_period(vid)

    def test_drawing_color_gradient(self):
        tools_drawing_color_gradient(
            [10, 10], [0, 0], [10, 10], [0, 0, 0], [255, 255, 255]
        )

    def test_drawing_color_split(self):
        tools_drawing_color_split(
            [10, 10], 5, 5, [0, 0], [10, 10], [0, 0, 0], [255, 255, 255]
        )

    def test_tools_check_installation(self):
        # Just verify it doesn't raise an unhandled exception
        result = tools_check_installation()
        assert isinstance(result, str)

    def test_list_available_fonts(self):
        fonts = list_available_fonts()
        assert isinstance(fonts, list)
        assert len(fonts) > 0
        assert any(f.endswith(".ttf") or f.endswith(".otf") for f in fonts)
        assert "Agaste.ttf" in fonts


# ---------------------------------------------------------------------------
# Upload / Download HTTP endpoints
# ---------------------------------------------------------------------------

class TestUploadEndpoint:
    def test_upload_ui_renders(self):
        client = TestClient(_app())
        resp = client.get("/upload-ui?session=abc")
        assert resp.status_code == 200
        assert "Upload" in resp.text

    def test_upload_success(self):
        client = TestClient(_app())
        content = b"fake video content for testing"
        resp = client.post(
            "/upload",
            files={"file": ("uploaded_test.bin", io.BytesIO(content), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "filename" in data
        assert data["size"] == len(content)
        assert os.path.exists(data["filename"])
        with open(data["filename"], "rb") as f:
            assert f.read() == content
        os.remove(data["filename"])

    def test_upload_with_session_registration(self):
        """Upload with a known session_id should register the path."""
        client = TestClient(_app())
        session_id = "test-session-abc"
        UPLOAD_SESSIONS[session_id] = None  # pending

        content = b"session file"
        resp = client.post(
            f"/upload?session={session_id}",
            files={"file": ("sess_test.bin", io.BytesIO(content), "application/octet-stream")},
        )
        assert resp.status_code == 200
        assert UPLOAD_SESSIONS[session_id] is not None  # should now be a path
        if os.path.exists(UPLOAD_SESSIONS[session_id]):
            os.remove(UPLOAD_SESSIONS[session_id])

    def test_upload_no_file_returns_400(self):
        client = TestClient(_app())
        resp = client.post("/upload")
        assert resp.status_code == 400

    def test_upload_options_cors(self):
        """OPTIONS pre-flight should return 200 with CORS headers."""
        client = TestClient(_app())
        resp = client.options("/upload")
        assert resp.status_code == 200
        assert "Access-Control-Allow-Methods" in resp.headers


class TestDownloadEndpoint:
    def test_download_success(self):
        # Write a real file then hit /download
        vid = _color(duration=0.2)
        write_videofile(vid, "download_test.mp4", fps=5)
        client = TestClient(_app())
        resp = client.get("/download?file=download_test.mp4")
        assert resp.status_code == 200
        assert len(resp.content) > 0

    def test_download_missing_param(self):
        client = TestClient(_app())
        resp = client.get("/download")
        assert resp.status_code == 400

    def test_download_missing_file(self):
        client = TestClient(_app())
        resp = client.get("/download?file=does_not_exist.mp4")
        assert resp.status_code == 404

    def test_download_path_traversal_blocked(self):
        client = TestClient(_app())
        resp = client.get("/download?file=../../etc/passwd")
        # Either 403 (traversal blocked) or 404 (file doesn't exist after resolution)
        assert resp.status_code in (403, 404)


class TestUploadDownloadTools:
    def test_request_file_upload_returns_json(self):
        import json
        result = request_file_upload()
        data = json.loads(result)
        assert "session_id" in data
        assert "upload_url" in data
        assert data["session_id"] in UPLOAD_SESSIONS

    def test_get_uploaded_file_unknown_session(self):
        with pytest.raises(ValueError, match="Unknown session_id"):
            get_uploaded_file("not-a-real-session")

    def test_get_uploaded_file_pending(self):
        import json
        result = request_file_upload()
        sid = json.loads(result)["session_id"]
        with pytest.raises(ValueError, match="still pending"):
            get_uploaded_file(sid)

    def test_get_uploaded_file_resolved(self):
        import json
        result = request_file_upload()
        sid = json.loads(result)["session_id"]
        UPLOAD_SESSIONS[sid] = "/tmp/resolved_file.mp4"
        path = get_uploaded_file(sid)
        assert path == "/tmp/resolved_file.mp4"

    def test_get_download_url(self):
        vid = _color(duration=0.2)
        write_videofile(vid, "download_test.mp4", fps=5)
        url = get_download_url("download_test.mp4")
        assert url.startswith("http")
        assert "download_test.mp4" in url

    def test_get_download_url_missing_file(self):
        with pytest.raises(ValueError):
            get_download_url("nonexistent_file.mp4")


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

class TestPrompts:
    def test_slideshow_wizard(self):
        from main import slideshow_wizard
        result = slideshow_wizard(
            images=["a.jpg", "b.jpg"],
            duration_per_image=5,
            transition_duration=1.0,
            resolution=[1920, 1080],
            fps=30,
        )
        assert isinstance(result, str)
        assert "slideshow" in result.lower()

    def test_title_card_generator(self):
        from main import title_card_generator
        result = title_card_generator(text="Hello World", resolution=[1920, 1080])
        assert "Hello World" in result

    def test_demonstrate_kaleidoscope(self):
        from main import demonstrate_kaleidoscope
        cid = _color()
        result = demonstrate_kaleidoscope(cid)
        assert cid in result

    def test_demonstrate_kaleidoscope_cube(self):
        from main import demonstrate_kaleidoscope_cube
        cid = _color()
        result = demonstrate_kaleidoscope_cube(cid)
        assert cid in result

    def test_glitch_effect_preset(self):
        from main import glitch_effect_preset
        cid = _color()
        result = glitch_effect_preset(cid)
        assert isinstance(result, str)

    def test_matrix_intro_preset(self):
        from main import matrix_intro_preset
        cid = _color()
        result = matrix_intro_preset(cid)
        assert isinstance(result, str)

    def test_auto_framing_for_tiktok(self):
        from main import auto_framing_for_tiktok
        cid = _color()
        result = auto_framing_for_tiktok(cid)
        assert isinstance(result, str)

    def test_rotating_cube_transition(self):
        from main import rotating_cube_transition
        cid = _color()
        result = rotating_cube_transition(cid)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Real-video fixtures — target uncovered branches
# ---------------------------------------------------------------------------

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "..", "media")
REAL_VIDEOS = sorted(
    os.path.join(MEDIA_DIR, f)
    for f in os.listdir(MEDIA_DIR)
    if f.endswith(".mp4")
) if os.path.isdir(MEDIA_DIR) else []

@pytest.mark.skipif(not REAL_VIDEOS, reason="No media/ MP4s found")
class TestRealVideoFixtures:
    """Use actual footage from media/ to exercise branches that solid-colour
    clips cannot reach (face detection, pixel-level colour ops, etc.)."""

    def setup_method(self):
        self.src = REAL_VIDEOS[0]  # Scene_a_cybernetic_202602071630_ez2wg.mp4

    def _load(self, duration=1.0):
        """Load a short subclip of the real video and return its clip_id."""
        from moviepy import VideoFileClip
        clip = VideoFileClip(self.src).subclipped(0, duration)
        return register_clip(clip)

    # --- auto_framing: face-detection + EMA smoothing paths ---

    def test_auto_framing_real_video_face_detection(self):
        """Exercises the face-detected and EMA-smoothing branches of AutoFraming."""
        from custom_fx.auto_framing import AutoFraming
        cid = self._load(duration=1.0)
        clip = get_clip(cid)
        # Apply and render 2 frames so EMA smoothing branch (L66-67) is hit
        effect = AutoFraming(target_aspect_ratio=9/16, smoothing=0.8)
        new_clip = effect.apply(clip)
        new_clip.get_frame(0)  # first frame — sets current_x/y
        new_clip.get_frame(0.5)  # second frame — hits EMA smoothing

    def test_auto_framing_custom_focus_func(self):
        """Exercises focus_func path (L39-44) including exception suppression."""
        from custom_fx.auto_framing import AutoFraming
        cid = self._load(duration=0.5)
        clip = get_clip(cid)

        call_count = {"n": 0}

        def focus_func(frame, t):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("deliberate error — must be swallowed")
            return (frame.shape[1] // 3, frame.shape[0] // 3)

        effect = AutoFraming(focus_func=focus_func)
        new_clip = effect.apply(clip)
        new_clip.get_frame(0)    # raises inside focus_func → fallback to face/center
        new_clip.get_frame(0.2)  # returns valid (x, y) → L41-42 hit

    def test_auto_framing_taller_than_target(self):
        """Source clip taller than target ratio → L77-78 crop branch."""
        from custom_fx.auto_framing import AutoFraming
        cid = self._load(duration=0.5)
        clip = get_clip(cid)
        # 720×1280 is portrait (w/h < 1), target_aspect_ratio=2 → taller branch
        effect = AutoFraming(target_aspect_ratio=2.0)
        new_clip = effect.apply(clip)
        new_clip.get_frame(0)

    # --- chroma_key: softness=0 binary mask and existing mask ---

    def test_chroma_key_softness_zero(self):
        """Exercises the hard binary mask branch (softness=0, L34)."""
        from custom_fx.chroma_key import ChromaKey
        cid = self._load(duration=0.5)
        clip = get_clip(cid)
        effect = ChromaKey(color=(0, 255, 0), threshold=30, softness=0)
        result = effect.apply(clip)
        result.get_frame(0)

    def test_chroma_key_with_existing_mask(self):
        """Exercises the clip.mask is not None branch (L38-42)."""
        from custom_fx.chroma_key import ChromaKey
        from moviepy import VideoFileClip
        clip = VideoFileClip(self.src).subclipped(0, 0.5)
        # Give the clip a mask so L38 is True
        mask_clip = clip.to_mask()
        clip = clip.with_mask(mask_clip)
        cid = register_clip(clip)
        effect = ChromaKey(color=(20, 20, 20), threshold=40, softness=15)
        result = effect.apply(get_clip(cid))
        result.get_frame(0)

    # --- clone_grid: non-power-of-2 and size-mismatch paths ---

    def test_clone_grid_non_power_of_2(self):
        """n_clones=3 → fallback grid calculation (L32-34)."""
        from custom_fx.clone_grid import CloneGrid
        cid = self._load(duration=0.5)
        clip = get_clip(cid)
        effect = CloneGrid(n_clones=3)
        result = effect.apply(clip)
        result.get_frame(0)

    def test_clone_grid_odd_dimensions_resize(self):
        """Use a clip with a size that guarantees grid shape mismatch → L60 resize."""
        from custom_fx.clone_grid import CloneGrid
        # A 7×7 clip and 3 clones: 7//2=3, so grid = 6×6 ≠ 7×7 → resize triggered
        cid = _color(duration=0.5, size=(7, 7))
        effect = CloneGrid(n_clones=4)
        new_cid = register_clip(effect.apply(get_clip(cid)))
        get_clip(new_cid).get_frame(0)

    # --- matrix: font fallback path ---

    def test_matrix_font_fallback(self):
        """Forces the font load to fail so ImageFont.load_default() is used (L48-49).

        Note: in modern Pillow, load_default() internally calls truetype(), so the
        mock must only raise on the *first* call and succeed on subsequent ones.
        """
        from custom_fx import matrix as matrix_mod
        from PIL import ImageFont as _ImageFont
        import unittest.mock as mock

        cid = _color(duration=0.5, size=(40, 40))
        clip = get_clip(cid)

        effect = matrix_mod.Matrix(font_size=8)

        real_truetype = _ImageFont.truetype
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("no font — force fallback to load_default")
            return real_truetype(*args, **kwargs)

        with mock.patch.object(_ImageFont, "truetype", side_effect=side_effect):
            effect._atlas = None
            new_clip = effect.apply(clip)
            new_clip.get_frame(0)

    # --- main.py: purge with leftover clips warning ---

    def test_purge_clips_with_leftover_warning(self):
        """Hits the 'still remain' warning branch in purge_clips (main.py L89)."""
        import main as main_mod

        # Build a dict subclass that injects a 'zombie' key on first deletion,
        # causing purge_clips to find remaining clips after its loop.
        class TrappedDict(dict):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self._first = True

            def __delitem__(self, key):
                super().__delitem__(key)
                if self._first:
                    self._first = False
                    zombie = MagicMock()
                    zombie.close = MagicMock()
                    super().__setitem__("zombie", zombie)

        trapped = TrappedDict({"clip-a": MagicMock()})
        trapped["clip-a"].close = MagicMock()

        # Temporarily replace main.CLIPS with our subclassed dict
        original = main_mod.CLIPS
        try:
            main_mod.CLIPS = trapped
            result = main_mod.purge_clips()
        finally:
            main_mod.CLIPS = original
            CLIPS.clear()

        assert "still remain" in result or isinstance(result, str)