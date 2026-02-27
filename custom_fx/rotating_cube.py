"""
RotatingCube - Interior Corner Perspective Effect

Simulates standing inside a cube looking at a corner where 3 faces meet.
The cube walls rotate around the viewer in a figure-8 (lemniscate) pattern
driven by full 3-axis (pitch/yaw/roll) oscillation so each face is
independently animated through the infinity-curve path.
"""

from moviepy import Effect
import numpy as np
import cv2


class RotatingCube(Effect):
    """
    Interior perspective of a cube rotating in a figure-8 (lemniscate) pattern.

    The camera is fixed at the origin inside the cube, aimed at the corner
    where three faces meet (+X right wall, +Y floor, +Z front wall).
    All three rotation axes are driven independently by the lemniscate so
    each face swings through the figure-8 path distinctly.

    Parameters
    ----------
    speed : float
        Base oscillation frequency in degrees/sec. All 3 axes derive from this.
    zoom : float
        Focal length multiplier. Higher = tighter / more telephoto corner view.
    amplitude : float
        Angular sweep amplitude in degrees (half-range of the figure-8 swing).
    """

    def __init__(
        self,
        speed: float = 45.0,
        zoom: float = 1.0,
        amplitude: float = 40.0,
        # Legacy compat — ignored by the new implementation
        speed_x: float = None,
        speed_y: float = None,
    ):
        # If called via old main.py path (speed_x/speed_y), derive speed from them
        if speed_x is not None or speed_y is not None:
            self.speed = max(abs(speed_x or 0), abs(speed_y or 0), 1.0)
        else:
            self.speed = max(abs(speed), 1.0)
        self.zoom = zoom
        self.amplitude = np.deg2rad(amplitude)

    # ------------------------------------------------------------------
    # Rotation matrix helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _Rx(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[1, 0, 0],
                         [0, c, -s],
                         [0, s,  c]], dtype=np.float64)

    @staticmethod
    def _Ry(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[ c, 0, s],
                         [ 0, 1, 0],
                         [-s, 0, c]], dtype=np.float64)

    @staticmethod
    def _Rz(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[c, -s, 0],
                         [s,  c, 0],
                         [0,  0, 1]], dtype=np.float64)

    @staticmethod
    def _project(pts_3d, focal, cx, cy):
        """
        Perspective-project Nx3 points to Nx2 screen coords.
        Returns None if any point is behind or at the camera plane.
        """
        out = []
        for x, y, z in pts_3d:
            if z <= 0.01:
                return None
            out.append([focal * x / z + cx,
                        focal * y / z + cy])
        return np.array(out, dtype=np.float32)

    # ------------------------------------------------------------------
    # Effect apply
    # ------------------------------------------------------------------

    def apply(self, clip):

        def filter_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]

            S = max(w, h) * 0.85          # cube half-size — slightly less than frame
            focal = max(w, h) * self.zoom
            cx, cy = w * 0.5, h * 0.5

            # --- 3-axis lemniscate (figure-8) angles ---
            # ω in rad/sec from degrees/sec speed
            omega = np.deg2rad(self.speed)
            A = self.amplitude

            # θ (pitch / X-axis): primary oscillation → drives +Y floor face
            theta = A * np.sin(omega * t)
            # φ (yaw   / Y-axis): double-frequency   → drives +X right wall face
            phi   = A * np.sin(2.0 * omega * t) * 0.5
            # ψ (roll  / Z-axis): coupled product     → drives +Z front wall face
            psi   = A * np.sin(2.0 * omega * t) * np.sin(omega * t) * 0.5

            # Combined rotation: cube rotates around the fixed interior camera
            R = self._Rz(psi) @ self._Ry(phi) @ self._Rx(theta)

            # --- Interior face definitions ---
            # Each face is a quad of 4 corners wound so that
            # cross(v1-v0, v3-v0) points OUTWARD from cube centre.
            # A face is VISIBLE from inside when its outward normal,
            # after rotation, has NEGATIVE Z (faces into the camera).
            #
            # Winding order matches cv2 src_pts: TL → TR → BR → BL
            faces = [
                # +X  right wall
                np.array([[ S, -S,  S],
                           [ S, -S, -S],
                           [ S,  S, -S],
                           [ S,  S,  S]], dtype=np.float64),
                # -X  left wall
                np.array([[-S, -S, -S],
                           [-S, -S,  S],
                           [-S,  S,  S],
                           [-S,  S, -S]], dtype=np.float64),
                # +Y  floor
                np.array([[-S,  S,  S],
                           [ S,  S,  S],
                           [ S,  S, -S],
                           [-S,  S, -S]], dtype=np.float64),
                # -Y  ceiling
                np.array([[-S, -S, -S],
                           [ S, -S, -S],
                           [ S, -S,  S],
                           [-S, -S,  S]], dtype=np.float64),
                # +Z  front wall
                np.array([[-S, -S,  S],
                           [ S, -S,  S],
                           [ S,  S,  S],
                           [-S,  S,  S]], dtype=np.float64),
                # -Z  back wall
                np.array([[ S, -S, -S],
                           [-S, -S, -S],
                           [-S,  S, -S],
                           [ S,  S, -S]], dtype=np.float64),
            ]

            # Source corners: TL → TR → BR → BL
            src_pts = np.array([[0, 0], [w, 0], [w, h], [0, h]],
                               dtype=np.float32)

            # Collect visible faces
            visible = []
            for verts in faces:
                rot = (R @ verts.T).T          # shape (4, 3)

                # Outward normal (cross product of two edges)
                normal = np.cross(rot[1] - rot[0], rot[3] - rot[0])

                # Interior visibility: outward normal must point INTO camera (neg Z)
                if normal[2] >= 0:
                    continue

                pts2d = self._project(rot, focal, cx, cy)
                if pts2d is None:
                    continue

                mean_z = rot[:, 2].mean()
                visible.append((mean_z, pts2d))

            # Painter's algorithm: most-negative Z (farthest) drawn first
            visible.sort(key=lambda x: x[0])

            canvas = np.zeros_like(frame)
            for _, dst_pts in visible:
                try:
                    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                    warped = cv2.warpPerspective(frame, M, (w, h))
                    mask = np.any(warped > 0, axis=-1)
                    canvas[mask] = warped[mask]
                except cv2.error:
                    continue

            return canvas

        return clip.transform(filter_frame)
