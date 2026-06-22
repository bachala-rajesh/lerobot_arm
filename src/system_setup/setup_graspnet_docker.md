# Claude Code Prompt — Install GraspNet inside Isaac ROS Docker

Paste this entire prompt into a Claude Code session running inside the docker.

---

## Task: Install GraspNet-baseline inside Isaac ROS Docker

### Context
We already installed GraspNet-baseline successfully on the host machine.
The setup guide with all patches is at:
/workspaces/lerobot_ws/src/system_setup/setup_graspnet.md

Read that file first — it has all 6 patches needed.

---

### Docker environment (verified)

- OS: Ubuntu 22.04
- Python: 3.10.12 at /usr/bin/python3
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU (sm_89)
- CUDA toolkit: 12.6 at /usr/local/cuda-12.6
- torch: 2.9.1 (compiled with CUDA 12.8 — minor mismatch, acceptable)
- nvcc: 12.6
- g++: 12.3

Already installed (skip these):
- torch 2.9.1, open3d 0.19.0, scipy 1.15.3, scikit-learn 1.7.2, trimesh 4.4.3

---

### Key difference from host setup

On host: CUDA_HOME=/usr/local/cuda-13.0, CPATH from nvidia/cu13/include
In docker: use these exact env vars instead:

  export CUDA_HOME=/usr/local/cuda-12.6
  export PATH=$CUDA_HOME/bin:$PATH
  export TORCH_CUDA_ARCH_LIST="8.9"
  export CPATH=/usr/local/cuda-12.6/targets/x86_64-linux/include

No venv needed — install directly into docker's global Python.

---

### Install location

Clone repo to: /workspaces/graspnet/

---

### Phase 1: Manual install (step by step)

Follow the same steps as setup_graspnet.md but with these changes:
- No venv — use python/pip directly
- Use docker CUDA paths above
- Same 6 patches apply

Steps in order:
1. Clone repo to /workspaces/graspnet/
2. Install missing Python deps: transforms3d cvxopt Pillow autolab_core gdown
   (open3d, scipy, scikit-learn, trimesh already installed)
3. Install graspnetAPI from local source
4. Compile pointnet2 extension
5. Compile knn extension
6. Fix egg zip issue (extract both .so files from eggs)
7. Apply all 6 source patches from setup_graspnet.md
8. Download checkpoint-rs.tar via gdown
9. Run demo.py — verify Open3D window opens

One step at a time. Wait for confirmation after each step.
Show exact error and diagnose before applying any fix.

---

### Phase 2: Dockerfile layer (only after Phase 1 succeeds)

After manual install works, write the Dockerfile RUN commands
that reproduce the exact same steps.
Place them as a separate section in:
/workspaces/lerobot_ws/src/setup_graspnet.md
under a new heading: ## Dockerfile Layer

---

### Communication rules
- Simple English. Short sentences.
- Ask confirmation before each step.
- One step at a time.
- If something fails, show exact error before fixing.
