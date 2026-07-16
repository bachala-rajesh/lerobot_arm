# Using the AnyGrasp Model — Laptop

What must be true for AnyGrasp to run on the laptop.
Wrapper class: `src/segment_grasppose/segment_grasppose/anygrasp_model.py`

---

## Quick run (copy-paste)

```bash
conda activate anygrasp
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH=/home/mira/workspaces/anygrasp/openssl11_libs:$LD_LIBRARY_PATH
export OMP_NUM_THREADS=8

cd src/segment_grasppose/segment_grasppose
python3 anygrasp_model.py           # print only
python3 anygrasp_model.py --show    # also open the Open3D window
```

---

## 1. Files in the SDK folder

Path: `src/deep_learning_models/models/raw_models/anygrasp/`

| File | Purpose |
|---|---|
| `gsnet.so` | the AnyGrasp engine |
| `lib_cxx.so` | helper library |
| `license/` | 4 files — `.lic`, `.public_key`, `.signature`, `licenseCfg.json` |
| `log/checkpoint_detection.tar` | trained model weights (296 MB) |
| `example_data/` | sample scene — only for the self-check |

---

## 2. Shell settings (you type these)

| Line | Why | Required? |
|---|---|---|
| `conda activate anygrasp` | gives torch, MinkowskiEngine, graspnetAPI, pointnet2 | **Yes** |
| `export PYTHONNOUSERSITE=1` | ignore `~/.local`, so the wrong torch is not picked | **Yes** |
| `export LD_LIBRARY_PATH=/home/mira/workspaces/anygrasp/openssl11_libs:$LD_LIBRARY_PATH` | gives `libcrypto.so.1.1` for `gsnet.so` | **Yes** |
| `export OMP_NUM_THREADS=8` | cap CPU threads | No — speed only |
| `source .../conda.sh` | make `conda` command exist | No — `.bashrc` already does it |

True required list = **3 lines**, not 5.

---

## 3. In-code settings (the class does these — you do NOT type them)

Inside `anygrasp_model.py`, `__init__` does two things:

| Line | Why |
|---|---|
| `sys.path.append(SDK_DIR)` | so `import gsnet` finds `gsnet.so` |
| `os.chdir(SDK_DIR)` | so the license checker finds `./license/` |

This is the whole reason the class exists — to hide these two lines.

---

## 4. Hardware / machine facts

| Need | Detail |
|---|---|
| GPU + CUDA | AnyGrasp runs on the GPU |
| Wired NIC present | license reads the MAC of `enp2s0` (`d8:43:ae:d8:7c:3e`) |

---

## 5. Why each `export` is needed

| Setting | Requirement it solves |
|---|---|
| `conda activate anygrasp` | Ubuntu 22.04 system python has no torch/Minkowski. The conda env does. |
| `PYTHONNOUSERSITE=1` | `~/.local` may hold a different torch. Without this, MinkowskiEngine fails with an `undefined symbol` error. |
| `LD_LIBRARY_PATH ...openssl11_libs` | `gsnet.so` needs `libcrypto.so.1.1`. Ubuntu 22.04 ships openssl 3.0. The side folder holds 1.1. |

---

## 6. Docker vs Laptop

Same 4 settings. Docker bakes them into the image; the laptop makes you type them.

| Setting | Laptop | Docker (`Dockerfile.robotics_layer2`) |
|---|---|---|
| torch, Minkowski | `conda activate` | built into system python (line ~231) |
| openssl 1.1 | `export LD_LIBRARY_PATH` | `ENV LD_LIBRARY_PATH=/opt/openssl11` (line 288) |
| thread cap | `export OMP_NUM_THREADS=8` | `ENV OMP_NUM_THREADS=8` (line 289) |
| ignore `~/.local` | `export PYTHONNOUSERSITE=1` | not needed — image has no polluting `~/.local` |

In docker with `--network host`, the container sees the laptop's real `enp2s0` MAC, so the license passes there too.

---

## 7. Minor gotcha — `.TimeRecord`

`.TimeRecord` in the SDK folder is owned by `root` (made inside docker). On the laptop you see:

```
[error] Unable to create file ./.TimeRecord
```

Harmless — license still passes. Delete when you like:

```bash
sudo rm src/deep_learning_models/models/raw_models/anygrasp/.TimeRecord
```
