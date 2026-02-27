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
    creating the illusion of live typing.
    
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
        
        def make_frame(get_frame, t):
            """Generate frame with progressively revealed text."""
            # Calculate how many characters should be visible at time t
            if t < self.delay:
                # Before delay, show nothing (empty text)
                num_chars = 0
            else:
                # After delay, calculate progress
                time_since_start = t - self.delay
                num_chars = int(time_since_start / char_duration) + 1
                num_chars = min(num_chars, total_chars)
            
            # Temporarily modify the clip's text
            original_get_frame = get_frame
            
            if num_chars == 0:
                # Show empty/blank frame
                frame = get_frame(t)
                # Clear the frame (make it transparent or black)
                frame[:] = 0
                return frame
            else:
                # Get the frame with the original render
                frame = get_frame(t)
                return frame
        
        # Create a new text clip with progressive text reveal
        def filter_func(get_frame, t):
            """Filter to progressively show text based on time."""
            if t < self.delay:
                num_chars = 0
            else:
                time_since_start = t - self.delay
                num_chars = int(time_since_start / char_duration) + 1
                num_chars = min(num_chars, total_chars)
            
            if num_chars == 0:
                # Create empty frame
                frame = get_frame(t)
                frame[:] = 0
                return frame
            else:
                # Show partial text
                return get_frame(t)
        
        # Build progressive text clips and composite them
        from moviepy import CompositeVideoClip
        
        clips = []
        
        # Collect attributes from original clip
        font = getattr(clip, 'font', None)
        font_size = getattr(clip, 'font_size', None)
        color = getattr(clip, 'color', 'black')
        bg_color = getattr(clip, 'bg_color', None)
        size = getattr(clip, 'size', (None, None))
        method = getattr(clip, 'method', 'label')

        # For each character progression, create a text clip
        for i in range(1, total_chars + 1):
            partial_text = original_text[:i]
            start_time = self.delay + (i - 1) * char_duration
            
            # Create a text clip with explicit keyword arguments to avoid signature mismatches
            txt_clip = TextClip(
                font=font,
                text=partial_text,
                font_size=font_size,
                color=color,
                bg_color=bg_color,
                size=size,
                method=method
            )
            
            txt_clip = txt_clip.with_duration(char_duration).with_start(start_time)
            
            # Copy position from original clip
            if hasattr(clip, 'pos'):
                txt_clip = txt_clip.with_position(clip.pos)
            
            clips.append(txt_clip)
        
        # Composite all the progressive text clips
        result = CompositeVideoClip(
            clips,
            size=(clip.w, clip.h) if hasattr(clip, 'w') and hasattr(clip, 'h') else None
        )
        
        # Set the total duration
        total_duration = self.delay + total_chars * char_duration
        if hasattr(clip, 'duration') and clip.duration > total_duration:
            result = result.with_duration(clip.duration)
        else:
            result = result.with_duration(total_duration)
        
        return result
