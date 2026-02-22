#!/usr/bin/env python3
"""Generate a 3D GLB mesh of cup4 from its math model.

5 components: lip (flared top), body (tapered), base (circular arc + flat bottom),
two mirrored handle tubes. Color: silver.
"""

import numpy as np
import trimesh

# ============================================================
# Parameters (from render_components.py)
# ============================================================
params = [1587, 460, 1850, 1320, 990, 2.5,
          -50, 454, 658, 980, 1090,
          0.3, 6.0, 153]

(body_cx, body_top_y, body_bot_y, top_width, bot_width, taper_exp,
 angle_deg, a_semi, b_semi, ell_cx, ell_cy,
 theta1, theta2, tube_w) = params

IMG_H, IMG_W = 2200, 3200
WALL_THICKNESS = 45.0  # px
N_RADIAL = 128
N_TUBE = 48


def body_width_at(y):
    t = np.clip((y - body_top_y) / max(body_bot_y - body_top_y, 1), 0, 1)
    return bot_width + (top_width - bot_width) * (1 - t) ** taper_exp


def inside_body(px, py):
    if py < body_top_y or py > body_bot_y:
        return False
    bw = body_width_at(py)
    return abs(px - body_cx) <= bw / 2


# ============================================================
# Handle spine computation
# ============================================================
def compute_handle_spine():
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

    keep = spine[:, 1] <= body_bot_y
    spine = spine[keep]

    tangents = np.zeros_like(spine)
    tangents[1:-1] = spine[2:] - spine[:-2]
    tangents[0] = spine[1] - spine[0]
    tangents[-1] = spine[-1] - spine[-2]
    lengths = np.sqrt(tangents[:, 0]**2 + tangents[:, 1]**2)
    lengths[lengths < 1e-10] = 1e-10
    tangents /= lengths[:, np.newaxis]
    normals = np.column_stack([-tangents[:, 1], tangents[:, 0]])
    # Vary tube width: tube_w at top, tube_w*1.5 at bottom
    y_min, y_max = spine[:, 1].min(), spine[:, 1].max()
    t_spine = (spine[:, 1] - y_min) / max(y_max - y_min, 1)
    tube_half_w = (tube_w + tube_w * 0.5 * t_spine) / 2
    left_edge = spine + normals * tube_half_w[:, np.newaxis]
    right_edge = spine - normals * tube_half_w[:, np.newaxis]

    both_inside = np.array([
        inside_body(left_edge[i, 0], left_edge[i, 1]) and
        inside_body(right_edge[i, 0], right_edge[i, 1])
        for i in range(len(spine))
    ])

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
    return (spine[start:end + 1], left_edge[start:end + 1],
            right_edge[start:end + 1], tube_half_w[start:end + 1],
            spine, tube_half_w, start, end)


# ============================================================
# Build outer profile (lip + body + base arc)
# ============================================================
def build_outer_profile(body_actual_top, body_actual_bot):
    """Returns (ys_img, radii_px, lip_rim_y, flat_y) from top to bottom."""

    # --- Lip ---
    lip_rim_y = body_actual_top - 0.726 * (body_actual_top - body_top_y)
    lip_bot_width = body_width_at(body_actual_top)
    lip_ys = np.linspace(lip_rim_y, body_actual_top, 100)
    lip_t = (body_actual_top - lip_ys) / max(body_actual_top - lip_rim_y, 1)
    lip_height = body_actual_top - lip_rim_y

    t_junc = (body_actual_top - body_top_y) / max(body_bot_y - body_top_y, 1)
    body_slope = ((top_width - bot_width) / 2 * taper_exp *
                  (1 - t_junc) ** (taper_exp - 1) / (body_bot_y - body_top_y))
    slope_at_rim = 0.3
    lip_r_bot = lip_bot_width / 2
    extra = slope_at_rim * lip_height
    lip_rs = lip_r_bot + body_slope * lip_height * lip_t + extra * lip_t ** 3

    # --- Body ---
    body_ys = np.linspace(body_actual_top, body_actual_bot, 200)
    body_rs = np.array([body_width_at(y) / 2 for y in body_ys])

    # --- Base arc ---
    base_top_width = body_width_at(body_actual_bot)
    base_half_w = base_top_width / 2
    cap_height = (body_bot_y - body_actual_bot) * 1.4641  # +46.4% (4x 10%)
    R_base = (base_top_width**2 + 4 * cap_height**2) / (8 * cap_height)
    circle_cy = body_actual_bot + cap_height - R_base
    flat_y = body_actual_bot + cap_height * 0.70

    base_ys = np.linspace(body_actual_bot, flat_y, 100)
    base_rs = np.sqrt(np.maximum(R_base**2 - (base_ys - circle_cy)**2, 0))

    # Concatenate (skip duplicate junction points)
    all_ys = np.concatenate([lip_ys, body_ys[1:], base_ys[1:]])
    all_rs = np.concatenate([lip_rs, body_rs[1:], base_rs[1:]])

    return all_ys, all_rs, lip_rim_y, flat_y


