"""
Typewriter Effect for Text Clips

This module provides a typewriter effect that reveals text one character at a time,
simulating the appearance of text being typed on screen.
"""

from moviepy import Effect, TextClip
import numpy as np


class TypeWriter(Effect):
    """
    A MoviePy effect that reveals text one character at a time, simulating typing.

    This effect progressively shows characters from the source text clip based on time,
    creating the illusion of live typing. Each character, once revealed, stays visible
    for the remainder of the clip's duration.

    Parameters
    ----------
    chars_per_second : float, default=10
        The speed of typing in characters per second.
    delay : float, default=0
        Initial delay in seconds before typing begins.
    """

    def __init__(self, chars_per_second: float = 10, delay: float = 0):
        """
        Initialize the typewriter effect.

        Parameters
        ----------
        chars_per_second : float
            How many characters to reveal per second (default: 10)
        delay : float
            Initial delay in seconds before typing starts (default: 0)
        """
        self.chars_per_second = chars_per_second
        self.delay = delay

    def apply(self, clip):
        """
        Apply the typewriter effect to a text clip.

        Parameters
        ----------
        clip : VideoClip
            The text clip to apply the effect to. Must have a 'text' attribute.

        Returns
        -------
        VideoClip
            A new clip with the typewriter effect applied
        """
        if not hasattr(clip, 'text') or not clip.text:
            # If it's not a text clip, return unchanged
            return clip

        original_text = clip.text
        char_duration = 1.0 / self.chars_per_second
        total_chars = len(original_text)

        # Total duration the typewriter animation itself takes
        typing_duration = self.delay + total_chars * char_duration
        # If the original clip is longer, honour that; otherwise use typing duration
        total_duration = max(
            typing_duration,
            clip.duration if (hasattr(clip, 'duration') and clip.duration is not None) else 0
        )

        # Collect attributes from original clip
        font = getattr(clip, 'font', None)
        font_size = getattr(clip, 'font_size', None)
        color = getattr(clip, 'color', 'black')
        bg_color = getattr(clip, 'bg_color', None)
        size = getattr(clip, 'size', (None, None))
        method = getattr(clip, 'method', 'label')

        from moviepy import CompositeVideoClip

        clips = []

        # For each character, create a text clip that shows from its reveal time
        # until the END of the total duration. This ensures characters accumulate
        # (i.e., once a character appears it stays visible).
        for i in range(1, total_chars + 1):
            partial_text = original_text[:i]
            start_time = self.delay + (i - 1) * char_duration
            # Each clip runs from 'start_time' to end of total clip
            clip_duration = total_duration - start_time

            if clip_duration <= 0:
                continue

            txt_clip = TextClip(
                font=font,
                text=partial_text,
                font_size=font_size,
                color=color,
                bg_color=bg_color,
                size=size,
                method=method,
                duration=clip_duration,
            )

            txt_clip = txt_clip.with_start(start_time)

            # Copy position from original clip
            if hasattr(clip, 'pos'):
                txt_clip = txt_clip.with_position(clip.pos)

            clips.append(txt_clip)

        if not clips:
            return clip

        # Composite all the progressive text clips.
        # use_bgclip=False so earlier (shorter accumulated) clips aren't treated as bg.
        # The last clip (full text) is on top and runs longest; earlier clips are hidden
        # behind it once the next one starts, but since they're composited by layering order
        # and each new clip has more text, we stack in reverse so the longest (most recent)
        # partial text is always on top.
        result = CompositeVideoClip(
            clips,
            size=(clip.w, clip.h) if (hasattr(clip, 'w') and clip.w and hasattr(clip, 'h') and clip.h) else None,
        )

        result = result.with_duration(total_duration)

        return result
