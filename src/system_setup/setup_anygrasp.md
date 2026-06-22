# AnyGrasp SDK — Install & Troubleshooting Note

Learning note + Docker reference. Records how AnyGrasp was installed and tested
on the laptop, every problem hit, and the exact fix.

- **Date:** 2026-06-20
- **Machine:** Laptop — RTX 4060 (8 GB, Ada, `sm_89`), Ubuntu 22.04.5
- **Goal:** Test AnyGrasp standalone → later move into Isaac ROS docker → ROS2 manipulation
- **Repo:** https://github.com/graspnet/anygrasp_sdk
- **Result:** ✅ Works. Demo prints grasp scores, top grasp ≈ 0.476.

---

## 1. Final Working Versions

| Component | Version | Note |
|-----------|---------|------|
| conda env | `anygrasp`, python 3.10 | run isolated (see Problem 2) |
| cuda-toolkit | **12.6** (inside env) | matched to Isaac ROS docker nvcc |
| PyTorch | 2.6.0+cu126 | |
| torchvision | 0.21.0+cu126 | |
| MinkowskiEngine | 0.5.4 (chenxi-wang fork, `cuda-12-1` branch) | |
| pointnet2 | from SDK | |
| numpy | **1.23.5** | must be `<1.24` (see Problem 7) |
| conda gcc/g++ | 12.4.0 | env compiler, not system gcc 13.3 |
| openssl | 1.1.1w libs (side-loaded) | for licensed `.so` (see Problem 6) |

**Why CUDA 12.6:** the Isaac ROS docker already has `nvcc 12.6`. Matching the
laptop env to it means the same build steps work later in docker with no version
surprises.

---

## 2. conda vs venv — Decision

**Chose conda.** Reasons:

| Need | conda | venv |
|------|-------|------|
| `openblas-devel` (MinkowskiEngine needs it) | `conda install` easy | manual / apt, painful |
| Isolated CUDA **toolkit** (need own nvcc 12.6, not system 13.0) | `conda install cuda-toolkit=12.6` | cannot — venv uses system nvcc |
| Own C/C++ compiler (gcc 12.4, not system 13.3) | conda provides | uses system gcc |
| README itself | uses conda | — |

> venv only manages python packages. It cannot give a separate CUDA toolkit or
> compiler. MinkowskiEngine + pointnet2 compile CUDA kernels, so the toolkit
> version matters → conda wins.

System had CUDA **13.0** (too new — AnyGrasp wants 11.x/12.x). A fresh conda env
with its own CUDA 12.6 sidesteps the system version completely.

---

## 3. Install Steps (in order)

All build/run commands assume:

```bash
conda activate anygrasp
export PYTHONNOUSERSITE=1          # isolate from ~/.local (Problem 2)
export CUDA_HOME=$CONDA_PREFIX     # use env's nvcc 12.6
export MAX_JOBS=4                  # limit RAM during compile
export TORCH_CUDA_ARCH_LIST="8.9"  # RTX 4060 = Ada = sm_89
```

### Step 1 — Create env + CUDA toolkit + BLAS
```bash
conda create -y -n anygrasp python=3.10
conda activate anygrasp
conda install -y -c "nvidia/label/cuda-12.6.0" cuda-toolkit
conda install -y -c anaconda openblas-devel
```

### Step 2 — PyTorch (CUDA 12.6 build)
```bash
pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
```

### Step 3 — Clone repos
```bash
cd /home/mira/workspaces/anygrasp
git clone https://github.com/graspnet/anygrasp_sdk.git
git clone https://github.com/chenxi-wang/MinkowskiEngine.git
cd MinkowskiEngine && git checkout cuda-12-1
```

### Step 4 — Patch MinkowskiEngine (see Problems 3, 4, 5) then build
```bash
cd /home/mira/workspaces/anygrasp/MinkowskiEngine
python setup.py install \
  --blas_include_dirs=${CONDA_PREFIX}/include \
  --blas_library_dirs=${CONDA_PREFIX}/lib \
  --blas=openblas
```

