# Table / Plane Removal in Point Clouds

Notes on every method for removing a table (a flat plane) from a point cloud,
so only the objects remain. Covers what we already used in this project and
other good options. Context: OAK-D depth → Open3D → AnyGrasp.

---

## Why remove the table?

AnyGrasp will try to grasp **any** surface, including the flat table. We must
delete the table points so grasps land only on objects.

---

## Quick map

| # | Method | We used? | Best when |
|---|--------|----------|-----------|
| 1 | Crop / passthrough box | ✅ yes | always — first rough cut |
| 2 | Single RANSAC plane | ✅ yes (file `2`) | clean, thin, single plane |
| 3 | Iterative RANSAC | ✅ yes (file `2.1`) | thick table, multiple flat surfaces |
| 4 | Height filter above plane | ✅ yes (files `2.2`, `2.3`) | **best simple choice**; noisy/thick table |
| 5 | Normal-constrained RANSAC | ⬜ suggested | walls/background planes confuse plain RANSAC |
| 6 | Normal + region growing | ⬜ suggested | want clean segmentation, no threshold guess |
| 7 | CSF (cloth simulation filter) | ⬜ suggested | uneven ground / outdoor / LiDAR-style |
| 8 | DBSCAN / Euclidean clustering | ✅ yes (file `2.4`) | separate objects + drop noise specks (after removal) |
| 9 | Organized plane segmentation | ⬜ suggested | need real-time; have an organized cloud (PCL) |

---

## 1. Crop / passthrough box

**Idea:** keep only points inside a 3D box (x,y,z min/max).

**How:** numpy mask on the coordinates.
```python
mask = (x>=X_MIN)&(x<=X_MAX)&(y>=Y_MIN)&(y<=Y_MAX)&(z>=Z_MIN)&(z<=Z_MAX)
```

| Merit | Demerit |
|-------|---------|
| trivial, very fast | does not remove the table inside the box |
| removes walls/floor/far junk | needs box tuned to the scene |

Use it **first**, always. It does not remove the table by itself.

---

## 2. Single RANSAC plane

**Idea:** fit the one biggest flat plane (the table), delete those points.

**How (Open3D):**
```python
plane, inliers = pcd.segment_plane(distance_threshold=0.01, ransac_n=3,
                                   num_iterations=1000)
pcd = pcd.select_by_index(inliers, invert=True)   # keep NON-plane
```

| Merit | Demerit |
|-------|---------|
| one line, fast | leaves crumbs if table is thick/noisy |
| auto-finds the plane | `distance_threshold` hard to tune |
|  | may delete a wall instead of the table |

---

## 3. Iterative RANSAC

**Idea:** one pass removes only the single biggest plane. Repeat a few times to
strip thick or multi-level tables.

**How:** loop `segment_plane` → remove inliers → repeat. Stop if a plane is too
small (probably an object, not a table).
```python
for i in range(MAX_PLANES):
    plane, inliers = rest.segment_plane(0.01, 3, 1000)
    if len(inliers) < MIN_PLANE_POINTS:
        break
    rest = rest.select_by_index(inliers, invert=True)
```

| Merit | Demerit |
|-------|---------|
| handles thick / layered tables | can eat objects if it runs too many passes |
| simple extension of method 2 | still threshold-based |

> In this project, iterative did not fully clean the layered table (depth
> banding made each "layer" its own plane). Height filter worked better.

---

## 4. Height filter above the plane (BEST simple choice)

**Idea:** fit the table plane **once**, then KEEP only points that rise above it
by more than `H`. Table thickness no longer matters — every table point sits at
height ≈ 0 and is dropped.

**How:**
```python
plane, inliers = pcd.segment_plane(0.01, 3, 1000)
a, b, c, d = plane                       # (a,b,c) = unit normal
pts = np.asarray(pcd.points)
height = pts @ np.array([a, b, c]) + d   # signed distance to plane
side = 1.0 if d >= 0 else -1.0           # object side = camera side = sign(d)
keep = (height * side) > H               # H = min object height, e.g. 0.01 m
objects = pcd.select_by_index(np.where(keep)[0])
```

