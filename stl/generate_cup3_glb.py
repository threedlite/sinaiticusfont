#!/usr/bin/env python3
"""Generate a 3D GLB mesh of the cup3 (depas amphikypellon) from its 14-parameter math model.

Body is a hollow surface of revolution; handles are tube sweeps along trimmed ellipse arcs.
Verification: front-view silhouette is compared against the orange mask via IoU.
"""

import numpy as np
import trimesh


# ============================================================
# Parameters (from render_components.py)
# ============================================================
params = [178.997, 81.674, 443.364, 95.0, 50.316, 2.2,
          21.315, 157.193, 60.234, 138.406, 285.343,
          1.191, 6.198, 17.167]

(body_cx, body_top_y, body_bot_y, top_width, bot_width, taper_exp,
 angle_deg, a_semi, b_semi, ell_cx, ell_cy,
 theta1, theta2, tube_w) = params


SCALE = 0.0005  # m/px → cup height ~18cm
WALL_THICKNESS = 4.0  # px
N_RADIAL = 64
N_TUBE = 24
N_PROFILE = 200


# ============================================================
# Geometry helpers (reused from render_components.py)
# ============================================================
def body_width_at(y):
    t = np.clip((y - body_top_y) / max(body_bot_y - body_top_y, 1), 0, 1)
    return bot_width + (top_width - bot_width) * (1 - t) ** taper_exp


def inside_body(px, py):
    if py < body_top_y or py > body_bot_y:
        return False
    bw = body_width_at(py)
    return abs(px - body_cx) <= bw / 2


def img_to_3d(ix, iy):
    """Convert image coordinates to 3D (Y-up, body centered at origin)."""
    x3 = (ix - body_cx) * SCALE
    y3 = (body_bot_y - iy) * SCALE
    return x3, y3


# ============================================================
# Body mesh (hollow surface of revolution)
# ============================================================
def make_cup_body(effective_bot_y=None):
    """Build body as a single closed-loop revolution for watertight mesh."""
    bot_y = effective_bot_y if effective_bot_y is not None else body_bot_y
    ys = np.linspace(body_top_y, bot_y, N_PROFILE)
    radii_outer = np.array([body_width_at(y) / 2 for y in ys])
    heights = (body_bot_y - ys) * SCALE
    radii_outer_m = radii_outer * SCALE

    radii_inner = np.maximum(radii_outer - WALL_THICKNESS, 0.5)
    radii_inner_m = radii_inner * SCALE

    # Floor: inner surface stops WALL_THICKNESS above outer bottom
    floor_height = heights[-1] + WALL_THICKNESS * SCALE
    inner_mask = heights >= floor_height
    if inner_mask.sum() < 2:
        inner_mask[:] = True
    n_inner = int(inner_mask.sum())

    n_outer = len(radii_outer_m)

    # Build closed profile loop:
    # outer top → outer bottom → floor center (r=0) → inner bottom → inner top → rim closes
    profile_r = np.concatenate([
        radii_outer_m,
        [0.0],
        [0.0],
        radii_inner_m[:n_inner][::-1],
    ])
    profile_h = np.concatenate([
        heights,
        [heights[-1]],
        [floor_height],
        heights[:n_inner][::-1],
    ])

    n_profile = len(profile_r)
    angles = np.linspace(0, 2 * np.pi, N_RADIAL, endpoint=False)

    verts = []
    vert_index = []

    for i in range(n_profile):
        if profile_r[i] < 1e-10:
            idx = len(verts)
            verts.append([0.0, profile_h[i], 0.0])
            vert_index.append([idx] * N_RADIAL)
        else:
            ring = []
            for j in range(N_RADIAL):
                idx = len(verts)
                verts.append([
                    profile_r[i] * np.cos(angles[j]),
                    profile_h[i],
                    profile_r[i] * np.sin(angles[j])
                ])
                ring.append(idx)
            vert_index.append(ring)

    faces = []
    for i in range(n_profile):
        i_next = (i + 1) % n_profile
        for j in range(N_RADIAL):
            jn = (j + 1) % N_RADIAL
            v00 = vert_index[i][j]
            v01 = vert_index[i][jn]
            v10 = vert_index[i_next][j]
            v11 = vert_index[i_next][jn]
            tri1 = [v00, v01, v10]
            tri2 = [v10, v01, v11]
            if len(set(tri1)) == 3:
                faces.append(tri1)
            if len(set(tri2)) == 3:
                faces.append(tri2)

    return np.array(verts), np.array(faces)