### Step 5 — SDK python deps + pin numpy
```bash
cd /home/mira/workspaces/anygrasp/anygrasp_sdk
export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True   # Problem 8
pip install -r requirements.txt
pip install "numpy==1.23.5"                                    # Problem 7 — keep last
```

### Step 6 — Build pointnet2
```bash
cd /home/mira/workspaces/anygrasp/anygrasp_sdk/pointnet2
python setup.py install
```

### Step 7 — Licensed binaries + license + checkpoint
```bash
cd /home/mira/workspaces/anygrasp/anygrasp_sdk/grasp_detection
# match python 3.10 .so
cp gsnet_versions/gsnet.cpython-310-x86_64-linux-gnu.so gsnet.so
cp ../license_registration/lib_cxx_versions/lib_cxx.cpython-310-x86_64-linux-gnu.so lib_cxx.so
# license folder
mkdir -p license && unzip -o /home/mira/workspaces/anygrasp/license_BachalaRajesh.zip -d license
# model weights
mkdir -p log && cp /home/mira/workspaces/anygrasp/checkpoint_detection.tar log/
```

### Step 8 — Run demo
```bash
export LD_LIBRARY_PATH=/home/mira/workspaces/anygrasp/openssl11_libs:$LD_LIBRARY_PATH  # Problem 6
cd /home/mira/workspaces/anygrasp/anygrasp_sdk/grasp_detection
python demo.py --checkpoint_path log/checkpoint_detection.tar --top_down_grasp
```

| Flag | Effect |
|------|--------|
| `--top_down_grasp` | only top-down grasps |
| (omit it) | all-angle 6-DOF grasps |
| `--debug` | open Open3D window with grippers (needs display) |

---

## 4. Problems Faced & Fixes

### Problem 1 — System CUDA 13.0 too new
- **Symptom:** README supports CUDA 11.x/12.x; system `nvcc` was 13.0.
- **Why:** MinkowskiEngine 0.5.4 (from 2021) cannot compile against CUDA 13.
- **Fix:** install CUDA **12.6** *inside* the conda env. The env's nvcc is used
  via `CUDA_HOME=$CONDA_PREFIX`, ignoring system CUDA.

### Problem 2 — Env leaked `~/.local` user packages
- **Symptom:** fresh env still saw `torch 2.12`, `isaaclab`, `numpy 2.x`.
- **Why:** Python reads `~/.local/lib/python3.10/site-packages` (user site) even>
  inside a conda env.
