# GraspNet-Baseline Setup Guide

Tested on:
- Ubuntu 22.04
- Python 3.10.12
- PyTorch 2.12.0+cu130
- CUDA 13.0
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU (sm_89)

---

## Repo

Use the patched fork — it has fixed C++ extensions for PyTorch 2.x:

```
https://github.com/yzxoi/gemini2-eye-to-hand-grasp
```

The `pointnet2` and `knn` extensions live under `graspnet-baseline/` subfolder.

---

## Step 1 — Clone repo

```bash
git clone https://github.com/yzxoi/gemini2-eye-to-hand-grasp.git ~/temp/gemini2-eye-to-hand-grasp
cd ~/temp/gemini2-eye-to-hand-grasp/graspnet-baseline
```

---

## Step 2 — Create venv

Use `--system-site-packages` to inherit PyTorch already installed at user level.
Do NOT use conda — it conflicts with system CUDA.

```bash
python3 -m venv ~/envs/graspnet --system-site-packages
source ~/envs/graspnet/bin/activate
```

Verify PyTorch inherited:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
# Expected: 2.12.0+cu130 / True
```

---

## Step 3 — Install Python dependencies

```bash
pip install open3d scipy scikit-learn trimesh transforms3d cvxopt matplotlib Pillow
```

Ignore isaaclab conflict warnings — not relevant here.

---

## Step 4 — Install graspnetAPI

```bash
cd graspnetAPI
pip install .
cd ..
```

Note: The `sklearn` → `scikit-learn` rename fix in `setup.py` was not needed for this version (already clean).

---

## Step 5 — Compile CUDA extensions

Find `cusparse.h` first:

```bash
find ~/.local -name "cusparse.h" 2>/dev/null | head -1
# Expected: ~/.local/lib/python3.10/site-packages/nvidia/cu13/include/cusparse.h
```

Then compile:

```bash
export CUDA_HOME=/usr/local/cuda-13.0
export PATH=$CUDA_HOME/bin:$PATH
export TORCH_CUDA_ARCH_LIST="8.9"
export CPATH=$HOME/.local/lib/python3.10/site-packages/nvidia/cu13/include

cd pointnet2
python setup.py install
cd ..

cd knn
python setup.py install
cd ..
```

---

## Step 6 — Fix: .so files trapped inside egg zips

### Problem
After `setup.py install`, both `pointnet2` and `knn_pytorch` were packaged as `.egg` zip files.
Python can import pure Python from zips but **cannot load `.so` shared libraries from inside a zip**.
Import fails with `ModuleNotFoundError: No module named 'pointnet2._ext'`.

### Fix
Extract both eggs so the `.so` files land directly in `site-packages`:

```bash
cd ~/envs/graspnet/lib/python3.10/site-packages/

python3 -c "import zipfile; zipfile.ZipFile('pointnet2-0.0.0-py3.10-linux-x86_64.egg').extractall('.')"
python3 -c "import zipfile; zipfile.ZipFile('knn_pytorch-0.1-py3.10-linux-x86_64.egg').extractall('.')"
```

### Verify

```bash
cd ~/temp/gemini2-eye-to-hand-grasp/graspnet-baseline
python -c "
import sys
sys.path += ['models','dataset','utils','pointnet2','knn']
import torch
import pointnet2._ext
print('Extensions OK')
print('CUDA:', torch.cuda.is_available())
print('GPU:', torch.cuda.get_device_name(0))
"
```

---

## Step 7 — Download checkpoint

```bash
source ~/envs/graspnet/bin/activate
pip install gdown
gdown "1hd0G8LN6tRpi4742XOTEisbTXNZ-1jmk" -O ~/temp/gemini2-eye-to-hand-grasp/graspnet-baseline/checkpoint-rs.tar
```

`checkpoint-rs.tar` = RealSense model (~12 MB). Baidu Pan alternative:
`https://pan.baidu.com/s/1Eme60l39tTZrilF0I86R5A`

---

## Step 8 — Apply source patches

### Patch 1 — torch.load weights_only (PyTorch >= 2.6)

File: `demo.py` line 43

```python
# Before
checkpoint = torch.load(cfgs.checkpoint_path)

# After
checkpoint = torch.load(cfgs.checkpoint_path, weights_only=False)
```

---

### Patch 2 — autolab_core missing

Error: `ModuleNotFoundError: No module named 'autolab_core'`

Fix:

```bash
pip install autolab_core
```

---

### Patch 3 — mpl_toolkits system/user conflict

Error:
```
ImportError: cannot import name 'docstring' from 'matplotlib'
  File "/usr/lib/python3/dist-packages/mpl_toolkits/mplot3d/axes3d.py"
```

Cause: system `mpl_toolkits` (old) loads instead of the installed matplotlib's version.
`mpl_toolkits` is a namespace package — Python merges both system and user versions,
and the system one tries to import `docstring` which was removed in matplotlib 3.4+.

**Fix A** — force reinstall matplotlib into venv (so its mpl_toolkits takes priority):

```bash
pip install matplotlib --force-reinstall
```

**Fix B** — patch the offending import in graspnetAPI (still needed even after Fix A):

File: `~/envs/graspnet/lib/python3.10/site-packages/graspnetAPI/utils/dexnet/grasping/quality.py` line 54

```python
# Before
from mpl_toolkits.mplot3d import Axes3D

# After
try:
    from mpl_toolkits.mplot3d import Axes3D
except ImportError:
    Axes3D = None
```

---

### Patch 4 — torch._six removed (PyTorch >= 1.9)

Error: `ModuleNotFoundError: No module named 'torch._six'`

File: `dataset/graspnet_dataset.py` line 12

```python
# Before
from torch._six import container_abcs

# After
import collections.abc as container_abcs
```

---

### Patch 5 — grasp_nms extension missing

Error: `ModuleNotFoundError: No module named 'grasp_nms'`

`grasp_nms` is a C extension referenced in graspnetAPI but not compiled in this repo.
It is only used in `gg.nms()` inside `vis_grasps()` — safe to skip for demo.

File: `demo.py`

```python
def vis_grasps(gg, cloud):
    # gg.nms()  # skipped: grasp_nms C extension not available
    gg.sort_by_score()
    gg = gg[:50]
    grippers = gg.to_open3d_geometry_list()
    o3d.visualization.draw_geometries([cloud, *grippers])
```

---

## Step 9 — Run demo

```bash
cd ~/temp/gemini2-eye-to-hand-grasp/graspnet-baseline
source ~/envs/graspnet/bin/activate
python demo.py --checkpoint_path checkpoint-rs.tar
```

Success output:
```
-> loaded checkpoint checkpoint-rs.tar (epoch: 18)
```

Open3D window opens showing point cloud with green gripper frames.

If running over SSH with no display:
```bash
DISPLAY=:0 python demo.py --checkpoint_path checkpoint-rs.tar
```

---

## Summary of all patches

| # | File | Problem | Fix |
|---|------|---------|-----|
| 1 | venv site-packages | `.so` inside egg zip | Extract egg zips manually |
| 2 | `demo.py` | `torch.load` weights_only error | Add `weights_only=False` |
| 3 | pip | `autolab_core` missing | `pip install autolab_core` |
| 4 | `graspnetAPI/utils/dexnet/grasping/quality.py` | `mpl_toolkits` system conflict | `try/except` around `Axes3D` import + `pip install matplotlib --force-reinstall` |
| 5 | `dataset/graspnet_dataset.py` | `torch._six` removed | Replace with `collections.abc` |
| 6 | `demo.py` | `grasp_nms` extension missing | Skip `gg.nms()` call |
