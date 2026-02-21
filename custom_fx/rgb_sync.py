from moviepy import Effect
import numpy as np

class RGBSync(Effect):
    """
    Splits the RGB channels and applies spatial and/or temporal offsets
    to create a "sync" or "split" glitch effect.
    
    Parameters:
    -----------
    r_offset : tuple (x, y)
        Pixel offset for the Red channel.
    g_offset : tuple (x, y)
        Pixel offset for the Green channel.
    b_offset : tuple (x, y)
        Pixel offset for the Blue channel.
    r_time_offset : float
        Time offset (seconds) for the Red channel.
    g_time_offset : float
        Time offset (seconds) for the Green channel.
    b_time_offset : float
        Time offset (seconds) for the Blue channel.
    """
    def __init__(self, 
                 r_offset=(0, 0), g_offset=(0, 0), b_offset=(0, 0),
                 r_time_offset=0, g_time_offset=0, b_time_offset=0):
        self.offsets = [r_offset, g_offset, b_offset]
        self.time_offsets = [r_time_offset, g_time_offset, b_time_offset]

    def apply(self, clip):
        def filter(get_frame, t):
            # Get frames for each channel based on time offsets
            # We use float32 for processing and then clip back to uint8
            channels = []
            for i in range(3):
                # Calculate the timestamp for this specific channel
                # Ensure it stays within clip bounds [0, duration]
                channel_t = max(0, min(clip.duration, t + self.time_offsets[i])) if clip.duration else t + self.time_offsets[i]
                
                frame = get_frame(channel_t)
                channel_data = frame[:, :, i]
                
                # Apply spatial offset using np.roll (wraps around)
                # axis 0 is Y, axis 1 is X
                if self.offsets[i] != (0, 0):
                    channel_data = np.roll(channel_data, shift=self.offsets[i], axis=(1, 0))
                
                channels.append(channel_data)
            
            return np.stack(channels, axis=-1)

        return clip.transform(filter)

# Usage Example:
# effect = RGBSync(r_offset=(5, 0), b_offset=(-5, 0), g_time_offset=0.05)
# clip = clip.apply_effect(effect)
