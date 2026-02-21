from moviepy import Effect
import numpy as np

class Kaleidoscope(Effect):
    """
    A custom effect that creates a kaleidoscope symmetry by taking a wedge 
    of the image and mirroring/rotating it radially.
    """
    def __init__(self, n_slices: int = 6, x: int = None, y: int = None):
        """
        :param n_slices: Number of radial slices. Usually an even number works best for mirroring.
        :param x: Horizontal center of the kaleidoscope. Defaults to clip center.
        :param y: Vertical center of the kaleidoscope. Defaults to clip center.
        """
        self.n_slices = n_slices
        self.x = x
        self.y = y

    def apply(self, clip):
        def filter(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            x_center = self.x if self.x is not None else w // 2
            y_center = self.y if self.y is not None else h // 2
            
            # Create a grid of coordinates
            y_coords, x_coords = np.indices((h, w))
            
            # Relative to center
            y_rel = y_coords - y_center
            x_rel = x_coords - x_center
            
            # Polar coordinates
            r = np.sqrt(x_rel**2 + y_rel**2)
            theta = np.arctan2(y_rel, x_rel)
            
            # Normalize theta to [0, 2*pi)
            theta = theta % (2 * np.pi)
            
            # Map theta to the kaleidoscope slices
            slice_angle = 2 * np.pi / self.n_slices
            
            # Find which slice we are in
            slice_idx = theta // slice_angle
            
            # Normalize theta to [0, slice_angle)
            theta_in_slice = theta % slice_angle
            
            # Mirror every other slice for seamless edges
            mask = (slice_idx % 2 == 1)
            theta_in_slice[mask] = slice_angle - theta_in_slice[mask]
            
            # Convert back to Cartesian for source sampling
            # Using the first slice [0, slice_angle] as the source wedge
            ix = (r * np.cos(theta_in_slice) + x_center).astype(int)
            iy = (r * np.sin(theta_in_slice) + y_center).astype(int)
            
            # Clip indices to be within frame bounds
            ix = np.clip(ix, 0, w - 1)
            iy = np.clip(iy, 0, h - 1)
            
            # Sample input frame at calculated source indices
            return frame[iy, ix]

        return clip.transform(filter)