# ============================================================
# Cup body mesh (hollow surface of revolution)
# ============================================================
def make_cup_body(ys_img, radii_px, flat_y, scale):
    """Build body as a single closed-loop revolution for watertight mesh.

    Profile loop: outer top → outer bottom → floor center → inner bottom → inner top → rim → close.
    Revolve this single closed loop around Y axis. Every edge shared by exactly 2 faces.
    """
    heights = (flat_y - ys_img) * scale  # Y-up, flat_y maps to Y=0
    radii_outer_m = radii_px * scale

    radii_inner = np.maximum(radii_px - WALL_THICKNESS, 0.5)
    radii_inner_m = radii_inner * scale

    # Floor: inner surface stops WALL_THICKNESS above outer bottom
    floor_height = heights[-1] + WALL_THICKNESS * scale
    inner_mask = heights >= floor_height
    if inner_mask.sum() < 2:
        inner_mask[:] = True
    n_inner = int(inner_mask.sum())

    # Build closed profile loop (radii and heights):
    # 1. Outer surface: top to bottom (indices 0..n_outer-1)
    # 2. Floor bottom center: radius=0 at outer bottom height (index n_outer)
    # 3. Floor top center: radius=0 at inner bottom height (index n_outer+1)
    # 4. Inner surface: bottom to top, reversed (indices n_outer+2..n_outer+1+n_inner)
    # The loop closes back to index 0 via the rim.

    n_outer = len(radii_outer_m)
    profile_r = np.concatenate([
        radii_outer_m,                          # outer: top to bottom
        [0.0],                                  # floor bottom center
        [0.0],                                  # floor top center
        radii_inner_m[:n_inner][::-1],          # inner: bottom to top
    ])
    profile_h = np.concatenate([
        heights,                                # outer: top to bottom
        [heights[-1]],                          # floor bottom center (outer bottom height)
        [floor_height],                         # floor top center (inner bottom height)
        heights[:n_inner][::-1],                # inner: bottom to top
    ])

    n_profile = len(profile_r)
    angles = np.linspace(0, 2 * np.pi, N_RADIAL, endpoint=False)

    # Generate vertices: for each profile point, create N_RADIAL vertices
    # Exception: center points (radius=0) get a single shared vertex
    verts = []
    vert_index = []  # maps (profile_idx, angle_idx) to vertex index

    for i in range(n_profile):
        if profile_r[i] < 1e-10:
            # Center point: single vertex shared by all angles
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

    # Generate faces: connect adjacent profile rings
    # The profile is a closed loop, so also connect last to first
    faces = []
    for i in range(n_profile):
        i_next = (i + 1) % n_profile
        for j in range(N_RADIAL):
            jn = (j + 1) % N_RADIAL
            v00 = vert_index[i][j]
            v01 = vert_index[i][jn]
            v10 = vert_index[i_next][j]
            v11 = vert_index[i_next][jn]
            # Skip degenerate faces (where 2+ vertices are the same)
            tri1 = [v00, v01, v10]
            tri2 = [v10, v01, v11]
            if len(set(tri1)) == 3:
                faces.append(tri1)
            if len(set(tri2)) == 3:
                faces.append(tri2)

    return np.array(verts), np.array(faces)