- **Fix:** always set `export PYTHONNOUSERSITE=1`. This also forced the env to be
  **fully self-contained** (had to install torch's deps explicitly — Problem 9),
  which is exactly what we want for docker.

### Problem 3 — MinkowskiEngine nvtx3 header clash
- **Symptom:** hundreds of errors in
  `src/3rdparty/cudf/detail/nvtx/nvtx3.hpp` — e.g.
  `identifier "nvtxColorType_t" is undefined`, `"_domain" is not a member`.
- **Why:** ME ships an **old** single-file `nvtx3.hpp` that does not match
  CUDA 12.6's NVTX headers.
- **Fix:** replace the bundled nvtx headers with the **modern** nvtx3 tree.
  Source used (already in env, ships with nsight):
  ```
  SRC=$CONDA_PREFIX/nsight-compute-2024.3.0/host/target-linux-x64/nvtx/include/nvtx3
  DST=/home/mira/workspaces/anygrasp/MinkowskiEngine/src/3rdparty/cudf/detail/nvtx
  mv $DST/nvtx3.hpp $DST/nvtx3.hpp.old
  cp -r $SRC/nvtx3.hpp $SRC/nvToolsExt*.h $SRC/nvtxDetail $DST/
  ```

### Problem 4 — `domain_thread_range` removed in modern nvtx3
- **Symptom:** after Problem 3 fix:
  `namespace "nvtx3" has no member "domain_thread_range"` in `ranges.hpp`.
- **Why:** modern nvtx3 API renamed/removed that type. `ranges.hpp` is only used
  for NVTX **profiling** (`CUDF_FUNC_RANGE()` macro), used in exactly one place.
- **Fix:** stub `ranges.hpp` — drop the nvtx dependency, make the macro a no-op:
  ```cpp
  #pragma once
  namespace cudf {
  struct libcudf_domain { static constexpr char const* name{"libcudf"}; };
  }  // namespace cudf
  #define CUDF_FUNC_RANGE()
  ```
  (file: `.../cudf/detail/nvtx/ranges.hpp`). NVTX is profiling only — no effect
  on functionality. Build also auto-defines `-DNVTX_DISABLE`.

### Problem 5 — `std::__to_address` ambiguous (conda gcc 12.4)
- **Symptom:**
  `more than one instance of overloaded function "std::__to_address" matches`
  and `no instance of ... _M_enable_shared_from_this_with matches`, both at
  `.../gcc/.../12.4.0/include/c++/bits/shared_ptr_base.h:1561` and `:1563`.
- **Why:** both `cuda::std::__to_address` and `std::__to_address` are visible,
  so the unqualified call is ambiguous. This is the exact issue the SDK README's
  `sed` hack fixes — but for the **conda** gcc header, not `/usr/include`.
- **Fix:** qualify the call in the conda libstdc++ header (lines 1561 & 1577):
  ```bash
  H=$CONDA_PREFIX/lib/gcc/x86_64-conda-linux-gnu/12.4.0/include/c++/bits/shared_ptr_base.h
  cp $H ${H}.bak
  sed -i 's/auto __raw = __to_address(__r.get());/auto __raw = std::__to_address(__r.get());/' $H
  ```
  > Note: this edits a toolchain header. Must be redone in docker (same sed on
  > that env's gcc header). Keep the `.bak`.

### Problem 6 — Licensed `.so` need OpenSSL 1.1
- **Symptom:** `ImportError: libcrypto.so.1.1: cannot open shared object file`.
- **Why:** `gsnet.so` / `lib_cxx.so` (FlexivLic license check) link OpenSSL
  **1.1**; Ubuntu 22.04 ships OpenSSL 3.
- **Fix:** do NOT downgrade env openssl (breaks python). Side-load 1.1 libs:
  ```bash
  conda create -y -p /tmp/ossl11 --no-deps -c conda-forge "openssl=1.1.1w"
  mkdir -p /home/mira/workspaces/anygrasp/openssl11_libs
  cp /tmp/ossl11/lib/libcrypto.so.1.1 /tmp/ossl11/lib/libssl.so.1.1 \
     /home/mira/workspaces/anygrasp/openssl11_libs/
  # at runtime:
  export LD_LIBRARY_PATH=/home/mira/workspaces/anygrasp/openssl11_libs:$LD_LIBRARY_PATH
  ```

### Problem 7 — `np.float` removed (check again)
- **Symptom:** `AttributeError: module 'numpy' has no attribute 'float'`,
  raised from inside `gsnet.so` after license check.
- **Why:** `np.float` was removed in numpy 1.24. The licensed binary uses it.
  Cannot edit the `.so`.
- **Fix:** `pip install "numpy==1.23.5"` (any `<1.24`). Verified ME + pointnet2
  still import fine at runtime with numpy 1.23.5 (no ABI break).
  Install numpy **last** — other packages try to pull newer numpy.

### Problem 8 — `graspnetAPI` pulls deprecated `sklearn`
- **Symptom:** `requirements.txt` install fails building `sklearn` (the dummy
  shim package errors on purpose now).
- **Fix:** `export SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True` before
  `pip install -r requirements.txt`. Real `scikit-learn` installs alongside.

### Problem 9 — missing torch deps under isolation
- **Symptom:** with `PYTHONNOUSERSITE=1`, `import torch` failed
  (`No module named typing_extensions`, later `mpmath`).
- **Why:** those deps were satisfied from `~/.local` before; isolation removed
  them.
- **Fix:** install them into the env:
  `pip install typing_extensions filelock networkx jinja2 fsspec pillow mpmath`.

### Harmless warnings (ignore)
- `isaaclab requires ... incompatible` — those are `~/.local` packages; we run
  isolated, so irrelevant.
- `Failed to import ros dependencies in rigid_transforms.py` /
  `autolab_core not installed as catkin package` — optional ROS bits in
  graspnetAPI, not needed for the demo.
- `OMP_NUM_THREADS not set` — set `export OMP_NUM_THREADS=8` to silence.

---

## 5. Verified Output

```
[FlexivLic] license ... check passed.
license passed: True, state: FvrLicenseState.PASSED
grasp score: 0.4764862060546875   # top of 20 ranked grasps
```

---

## 6. Docker Notes (Isaac ROS docker — has nvcc 12.6)

The docker already has CUDA 12.6, so skip the in-env CUDA toolkit. Order of
layers (adapt to the docker's base image / compiler):

```dockerfile
# --- assumes base image already has CUDA 12.6 toolkit + nvcc ---
ENV CUDA_HOME=/usr/local/cuda
ENV TORCH_CUDA_ARCH_LIST="8.9"
ENV MAX_JOBS=4

# 1. python deps
RUN pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
RUN apt-get update && apt-get install -y libopenblas-dev   # or conda openblas-devel

# 2. clone + patch + build MinkowskiEngine
RUN git clone https://github.com/chenxi-wang/MinkowskiEngine.git /opt/MinkowskiEngine && \
    cd /opt/MinkowskiEngine && git checkout cuda-12-1
#   PATCH Problem 3: swap nvtx3 headers (find docker's modern nvtx3 tree)
#   PATCH Problem 4: stub ranges.hpp -> CUDF_FUNC_RANGE() no-op
#   PATCH Problem 5: sed std::__to_address in docker's gcc shared_ptr_base.h
RUN cd /opt/MinkowskiEngine && python setup.py install \
    --blas_include_dirs=/usr/include --blas_library_dirs=/usr/lib/x86_64-linux-gnu --blas=openblas

# 3. SDK
RUN git clone https://github.com/graspnet/anygrasp_sdk.git /opt/anygrasp_sdk
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True
RUN pip install -r /opt/anygrasp_sdk/requirements.txt && pip install "numpy==1.23.5"
RUN cd /opt/anygrasp_sdk/pointnet2 && python setup.py install

# 4. OpenSSL 1.1 for licensed .so (Problem 6) — install libssl1.1 or copy .so.1.1
#    e.g. add libcrypto.so.1.1 / libssl.so.1.1 to /opt/openssl11 and:
ENV LD_LIBRARY_PATH=/opt/openssl11:${LD_LIBRARY_PATH}

# 5. at runtime: copy gsnet/lib_cxx .so for the docker's python version,
#    license/, log/checkpoint_detection.tar  (license is per-machine — re-register
#    the feature ID for the docker/host if it changes)
```

### Docker gotchas to watch
| Item | Watch for |
|------|-----------|
| python version | `.so` must match docker's python (`cpython-3XX`) |
| license feature ID | tied to machine/container — may need re-register |
| compiler header patch (Prob 5) | redo sed on the docker's gcc header path |
| nvtx headers (Prob 3) | locate the docker's modern nvtx3 tree |
| GPU arch | keep `TORCH_CUDA_ARCH_LIST="8.9"` for RTX 4060 |

---

## 7. Key Paths

| What | Path |
|------|------|
| SDK | `/home/mira/workspaces/anygrasp/anygrasp_sdk` |
| MinkowskiEngine | `/home/mira/workspaces/anygrasp/MinkowskiEngine` |
| OpenSSL 1.1 libs | `/home/mira/workspaces/anygrasp/openssl11_libs` |
| checkpoint / license (source) | `/home/mira/workspaces/anygrasp/` |
| demo | `anygrasp_sdk/grasp_detection/demo.py` |

---

## 8. Docker — What Actually Happened (2026-06-22)

Built AnyGrasp **into** the Isaac ROS docker (`Dockerfile.robotics_layer2`), then
ran the demo inside the container. The build was easy. The **license** was the
hard part. This section records the surprises so future-me does not re-debug.

### 8.1 The image was different from the laptop note

The `robotics_layer2` image **already had** its own ML stack, so several Section 1
assumptions were **stale**:

| Thing | Laptop note said | Docker image actually had | What we did |
|-------|------------------|---------------------------|-------------|
| PyTorch | 2.6.0+cu126 | **2.9.1+cu128** | kept docker's torch — AnyGrasp built fine against it |
| numpy | must be **1.23.5** (Problem 7) | **2.2.6** | kept 2.2.6 — **Problem 7 is stale**, see 8.2 |
| python | 3.10 | 3.10.12 | `gsnet.cpython-310` .so works |
| nvcc | 12.6 (in conda) | 12.6 (system) | no conda toolkit needed |
| env | conda env | **system python** | no venv, no conda — installed straight in |
| gcc header (Prob 5) | conda path | `/usr/include/c++/12/bits/shared_ptr_base.h` | same sed, system path |
| BLAS | conda openblas-devel | apt `libopenblas-dev` | headers in `/usr/include/x86_64-linux-gnu/openblas-pthread` |

> **Key lesson:** no separate env was needed. numpy 2.2.6 + torch 2.9.1 ran the
> licensed `.so` with no trouble. The whole "isolate / pin old versions" worry
> from the laptop note did not apply.

### 8.2 Problem 7 (np.float) was a false alarm

The laptop's own working `anygrasp` env actually had **numpy 2.2.6**, not 1.23.5,
and the demo still printed `grasp score: 0.476`. So `gsnet.so` does **not** crash
on numpy ≥ 1.24. The `np.float` note is obsolete — do not pin numpy down.

### 8.3 Patches in docker (simpler than the note)

- **Problems 3 + 4 → ONE patch.** The bundled `nvtx3.hpp` is only pulled in by
  `ranges.hpp`. Instead of swapping in a modern nvtx tree (Problem 3) and then
  stubbing (Problem 4), just stub `ranges.hpp` directly — drop the
  `#include "nvtx3.hpp"`, delete the `domain_thread_range` typedef, no-op
  `CUDF_FUNC_RANGE()`. That kills both at once. (Docker has no `nvtx3.hpp` to copy
  anyway — its `nvtx3/` tree only has the C headers.)
- **Problem 5** identical, just the system gcc header path.
- **Problem 6** (OpenSSL 1.1) identical; in docker we pull focal's `libssl1.1`
  `.deb` into `/opt/openssl11` instead of conda.

### 8.4 Problem 10 — License "feature id doesn't match the hardware" ★ the big one

- **Symptom:** demo build worked perfectly, but the license check failed:
  ```
  [FlexivLic] feature id doesn't match the hardware.
  license passed: False
  ```
  Container feature id = `13161796167236013604`, but the laptop license is for
  `10752581772502770378`.

- **What it is NOT** (ruled out one by one):
  - NOT the network MAC list — identical (`run_dev.sh` uses `--network host`).
  - NOT `/etc/machine-id` — set it to match, no change.
  - NOT `/var/lib/dbus/machine-id` — set it to match, no change.
  - NOT the binaries — `gsnet.so` / `lib_cxx.so` / `license_checker` md5 identical.
  - NOT product_uuid / board_serial / hostname — all identical.

- **Root cause (found via `strace -f -e execve` on `license_checker`):**
  the feature id is the **wired NIC MAC**. The checker shells out to:
  ```
  ifconfig | grep flags | ... | grep -vE 'docker|br-|veth' | xargs -n1 ifconfig | grep ether
  ... | xargs -n1 iwconfig    # <-- used to drop the WIRELESS card
  ```
  It uses **`iwconfig`** to identify and skip the wifi card. The container had
  `net-tools` (ifconfig) but **not `wireless-tools` (iwconfig)**. Without it the
  wireless filter silently failed → it picked the **wrong** card → wrong feature
  id → license rejected. On bare metal `iwconfig` exists, so the laptop picked the
  right (wired) card and got the matching id.

- **Fix:**
  ```bash
  apt-get install -y wireless-tools
  ```
  After this the container computes `10752581772502770378` — the **same** id as
  the laptop — and the **existing** license validates as-is. No re-registration,
  no MAC pinning, one license for both machines.

- **Why one license works for both:** `run_dev.sh` runs the container with
  `--network host`, so the container sees the host's real NICs. With
  `net-tools` + `wireless-tools` present, the id is computed exactly like bare
  metal → laptop license matches.

### 8.4b Problem 11 — MinkowskiEngine compiled CPU_ONLY in `docker build`

- **Symptom (runtime):**
  ```
  AssertionError: The MinkowskiEngine was compiled with CPU_ONLY flag.
  ```
- **Why:** ME's `setup.py` decides CPU vs CUDA from `torch.cuda.is_available()`
  **at build time**. `docker build` has **no GPU** (the GPU is only attached at
  `docker run` via `--gpus`), so it silently built CPU-only. (It worked in the
  earlier *live* test because that built ME **inside** the running, GPU-attached
  container.)
- **Fix:** add **`--force_cuda`** to the ME build. It compiles CUDA kernels with
  `nvcc` (no live GPU needed) and sets `CPU_ONLY=False`:
  ```dockerfile
  python3 setup.py install --force_cuda --blas_include_dirs=... --blas=openblas
  ```

### 8.4c Problem 12 — `transforms3d` 0.3.1 uses removed `np.maximum_sctype`

- **Symptom (right after license passes):**
  ```
  AttributeError: `np.maximum_sctype` was removed in the NumPy 2.0 release.
  ```
- **Why:** `graspnetAPI` (from `requirements.txt`) pulls **transforms3d 0.3.1**,
  which calls `np.maximum_sctype` at import — gone in numpy 2.0. The laptop had
  **0.4.2** (which fixed this), so it never hit the error.
- **Fix:** `pip install "transforms3d==0.4.2"` (added as the last docker layer).

### 8.4d Problem 13 — `./.TimeRecord` write fails (root-owned dir)

- **Symptom:** license key/signature pass, then:
  ```
  Unable to create file ./.TimeRecord
  [FlexivLic] check time record failed!  -> license passed: False
  ```
- **Why:** FlexivLic writes an anti-tamper file `.TimeRecord` in the **current
  dir** at runtime. `/opt/anygrasp_sdk/grasp_detection` is root-owned (built as
  root); the container runs as `admin` and cannot write there.
- **Fix:** make the run dir writable — `chmod -R a+w
  /opt/anygrasp_sdk/grasp_detection` (or `chown` to the runtime user).

### 8.5 Final docker layer order (in `Dockerfile.robotics_layer2`)

1. apt: `libopenblas-dev`, `net-tools`, `wireless-tools` (Prob 10).
2. sed `std::__to_address` in `/usr/include/c++/12/bits/shared_ptr_base.h` (Prob 5).
3. clone ME `cuda-12-1`, stub `ranges.hpp` (Prob 3+4), build with
   **`--force_cuda`** + openblas-pthread (Prob 11).
4. clone SDK, `pip install -r requirements.txt` with `SKLEARN_ALLOW...=True` (Prob 8).
   **No numpy pin.**
5. build SDK `pointnet2`.
6. copy `gsnet.cpython-310` / `lib_cxx.cpython-310` `.so` from the repo.
7. side-load OpenSSL 1.1 → `/opt/openssl11` (Prob 6).
8. `ENV LD_LIBRARY_PATH=/opt/openssl11:...`, `ENV OMP_NUM_THREADS=8`.
9. (last layer) `pip install transforms3d==0.4.2` (Prob 12) — kept last for cache.

**Runtime (not baked):** mount the unzipped `license/` folder and
`checkpoint_detection.tar` into `/opt/anygrasp_sdk/grasp_detection/`, and make
that dir writable for `.TimeRecord` (Prob 13).

### 8.6 Verified output in docker

```
license passed: True, state: FvrLicenseState.PASSED
grasp score: 0.4764862060546875
```
Same as bare metal. ✅