**Why it beats deleting plane points:** thick/noisy/banded table is all near
height 0 → all dropped in one shot. Objects clearly stand above → kept.

| Merit | Demerit |
|-------|---------|
| robust to table thickness + depth banding | short objects (< H) get dropped |
| one knob (`H`) with clear meaning | needs a good single plane fit |
| sharp object base (esp. before voxel) |  |

---

## 5. Normal-constrained RANSAC

**Idea:** same as RANSAC, but accept the plane only if its normal points "up"
(roughly vertical). Stops it deleting a wall.

**How:** Open3D `segment_plane` has no built-in normal constraint, so check the
returned normal yourself, or loop and skip non-horizontal planes:
```python
a, b, c, d = plane
up = np.array([0, -1, 0])                # camera up direction (y is down)
if abs(np.dot([a, b, c], up)) > 0.9:     # plane normal ~ vertical -> table
    pcd = pcd.select_by_index(inliers, invert=True)
```

| Merit | Demerit |
|-------|---------|
| never deletes walls / background | need to know the up direction |
| good with cluttered scenes | extra check code |

---

## 6. Normal estimation + region growing

**Idea:** compute each point's surface normal. The table is one big region of
points whose normals all point the same way. Grow that region and remove it.

**How:** `pcd.estimate_normals(...)`, then region-growing segmentation (Open3D
has clustering; PCL has `RegionGrowing`). Table = largest smooth region.

| Merit | Demerit |
|-------|---------|
| clean segmentation, no distance threshold | slower (normals + growing) |
| handles gently curved tables | more parameters |

---

## 7. CSF — Cloth Simulation Filter

**Idea:** flip the cloud upside down, drop a virtual "cloth" on it. The cloth
settles on the lowest surface = the ground/table. Points near the cloth = table.

**How:** library `cloth-simulation-filter` (`pip install cloth-simulation-filter`).
Common in LiDAR ground filtering.

| Merit | Demerit |
|-------|---------|
| very robust for uneven ground | heavier, extra dependency |
| no plane assumption | tuned for large outdoor scans |

---

## 8. DBSCAN / Euclidean clustering

**Idea:** NOT a primary table remover. Run it **after** table removal to group
leftover points into separate objects and drop tiny noise specks.

**How (Open3D):**
```python
labels = np.array(pcd.cluster_dbscan(eps=0.02, min_points=10))
# label -1 = noise; keep clusters big enough
```

| Merit | Demerit |
|-------|---------|
| separates touching objects | needs `eps` tuned to point spacing |
| drops floating noise specks | merges objects that touch |

Best combo: **height filter → DBSCAN** (file `2.4`).

---

## 9. Organized plane segmentation (PCL)

**Idea:** if the cloud is "organized" (still a 2D image grid, neighbors known),
plane finding is much faster using the grid structure.

**How:** PCL `OrganizedMultiPlaneSegmentation`. Not in Open3D.

| Merit | Demerit |
|-------|---------|
| real-time fast | needs organized cloud + PCL |
| finds multiple planes at once | C++ / pcl-python setup |

---

## Side note — why a flat table shows several layers

The table looks like stacked sheets because stereo **depth is quantized**:
```
Z = fx * baseline / disparity
```
- Without **subpixel**, disparity is integer → depth has discrete steps.
- We turned subpixel OFF because **extended disparity** (for close objects)
  cannot run with subpixel at the same time.
- Step size grows with distance:  `ΔZ ≈ Z² / (fx · baseline)` per disparity step.
- So a far, flat table snaps to a few depth values → visible bands.
- Random stereo noise adds extra thickness on top.

Fixes: enable subpixel (loses close range), or temporal/spatial depth filters,
or just rely on the height filter, which tolerates the thickness.

---

## Recommendation for this project

```
crop box  →  height filter (remove table)  →  DBSCAN (split objects, drop specks)
```
- crop = rough cut
- height filter = robust table removal (handles banding)
- DBSCAN = clean separated objects for AnyGrasp

Do table removal BEFORE voxel downsample (sharper object base). Once the cloud
is small (objects only), voxel is usually unnecessary and only loses detail.
