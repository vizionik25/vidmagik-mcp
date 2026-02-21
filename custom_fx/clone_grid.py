from moviepy import Effect
import numpy as np
import cv2

class CloneGrid(Effect):
    """
    Creates a grid of clones of the original clip.
    Supported number of clones: 2, 4, 8, 16, 32, 64.
    The effect automatically determines the best grid layout (rows x columns).
    """
    def __init__(self, n_clones: int = 4):
        """
        Args:
            n_clones (int): Number of clones in the grid. 
                           Recommended values: 2, 4, 8, 16, 32, 64.
        """
        self.n_clones = n_clones
        self.rows, self.cols = self._calculate_grid(n_clones)

    def _calculate_grid(self, n):
        # Specific mappings for the requested powers of 2
        # or a general logic for any power of 2
        import math
        k = math.log2(n)
        if k.is_integer():
            k = int(k)
            rows = 2 ** (k // 2)
            cols = 2 ** (k // 2 + k % 2)
            return rows, cols
        else:
            # Fallback for non-powers of 2: try to make it as square as possible
            cols = math.ceil(math.sqrt(n))
            rows = math.ceil(n / cols)
            return rows, cols

    def apply(self, clip):
        def filter(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Target size for each clone
            # We want the final composite to be the same size as the original
            # so each clone must be resized to (w/cols, h/rows)
            target_w = w // self.cols
            target_h = h // self.rows
            
            # Handle potential rounding issues by adjusting the last clones or 
            # just resizing to exact division and letting the grid fit.
            # Best approach: resize one clone and tile it.
            small_frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
            
            # Tile the small frame
            # np.tile on (H, W, 3) with (R, C, 1) repeats
            grid = np.tile(small_frame, (self.rows, self.cols, 1))
            
            # If rounding caused the grid to be slightly smaller than the original,
            # we might want to pad or resize back. But usually w//cols * cols is close enough.
            # To be safe and maintain original dimensions:
            if grid.shape[0] != h or grid.shape[1] != w:
                grid = cv2.resize(grid, (w, h), interpolation=cv2.INTER_NEAREST)
                
            return grid

        return clip.transform(filter)
