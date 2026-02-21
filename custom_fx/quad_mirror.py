from moviepy import Effect
import numpy as np

class QuadMirror(Effect):
    """
    A custom effect that mirrors the clip both horizontally and vertically
    based on a custom center (x, y).
    """
    def __init__(self, x: int = None, y: int = None):
        self.x = x
        self.y = y

    def apply(self, clip):
        def filter(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            x_center = self.x if self.x is not None else w // 2
            y_center = self.y if self.y is not None else h // 2
            
            # Ensure center is within bounds
            x_center = int(max(0, min(w - 1, x_center)))
            y_center = int(max(0, min(h - 1, y_center)))
            
            idx_x = np.arange(w)
            idx_x = np.where(idx_x <= x_center, idx_x, 2 * x_center - idx_x)
            idx_x = np.clip(idx_x, 0, x_center)
            
            idx_y = np.arange(h)
            idx_y = np.where(idx_y <= y_center, idx_y, 2 * y_center - idx_y)
            idx_y = np.clip(idx_y, 0, y_center)
            
            return frame[idx_y][:, idx_x]

        return clip.transform(filter)
