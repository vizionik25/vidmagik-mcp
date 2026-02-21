from moviepy import Effect
import numpy as np

class ChromaKey(Effect):
    """
    An advanced Chroma Key effect that creates a mask for transparency
    based on the distance from a target color.
    
    Parameters:
    -----------
    color : tuple (R, G, B)
        The target color to remove (e.g., (0, 255, 0) for green screen).
    threshold : float
        The distance threshold below which pixels are fully transparent.
    softness : float
        The range over which pixels transition from transparent to opaque.
    """
    def __init__(self, color=(0, 255, 0), threshold=50, softness=20):
        self.color = np.array(color)
        self.threshold = threshold
        self.softness = softness

    def apply(self, clip):
        def filter(image):
            # Calculate Euclidean distance to target color
            # Use float32 to avoid overflow during squaring
            dist = np.sqrt(np.sum((image.astype('float32') - self.color)**2, axis=-1))
            
            # Create a smooth mask
            # 0.0 is transparent, 1.0 is opaque
            if self.softness > 0:
                mask = np.clip((dist - self.threshold) / self.softness, 0, 1)
            else:
                mask = (dist > self.threshold).astype('float32')
            
            # MoviePy masks are usually 2D arrays of floats [0, 1]
            # If the clip already has a mask, we should combine them
            if clip.mask is not None:
                old_mask = clip.mask.get_frame(0) # Simplified for image_transform context
                # Note: combining with existing mask is tricky in image_transform
                # Usually better to set the mask explicitly
                pass

            return mask

        # In MoviePy, we apply the mask to the clip
        mask_clip = clip.image_transform(filter)
        return clip.with_mask(mask_clip)

# Usage Example:
# clip = VideoFileClip("greenscreen.mp4")
# keyed_clip = ChromaKey(color=(0, 255, 0), threshold=60, softness=30).apply(clip)
