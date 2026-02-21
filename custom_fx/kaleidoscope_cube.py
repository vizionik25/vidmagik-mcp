from moviepy import Effect
from .kaleidoscope import Kaleidoscope
from .rotating_cube import RotatingCube

class KaleidoscopeCube(Effect):
    """
    A custom effect that combines Kaleidoscope and RotatingCube.
    It first applies a kaleidoscope effect and then maps the result
    onto a rotating 3D cube.
    """
    def __init__(self, kaleidoscope_params=None, cube_params=None):
        """
        :param kaleidoscope_params: A dictionary of parameters for the Kaleidoscope effect.
        :param cube_params: A dictionary of parameters for the RotatingCube effect.
        """
        self.kaleidoscope_params = kaleidoscope_params if kaleidoscope_params is not None else {}
        self.cube_params = cube_params if cube_params is not None else {}
        
        # Instantiate the individual effects
        self.kaleidoscope_effect = Kaleidoscope(**self.kaleidoscope_params)
        self.cube_effect = RotatingCube(**self.cube_params)

    def apply(self, clip):
        """
        Applies the chained effects.
        """
        # Chain the transformations: first kaleidoscope, then rotating cube
        kaleidoscope_clip = self.kaleidoscope_effect.apply(clip)
        final_clip = self.cube_effect.apply(kaleidoscope_clip)
        
        return final_clip