# ============================================================
# Handle tube mesh
# ============================================================
def make_handle(spine_2d, tube_half_w_px, flat_y, scale, mirror=False):
    if mirror:
        spine_2d = spine_2d.copy()
        spine_2d[:, 0] = 2 * body_cx - spine_2d[:, 0]
        spine_2d = spine_2d[::-1]
        tube_half_w_px = tube_half_w_px[::-1]

    n_pts = len(spine_2d)
    tube_r_arr = tube_half_w_px * scale  # per-point radius

    centers = np.zeros((n_pts, 3))
    for i in range(n_pts):
        x3 = (spine_2d[i, 0] - body_cx) * scale
        y3 = (flat_y - spine_2d[i, 1]) * scale
        centers[i] = [x3, y3, 0.0]

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
            offset = tube_r_arr[i] * (np.cos(tube_angles[j]) * N +
                               np.sin(tube_angles[j]) * B)
            verts.append(centers[i] + offset)

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
    global body_top_y
    print("=== Generating cup4.glb ===")

    print("Computing handle spine...")
    (spine_left, left_edge, right_edge, thw_clip,
     spine_full, thw_full, trim_start, trim_end) = compute_handle_spine()
    print(f"  Left handle spine: {len(spine_left)} points")

    # Find attachment points
    if spine_left[0, 1] < spine_left[-1, 1]:
        body_actual_top = min(left_edge[0, 1], right_edge[0, 1])
        # Extend body to 2/3 of total stroke width at lower attachment
        inner_y = min(left_edge[-1, 1], right_edge[-1, 1])
        outer_y = max(left_edge[-1, 1], right_edge[-1, 1])
        body_actual_bot = inner_y + 2/3 * (outer_y - inner_y)
    else:
        body_actual_top = min(left_edge[-1, 1], right_edge[-1, 1])
        # Extend body to 2/3 of total stroke width at lower attachment
        inner_y = min(left_edge[0, 1], right_edge[0, 1])
        outer_y = max(left_edge[0, 1], right_edge[0, 1])
        body_actual_bot = inner_y + 2/3 * (outer_y - inner_y)

    # Extend handle top so tube outer edge reaches body_actual_top
    if spine_left[0, 1] < spine_left[-1, 1]:
        while trim_start > 0 and spine_full[trim_start - 1, 1] >= body_actual_top - tube_w / 2:
            trim_start -= 1
    else:
        while trim_end + 1 < len(spine_full) and spine_full[trim_end + 1, 1] >= body_actual_top - tube_w / 2:
            trim_end += 1

    # Extend handle bottom so tube outer edge reaches body_actual_bot
    if spine_left[0, 1] < spine_left[-1, 1]:
        while trim_end + 1 < len(spine_full) and spine_full[trim_end + 1, 1] <= body_actual_bot + tube_w / 2:
            trim_end += 1
    else:
        while trim_start > 0 and spine_full[trim_start - 1, 1] <= body_actual_bot + tube_w / 2:
            trim_start -= 1
    spine_left = spine_full[trim_start:trim_end + 1]
    thw_clip = thw_full[trim_start:trim_end + 1]

    # Lower body_actual_top so lip stays 125px
    target_lip = 125.0
    body_actual_top = max(body_actual_top, body_top_y + target_lip / 0.726)

    # Make orange body 10% taller by extending upward
    orange_height = body_actual_bot - body_actual_top
    extra = 0.1 * orange_height
    body_actual_top -= extra
    body_top_y -= extra

    # Raise base of orange part by 5%
    body_actual_bot -= 0.03 * (body_actual_bot - body_actual_top)

    print(f"  Body range: {body_actual_top:.1f} to {body_actual_bot:.1f}")

    # Build outer profile
    print("Building outer profile (lip + body + base arc)...")
    ys_img, radii_px, lip_rim_y, flat_y = build_outer_profile(
        body_actual_top, body_actual_bot)

    # Scale: target ~20cm cup height
    total_height_px = flat_y - lip_rim_y
    SCALE = 0.20 / total_height_px
    print(f"  Total height: {total_height_px:.0f} px, SCALE={SCALE:.6f} m/px")
    print(f"  Cup height: {total_height_px * SCALE * 100:.1f} cm")
    print(f"  Lip rim radius: {radii_px[0] * SCALE * 100:.1f} cm")
    print(f"  Body bottom radius: {body_width_at(body_actual_bot)/2 * SCALE * 100:.1f} cm")

    # Build cup body mesh
    print("Building cup body mesh...")
    body_v, body_f = make_cup_body(ys_img, radii_px, flat_y, SCALE)
    body_mesh = trimesh.Trimesh(vertices=body_v, faces=body_f, process=False)

    # Build inner radius lookup for clipping handles
    # Use non-tapered inner radius so handles don't poke through near the base
    radii_inner_clip = np.maximum(radii_px - WALL_THICKNESS, 0.5)
    clip_margin = WALL_THICKNESS * 1.0 * SCALE  # outward margin to prevent interior protrusion
    heights_3d = (flat_y - ys_img) * SCALE
    radii_inner_clip_m = radii_inner_clip * SCALE

    def clip_handle_to_inner_wall(verts, faces):
        """Clamp handle vertices that penetrate the cup interior to the inner wall.
        Remove faces where all 3 vertices are inside (fully embedded in body)."""
        clipped = np.zeros(len(verts), dtype=bool)
        for i in range(len(verts)):
            x, y, z = verts[i]
            r = np.sqrt(x**2 + z**2)
            if r < 1e-10:
                continue
            if y <= heights_3d[-1] or y >= heights_3d[0]:
                continue
            r_inner = np.interp(y, heights_3d[::-1], radii_inner_clip_m[::-1]) + clip_margin
            if r < r_inner:
                verts[i, 0] = x / r * r_inner
                verts[i, 2] = z / r * r_inner
                clipped[i] = True
        n_clipped = int(clipped.sum())
        # Remove faces where all 3 vertices were clipped (fully inside body)
        keep = ~(clipped[faces[:, 0]] & clipped[faces[:, 1]] & clipped[faces[:, 2]])
        faces_out = faces[keep]
        n_removed = len(faces) - len(faces_out)

        # Cap boundary loops where interior faces were removed
        verts, faces_out = _cap_boundary_loops(verts, faces_out)

        return verts, faces_out, n_clipped, n_removed

    def _cap_boundary_loops(verts, faces):
        """Find boundary edge loops and fill them with triangle fans."""
        # Build edge counts
        edges = {}
        for f in faces:
            for i in range(3):
                e = tuple(sorted((f[i], f[(i+1) % 3])))
                edges[e] = edges.get(e, 0) + 1
        # Boundary edges appear in exactly one face
        boundary = [e for e, cnt in edges.items() if cnt == 1]
        if not boundary:
            return verts, faces

        # Build adjacency for boundary vertices
        adj = {}
        for a, b in boundary:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)

        # Walk loops
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

        # Fill each loop with a triangle fan
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

    # Build handles
    print("Building left handle tube...")
    lh_v, lh_f = make_handle(spine_left, thw_clip, flat_y, SCALE, mirror=False)
    lh_v, lh_f, n, nr = clip_handle_to_inner_wall(lh_v, lh_f)
    print(f"  Clipped {n} vertices, removed {nr} interior faces")
    lh_mesh = trimesh.Trimesh(vertices=lh_v, faces=lh_f, process=False)

    print("Building right handle tube...")
    rh_v, rh_f = make_handle(spine_left, thw_clip, flat_y, SCALE, mirror=True)
    rh_v, rh_f, n, nr = clip_handle_to_inner_wall(rh_v, rh_f)
    print(f"  Clipped {n} vertices, removed {nr} interior faces")
    rh_mesh = trimesh.Trimesh(vertices=rh_v, faces=rh_f, process=False)

    # Check sub-meshes
    print(f"  Body watertight={body_mesh.is_watertight}, euler={body_mesh.euler_number}")
    print(f"  LH watertight={lh_mesh.is_watertight}, euler={lh_mesh.euler_number}")
    print(f"  RH watertight={rh_mesh.is_watertight}, euler={rh_mesh.euler_number}")

    # Combine
    print("Combining meshes...")
    combined = trimesh.util.concatenate([body_mesh, lh_mesh, rh_mesh])
    # Normals are set by construction (known winding order)

    # Silver color
    color = [120, 120, 120, 255]
    combined.visual = trimesh.visual.ColorVisuals(
        mesh=combined,
        face_colors=np.tile(color, (len(combined.faces), 1))
    )

    # Bounding box
    bb_min = combined.vertices.min(axis=0)
    bb_max = combined.vertices.max(axis=0)
    bb_size = bb_max - bb_min
    print(f"Bounding box (cm): X={bb_size[0]*100:.1f} Y={bb_size[1]*100:.1f} Z={bb_size[2]*100:.1f}")

    # Export
    out_path = "/Users/user1/cup/cup4/cup4.glb"
    combined.export(out_path, file_type='glb')
    print(f"\nExported {out_path}")
    print(f"  Vertices: {len(combined.vertices)}")
    print(f"  Faces:    {len(combined.faces)}")

    # Export STL with Z-up orientation for 3D printing, scaled to 3.5in height
    stl_mesh = combined.copy()
    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    stl_mesh.apply_transform(rot)
    stl_mesh.vertices[:, 2] -= stl_mesh.vertices[:, 2].min()  # bottom at Z=0
    current_height = stl_mesh.vertices[:, 2].max()
    target_height = 3.5 * 0.0254  # 3.5 inches in meters
    scale_factor = target_height / current_height
    stl_mesh.apply_scale(scale_factor)
    stl_path = "/Users/user1/cup/cup4/cup4.stl"
    stl_mesh.export(stl_path)
    sz = stl_mesh.bounds[1] - stl_mesh.bounds[0]
    print(f"Exported {stl_path} (Z-up, height={sz[2]*100/2.54:.2f}in)")
    print(f"  Watertight: {stl_mesh.is_watertight}")
    if not stl_mesh.is_watertight:
        print(f"  WARNING: mesh is not watertight — may cause issues with slicers")

    print("Done!")


if __name__ == "__main__":
    main()