# ============================================================
# Handle spine computation (from render_components.py)
# ============================================================
def compute_handle_spine():
    """Compute trimmed left handle spine in image coordinates."""
    phi = np.radians(-angle_deg)
    cos_p, sin_p = np.cos(phi), np.sin(phi)
    n_spine = 400
    thetas_arr = np.linspace(theta1, theta2, n_spine)
    spine = np.zeros((n_spine, 2))
    for i, th in enumerate(thetas_arr):
        u = b_semi * np.cos(th)
        v = a_semi * np.sin(th)
        spine[i, 0] = ell_cx + u * cos_p - v * sin_p
        spine[i, 1] = ell_cy + u * sin_p + v * cos_p

    # Clip at body_bot_y
    keep = spine[:, 1] <= body_bot_y
    spine = spine[keep]

    # Compute tangents and normals for tube edges
    tangents = np.zeros_like(spine)
    tangents[1:-1] = spine[2:] - spine[:-2]
    tangents[0] = spine[1] - spine[0]
    tangents[-1] = spine[-1] - spine[-2]
    lengths = np.sqrt(tangents[:, 0]**2 + tangents[:, 1]**2)
    lengths[lengths < 1e-10] = 1e-10
    tangents /= lengths[:, np.newaxis]
    normals = np.column_stack([-tangents[:, 1], tangents[:, 0]])
    left_edge = spine + normals * tube_w / 2
    right_edge = spine - normals * tube_w / 2

    # Trim where both tube edges are inside the body
    both_inside = np.array([
        inside_body(left_edge[i, 0], left_edge[i, 1]) and
        inside_body(right_edge[i, 0], right_edge[i, 1])
        for i in range(len(spine))
    ])

    # Find longest contiguous run of "outside" points
    outside = ~both_inside
    runs = []
    run_start = None
    for i in range(len(outside)):
        if outside[i]:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                runs.append((run_start, i - 1))
                run_start = None
    if run_start is not None:
        runs.append((run_start, len(outside) - 1))

    best = max(runs, key=lambda r: r[1] - r[0])
    start, end = best
    print(f"  Handle trimmed: kept {start} to {end} of {len(spine)} spine points")
    return spine[start:end + 1], left_edge[start:end + 1], right_edge[start:end + 1]


# ============================================================
# Handle tube mesh
# ============================================================
def make_handle(spine_2d, mirror=False):
    """Build tube mesh along a 2D spine.
    spine_2d: (N, 2) array in image coordinates.
    mirror: if True, mirror across body_cx for right handle.
    """
    if mirror:
        spine_2d = spine_2d.copy()
        spine_2d[:, 0] = 2 * body_cx - spine_2d[:, 0]
        spine_2d = spine_2d[::-1]  # reverse for consistent normals

    n_pts = len(spine_2d)
    tube_r = tube_w / 2 * SCALE

    # Convert to 3D
    centers = np.zeros((n_pts, 3))
    for i in range(n_pts):
        x3, y3 = img_to_3d(spine_2d[i, 0], spine_2d[i, 1])
        centers[i] = [x3, y3, 0.0]

    # Tangents via finite differences
    tangents_3d = np.zeros((n_pts, 3))
    tangents_3d[1:-1] = centers[2:] - centers[:-2]
    tangents_3d[0] = centers[1] - centers[0]
    tangents_3d[-1] = centers[-1] - centers[-2]
    norms = np.sqrt(np.sum(tangents_3d**2, axis=1, keepdims=True))
    norms[norms < 1e-10] = 1.0
    tangents_3d /= norms

    tube_angles = np.linspace(0, 2 * np.pi, N_TUBE, endpoint=False)
    verts = []
    faces = []

    for i in range(n_pts):
        T = tangents_3d[i]
        # Spine is planar (Z=0), so Z-axis is perpendicular to tangent
        ref = np.array([0, 0, 1], dtype=float)
        N = np.cross(T, ref)
        n_len = np.linalg.norm(N)
        if n_len > 1e-10:
            N /= n_len
        else:
            N = np.array([1, 0, 0], dtype=float)
        B = np.cross(T, N)
        B /= max(np.linalg.norm(B), 1e-10)

        for j in range(N_TUBE):
            offset = tube_r * (np.cos(tube_angles[j]) * N +
                               np.sin(tube_angles[j]) * B)
            verts.append(centers[i] + offset)

    # Quad strip faces
    for i in range(n_pts - 1):
        for j in range(N_TUBE):
            jn = (j + 1) % N_TUBE
            v00 = i * N_TUBE + j
            v01 = i * N_TUBE + jn
            v10 = (i + 1) * N_TUBE + j
            v11 = (i + 1) * N_TUBE + jn
            faces.append([v00, v01, v10])
            faces.append([v10, v01, v11])

    # No end caps — handle ends are embedded in the body wall

    return np.array(verts), np.array(faces)



