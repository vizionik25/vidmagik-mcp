"""
Typewriter Effect for Text Clips

This module provides a typewriter effect that reveals text one character at a time,
simulating the appearance of text being typed on screen.
"""

from moviepy import VideoClip, TextClip, CompositeVideoClip
from moviepy.decorators import requires_duration
import numpy as np


class TypeWriter:
    """
    A typewriter effect that progressively reveals text one character at a time.
    
    This effect works by creating text clips for each progressive state of the text
    and compositing them with precise timing to simulate typing.
    
    Parameters
    ----------
    chars_per_second : float, default=10
        The speed of typing in characters per second.
    delay : float, default=0
        Initial delay before typing begins, in seconds.
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
    
    def apply(self, clip: VideoClip) -> VideoClip:
        """
        Apply the typewriter effect to a text clip.
        
        Parameters
        ----------
        clip : VideoClip
            The text clip to apply the effect to
            
        Returns
        -------
        VideoClip
            A new clip with the typewriter effect applied
        """
        if not hasattr(clip, 'text') or not clip.text:
            # If it's not a text clip, return unchanged
            return clip
        
        text = clip.text
        char_duration = 1.0 / self.chars_per_second
        total_chars = len(text)
        
        # Calculate total duration needed for typing
        typing_duration = total_chars * char_duration
        clip_duration = clip.duration if hasattr(clip, 'duration') else typing_duration + self.delay
        
        # Create clips for each character progression
        clips = []
        
        if self.delay > 0:
            # Create a blank/empty clip for the delay period
            from moviepy import ColorClip
            blank = ColorClip(
                size=(clip.w, clip.h) if hasattr(clip, 'w') else (1920, 1080),
                color=(0, 0, 0)
            ).with_duration(self.delay)
            clips.append(blank)
        
        # Generate progressively longer text clips
        for i in range(1, total_chars + 1):
            partial_text = text[:i]
            
            # Create a text clip with the partial text
            # Use the same properties as the original clip
            text_props = {}
            if hasattr(clip, 'font'):
                text_props['font'] = clip.font
            if hasattr(clip, 'font_size'):
                text_props['font_size'] = clip.font_size
            if hasattr(clip, 'color'):
                text_props['color'] = clip.color
            if hasattr(clip, 'method'):
                text_props['method'] = clip.method
            if hasattr(clip, 'bg_color'):
                text_props['bg_color'] = clip.bg_color
            if hasattr(clip, 'size'):
                text_props['size'] = clip.size
            
            txt_clip = TextClip(
                text=partial_text,
                **text_props
            ).with_duration(char_duration)
            
            clips.append(txt_clip)
        
        # Concatenate all clips to create the typewriter effect
        result = CompositeVideoClip(
            clips,
            size=(clip.w, clip.h) if hasattr(clip, 'w') else None
        ).with_duration(clip_duration)
        
        # Copy position and other properties from original clip
        if hasattr(clip, 'pos'):
            result = result.with_position(clip.pos)
        
        return result
