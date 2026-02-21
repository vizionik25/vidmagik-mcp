from moviepy import Effect
import numpy as np
import cv2

class AutoFraming(Effect):
    """
    Automatically crops and centers the frame on a detected face or a specified focus point.
    Ideal for converting horizontal video to vertical while keeping the subject in frame.
    """
    def __init__(self, target_aspect_ratio: float = 9/16, smoothing: float = 0.9, 
                 focus_func=None):
        """
        Args:
            target_aspect_ratio (float): The aspect ratio of the output (width/height).
            smoothing (float): Smoothing factor (0 to 1). Higher = smoother movement.
            focus_func (callable): Optional function taking (frame, t) and returning (x, y) 
                                 or None. If it returns None, face detection is used.
        """
        self.target_aspect_ratio = target_aspect_ratio
        self.smoothing = smoothing
        self.focus_func = focus_func
        
        # Load the face cascade
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # State for smoothing
        self.current_x = None
        self.current_y = None

    def apply(self, clip):
        def filter(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            target_x, target_y = None, None
            
            # 1. Try custom focus function
            if self.focus_func:
                try:
                    res = self.focus_func(frame, t)
                    if res and len(res) == 2:
                        target_x, target_y = res
                except Exception:
                    pass
            
            # 2. Try face detection if no target yet
            if target_x is None:
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                if len(faces) > 0:
                    # Select the largest face as the main subject
                    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                    target_x = fx + fw / 2
                    target_y = fy + fh / 2
                else:
                    # Fallback to center or last known position
                    target_x = self.current_x if self.current_x is not None else w / 2
                    target_y = self.current_y if self.current_y is not None else h / 2

            # 3. Apply Smoothing (Exponential Moving Average)
            if self.current_x is None:
                self.current_x = target_x
                self.current_y = target_y
            else:
                self.current_x = self.current_x * self.smoothing + target_x * (1 - self.smoothing)
                self.current_y = self.current_y * self.smoothing + target_y * (1 - self.smoothing)

            # 4. Calculate Crop Box
            # Determine dimensions based on target aspect ratio
            if w / h > self.target_aspect_ratio:
                # Source is wider than target (e.g. 16:9 -> 9:16)
                crop_h = h
                crop_w = h * self.target_aspect_ratio
            else:
                # Source is taller than target (e.g. 4:3 -> 1:1)
                crop_w = w
                crop_h = w / self.target_aspect_ratio

            # Initial bounds based on smoothed center
            x1 = int(self.current_x - crop_w / 2)
            y1 = int(self.current_y - crop_h / 2)
            
            # Clamp bounds to ensure the crop box stays within the original frame
            x1 = max(0, min(w - int(crop_w), x1))
            y1 = max(0, min(h - int(crop_h), y1))
            x2 = x1 + int(crop_w)
            y2 = y1 + int(crop_h)

            # Crop the frame
            return frame[y1:y2, x1:x2]

        return clip.transform(filter)