# ============================================================
# Main
# ============================================================
def main():
    print("=== Generating cup3.glb ===")

    print("Computing handle spine...")
    spine_left, left_edge, right_edge = compute_handle_spine()
    print(f"  Left handle spine: {len(spine_left)} points")

    # Truncate body at bottom handle stroke edge (not spine center)
    if spine_left[0, 1] > spine_left[-1, 1]:
        effective_bot = max(left_edge[0, 1], right_edge[0, 1])
    else:
        effective_bot = max(left_edge[-1, 1], right_edge[-1, 1])
    print(f"  Body bottom truncated: {body_bot_y:.1f} -> {effective_bot:.1f}")

    print(f"  Wall thickness: {WALL_THICKNESS:.1f} px")

    print("Building cup body...")
    body_v, body_f = make_cup_body(effective_bot_y=effective_bot)
    body_mesh = trimesh.Trimesh(vertices=body_v, faces=body_f, process=False)

    # Build inner radius lookup for clipping handles
    ys_profile = np.linspace(body_top_y, effective_bot, N_PROFILE)
    radii_outer_profile = np.array([body_width_at(y) / 2 for y in ys_profile])
    radii_inner_profile = np.maximum(radii_outer_profile - WALL_THICKNESS, 0.5)
    heights_profile = (body_bot_y - ys_profile) * SCALE
    radii_inner_m = radii_inner_profile * SCALE

    def clip_handle_to_inner_wall(verts, faces):
        """Clamp handle vertices that penetrate the cup interior to the inner wall.
        Remove faces where all 3 vertices are inside (fully embedded in body)."""
        clipped = np.zeros(len(verts), dtype=bool)
        for i in range(len(verts)):
            x, y, z = verts[i]
            r = np.sqrt(x**2 + z**2)
            if r < 1e-10:
                continue
            # heights_profile goes from high (top) to low (bottom)
            if y <= heights_profile[-1] or y >= heights_profile[0]:
                continue
            r_inner = np.interp(y, heights_profile[::-1], radii_inner_m[::-1])
            if r < r_inner:
                verts[i, 0] = x / r * r_inner
                verts[i, 2] = z / r * r_inner
                clipped[i] = True
        n_clipped = int(clipped.sum())
        keep = ~(clipped[faces[:, 0]] & clipped[faces[:, 1]] & clipped[faces[:, 2]])
        faces_out = faces[keep]
        n_removed = len(faces) - len(faces_out)

        # Cap boundary loops where interior faces were removed
        verts, faces_out = _cap_boundary_loops(verts, faces_out)

        return verts, faces_out, n_clipped, n_removed

    def _cap_boundary_loops(verts, faces):
        """Find boundary edge loops and fill them with triangle fans."""
        edges = {}
        for f in faces:
            for i in range(3):
                e = tuple(sorted((f[i], f[(i+1) % 3])))
                edges[e] = edges.get(e, 0) + 1
        boundary = [e for e, cnt in edges.items() if cnt == 1]
        if not boundary:
            return verts, faces

        adj = {}
        for a, b in boundary:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)

        visited = set()
        loops = []
        for start in adj:
            if start in visited:
                continue
            loop = [start]
            visited.add(start)
            cur = start
            while True:
                neighbors = [n for n in adj[cur] if n not in visited]
                if not neighbors:
                    break
                nxt = neighbors[0]
                loop.append(nxt)
                visited.add(nxt)
                cur = nxt
            if len(loop) >= 3:
                loops.append(loop)

        verts_list = list(verts) if isinstance(verts, np.ndarray) else verts
        faces_list = list(faces) if isinstance(faces, np.ndarray) else faces
        n_caps = 0
        for loop in loops:
            center = np.mean([verts_list[i] for i in loop], axis=0)
            ci = len(verts_list)
            verts_list.append(center)
            for i in range(len(loop)):
                a = loop[i]
                b = loop[(i + 1) % len(loop)]
                faces_list.append([ci, a, b])
            n_caps += 1

        print(f"    Capped {n_caps} boundary loops ({len(boundary)} boundary edges)")
        return np.array(verts_list), np.array(faces_list)

    print("Building left handle tube...")
    lh_v, lh_f = make_handle(spine_left, mirror=False)
    lh_v, lh_f, n, nr = clip_handle_to_inner_wall(lh_v, lh_f)
    print(f"  Clipped {n} vertices, removed {nr} interior faces")
    lh_mesh = trimesh.Trimesh(vertices=lh_v, faces=lh_f, process=False)

    print("Building right handle tube...")
    rh_v, rh_f = make_handle(spine_left, mirror=True)
    rh_v, rh_f, n, nr = clip_handle_to_inner_wall(rh_v, rh_f)
    print(f"  Clipped {n} vertices, removed {nr} interior faces")
    rh_mesh = trimesh.Trimesh(vertices=rh_v, faces=rh_f, process=False)

    print("Combining meshes...")
    combined = trimesh.util.concatenate([body_mesh, lh_mesh, rh_mesh])
    # Normals are set by construction (known winding order)

    # Dark burnt sienna pottery color
    color = [112, 56, 27, 255]
    combined.visual = trimesh.visual.ColorVisuals(
        mesh=combined,
        face_colors=np.tile(color, (len(combined.faces), 1))
    )

    # Bounding box
    bb_min = combined.vertices.min(axis=0)
    bb_max = combined.vertices.max(axis=0)
    bb_size = bb_max - bb_min
    print(f"Bounding box (m):  X={bb_size[0]:.4f} Y={bb_size[1]:.4f} Z={bb_size[2]:.4f}")
    print(f"Bounding box (cm): X={bb_size[0]*100:.1f} Y={bb_size[1]*100:.1f} Z={bb_size[2]*100:.1f}")

    # Export GLB
    out_path = "/Users/user1/cup/cup3/cup3.glb"
    combined.export(out_path, file_type='glb')
    print(f"\nExported {out_path}")
    print(f"  Vertices: {len(combined.vertices)}")
    print(f"  Faces:    {len(combined.faces)}")

    # Export STL with Z-up orientation for 3D printing, scaled to 6in height
    stl_mesh = combined.copy()
    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    stl_mesh.apply_transform(rot)
    stl_mesh.vertices[:, 2] -= stl_mesh.vertices[:, 2].min()  # bottom at Z=0
    current_height = stl_mesh.vertices[:, 2].max()
    target_height = 6.0 * 0.0254  # 6 inches in meters
    scale_factor = target_height / current_height
    stl_mesh.apply_scale(scale_factor)
    stl_path = "/Users/user1/cup/cup3/cup3.stl"
    stl_mesh.export(stl_path)
    sz = stl_mesh.bounds[1] - stl_mesh.bounds[0]
    print(f"Exported {stl_path} (Z-up, height={sz[2]*100/2.54:.2f}in)")
    print(f"  Watertight: {stl_mesh.is_watertight}")
    if not stl_mesh.is_watertight:
        print(f"  WARNING: mesh is not watertight — may cause issues with slicers")

    print("\nDone!")


if __name__ == "__main__":
    main()
