from moviepy import Effect
import numpy as np
import cv2

class RotatingCube(Effect):
    """
    Simulates a 3D rotating cube effect where the video is mapped to the faces.
    Enhanced version with multi-axis rotation, optional quad mirroring, 
    and circular/elliptical motion paths.
    """
    def __init__(self, 
                 speed_x: float = 45, 
                 speed_y: float = 30, 
                 zoom: float = 1.0, 
                 mirror: bool = True,
                 motion_radius: float = 0.1,
                 motion_speed: float = 20):
        """
        Args:
            speed_x (float): Rotation speed around X axis (degrees/sec).
            speed_y (float): Rotation speed around Y axis (degrees/sec).
            zoom (float): Zoom factor. Higher values make the cube appear closer.
            mirror (bool): If True, applies a quad-mirror effect to the video before mapping.
            motion_radius (float): Radius of the circular motion path (fraction of screen size).
            motion_speed (float): Speed of the circular motion (degrees/sec).
        """
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.zoom = zoom
        self.mirror = mirror
        self.motion_radius = motion_radius
        self.motion_speed = motion_speed

    def _apply_quad_mirror(self, frame):
        h, w = frame.shape[:2]
        xc, yc = w // 2, h // 2
        idx_x = np.arange(w)
        idx_x = np.where(idx_x <= xc, idx_x, 2 * xc - idx_x)
        idx_x = np.clip(idx_x, 0, xc)
        idx_y = np.arange(h)
        idx_y = np.where(idx_y <= yc, idx_y, 2 * yc - idx_y)
        idx_y = np.clip(idx_y, 0, yc)
        return frame[idx_y][:, idx_x]

    def apply(self, clip):
        def filter(get_frame, t):
            raw_frame = get_frame(t)
            frame = self._apply_quad_mirror(raw_frame) if self.mirror else raw_frame
            h, w = frame.shape[:2]
            
            # Rotation angles
            ax = np.deg2rad((self.speed_x * t) % 360)
            ay = np.deg2rad((self.speed_y * t) % 360)
            
            # Motion path offset
            m_rad = np.deg2rad((self.motion_speed * t) % 360)
            off_x = w * self.motion_radius * np.cos(m_rad)
            off_y = h * self.motion_radius * np.sin(m_rad)
            
            # Perspective parameters
            focal_length = max(w, h) * self.zoom
            dist = max(w, h) / 2
            
            # Define 6 faces (Front, Back, Top, Bottom, Right, Left)
            cube_faces = [
                np.array([[-w/2, -h/2,  dist], [ w/2, -h/2,  dist], [ w/2,  h/2,  dist], [-w/2,  h/2,  dist]]), # Front
                np.array([[ w/2, -h/2, -dist], [-w/2, -h/2, -dist], [-w/2,  h/2, -dist], [ w/2,  h/2, -dist]]), # Back
                np.array([[-w/2, -dist, -h/2], [ w/2, -dist, -h/2], [ w/2, -dist,  h/2], [-w/2, -dist,  h/2]]), # Top
                np.array([[-w/2,  dist,  h/2], [ w/2,  dist,  h/2], [ w/2,  dist, -h/2], [-w/2,  dist, -h/2]]), # Bottom
                np.array([[ dist, -h/2,  w/2], [ dist, -h/2, -w/2], [ dist,  h/2, -w/2], [ dist,  h/2,  w/2]]), # Right
                np.array([[-dist, -h/2, -w/2], [-dist, -h/2,  w/2], [-dist,  h/2,  w/2], [-dist,  h/2, -w/2]]), # Left
            ]

            # Rotation Matrices
            cx, sx = np.cos(ax), np.sin(ax)
            Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
            cy, sy = np.cos(ay), np.sin(ay)
            Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            
            R = Ry @ Rx # Combined rotation

            # Project and sort faces by depth
            rendered_faces = []
            for face_pts in cube_faces:
                # Rotate
                rot_pts = face_pts @ R.T
                
                # Check visibility (backface culling)
                v1 = rot_pts[1] - rot_pts[0]
                v2 = rot_pts[3] - rot_pts[0]
                normal = np.cross(v1, v2)
                if normal[2] <= 0: # Facing away
                    continue
                
                # Project
                points_2d = []
                visible = True
                avg_z = np.mean(rot_pts[:, 2])
                
                for x, y, z in rot_pts:
                    if z <= 0.1:
                        visible = False
                        break
                    px = (x * focal_length / z) + w/2 + off_x
                    py = (y * focal_length / z) + h/2 + off_y
                    points_2d.append([px, py])
                
                if visible:
                    rendered_faces.append((avg_z, np.array(points_2d, dtype=np.float32)))

            # Sort by depth (farthest first)
            rendered_faces.sort(key=lambda x: x[0], reverse=True)

            # Draw
            canvas = np.zeros_like(frame)
            src_pts = np.array([[0,0], [w,0], [w,h], [0,h]], dtype=np.float32)
            
            for _, dst_pts in rendered_faces:
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                face_img = cv2.warpPerspective(frame, M, (w, h))
                mask = np.any(face_img > 0, axis=-1)
                canvas[mask] = face_img[mask]
            
            return canvas

        return clip.transform(filter)
