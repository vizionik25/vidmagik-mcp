import moviepy
print(f"MoviePy version: {moviepy.__version__}")
import moviepy.video
# print(dir(moviepy.video))
try:
    from moviepy.video.drawing import color_gradient
    print("Found in moviepy.video.drawing")
except ImportError:
    print("Not in moviepy.video.drawing")

try:
    from moviepy.video.VideoClip import ColorClip
    print("ColorClip found in moviepy.video.VideoClip")
except ImportError:
    print("ColorClip not in moviepy.video.VideoClip")

import pkgutil
package = moviepy
for loader, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
    if "drawing" in name or "gradient" in name:
        print(name)
