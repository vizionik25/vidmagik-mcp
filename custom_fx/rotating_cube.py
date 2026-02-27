"""
RotatingCube - Interior Corner Perspective Effect (Ray-Cast Implementation)

Simulates standing inside a cube looking at a corner where 3 faces meet.
Uses ray-casting — each output pixel casts a ray into the rotated cube and
samples the source frame at the UV intersection point. Geometrically correct
for interior rendering with no backface-culling ambiguity.

The cube rotates around the fixed camera via a 3-axis lemniscate (figure-8):
  theta (X-pitch) = A * sin(w*t)
  phi   (Y-yaw)   = A * sin(2*w*t) / 2
  psi   (Z-roll)  = A * sin(2*w*t) * sin(w*t) / 2
"""

from moviepy import Effect
import numpy as np


class RotatingCube(Effect):
    """
    Interior perspective of a cube rotating in a figure-8 (lemniscate) pattern.

    The camera is fixed at the origin inside the cube, aimed at the corner
    where three faces meet (+X right wall, +Y floor, +Z front wall).
    Each rotation axis (pitch/X, yaw/Y, roll/Z) can be driven at an
    independent speed, enabling true 3-axis independent motion.

    Parameters
    ----------
    speed : float
        Base oscillation frequency in degrees/sec applied to all axes
        unless overridden by speed_x / speed_y / speed_z.
    zoom : float
        Focal length multiplier. Higher = more telephoto, tighter corner.
    amplitude : float
        Angular sweep in degrees — how far each axis oscillates.
    speed_x : float, optional
        Independent pitch (X-axis) speed in degrees/sec. Overrides speed.
    speed_y : float, optional
        Independent yaw (Y-axis) speed in degrees/sec. Overrides speed.
    speed_z : float, optional
        Independent roll (Z-axis) speed in degrees/sec. Overrides speed.
    """

    def __init__(
        self,
        speed: float = 45.0,
        zoom: float = 1.0,
        amplitude: float = 40.0,
        speed_x: float = None,
        speed_y: float = None,
        speed_z: float = None,
    ):
        base = max(abs(speed), 1.0)
        self.speed_x = max(abs(speed_x), 1.0) if speed_x is not None else base
        self.speed_y = max(abs(speed_y), 1.0) if speed_y is not None else base
        self.speed_z = max(abs(speed_z), 1.0) if speed_z is not None else base
        self.zoom = zoom
        self.amplitude = np.deg2rad(amplitude)

    # ------------------------------------------------------------------
    # Rotation matrix helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _Rx(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)

    @staticmethod
    def _Ry(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)

    @staticmethod
    def _Rz(a):
        c, s = np.cos(a), np.sin(a)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)

    # ------------------------------------------------------------------
    # Effect apply
    # ------------------------------------------------------------------

    def apply(self, clip):

        def filter_frame(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]

            S     = max(w, h) * 0.85          # cube half-size
            focal = max(w, h) * self.zoom
            cx, cy = w * 0.5, h * 0.5

            # --- 3-axis independent angles ---
            omega_x = np.deg2rad(self.speed_x)
            omega_y = np.deg2rad(self.speed_y)
            omega_z = np.deg2rad(self.speed_z)
            A = self.amplitude

            theta = A * np.sin(omega_x * t)          # pitch X
            phi   = A * np.sin(omega_y * t) * 0.5   # yaw   Y
            psi   = A * np.sin(omega_z * t) * 0.5   # roll  Z

            # Base rotation: orient camera toward the (+X,+Y,+Z) corner
            # yaw 45° right + pitch 35.26° up = look at (1,1,1)/sqrt(3)
            R_base = self._Ry(np.deg2rad(45.0)) @ self._Rx(np.deg2rad(-35.26))

            # Lemniscate oscillation applied on top of the base orientation
            R_lemni = self._Rz(psi) @ self._Ry(phi) @ self._Rx(theta)

            # Final rotation: base then oscillate.
            # R_inv (transpose) transforms world rays into cube-local space.
            R     = R_base @ R_lemni
            R_inv = R.T  # orthogonal matrix: inverse = transpose

            # --- Build per-pixel ray directions ---
            Y_idx, X_idx = np.mgrid[0:h, 0:w]
            rx = (X_idx - cx) / focal
            ry = (Y_idx - cy) / focal
            rz = np.ones((h, w), dtype=np.float64)

            # Transform rays into cube-local space: (h*w, 3)
            rays_flat  = np.stack([rx.ravel(), ry.ravel(), rz.ravel()], axis=1)
            rays_local = (R_inv @ rays_flat.T).T.reshape(h, w, 3)

            # --- Ray-cube intersection ---
            # For each of 6 axis-aligned faces, compute the hit distance t and
            # the UV coords. Track the nearest positive-t hit per pixel.
            #
            # Face spec: (normal_axis, sign, u_tangent_axis, v_tangent_axis)
            #   normal_axis: 0=X, 1=Y, 2=Z
            #   sign:        +1 or -1 (which side of the axis)
            #   u/v axes:    the two remaining axes used for UV coords
            faces = [
                (0,  1, 2, 1),  # +X right wall   u=Z  v=Y
                (0, -1, 2, 1),  # -X left wall    u=Z  v=Y
                (1,  1, 0, 2),  # +Y floor        u=X  v=Z
                (1, -1, 0, 2),  # -Y ceiling      u=X  v=Z
                (2,  1, 0, 1),  # +Z front wall   u=X  v=Y
                (2, -1, 0, 1),  # -Z back wall    u=X  v=Y
            ]

            best_t = np.full((h, w), np.inf)
            result = np.zeros((h, w, 3), dtype=np.uint8)
            eps = 1e-4

            for axis, sign, u_ax, v_ax in faces:

                d = rays_local[..., axis]          # ray component along this axis
                valid = np.abs(d) > eps            # avoid division by zero

                # Distance to the face plane
                t_hit = np.where(valid, (sign * S) / d, np.inf)

                # Intersection point
                ix = rays_local[..., 0] * t_hit
                iy = rays_local[..., 1] * t_hit
                iz = rays_local[..., 2] * t_hit

                # Valid hit: t > 0 and intersection within face bounds
                hit = (
                    valid &
                    (t_hit > 0) &
                    (np.abs(ix) <= S + eps) &
                    (np.abs(iy) <= S + eps) &
                    (np.abs(iz) <= S + eps)
                )

                # UV — the two tangent-axis components, mapped [-S,S] → [0, dim-1]
                inter = np.stack([ix, iy, iz], axis=-1)
                u_world = inter[..., u_ax]
                v_world = inter[..., v_ax]

                u_px = np.clip(((u_world + S) / (2.0 * S)) * (w - 1), 0, w - 1)
                v_px = np.clip(((v_world + S) / (2.0 * S)) * (h - 1), 0, h - 1)

                # Keep nearest hit
                update = hit & (t_hit < best_t)
                best_t = np.where(update, t_hit, best_t)

                u_int = u_px.astype(np.int32)
                v_int = v_px.astype(np.int32)
                result[update] = frame[v_int[update], u_int[update]]

            return result

        return clip.transform(filter_frame)
