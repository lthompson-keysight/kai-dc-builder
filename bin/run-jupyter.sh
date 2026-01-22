#!/usr/bin/env bash
set -euo pipefail

VENV_PATH=/home/jovyan/.venv/dse/dse-${VERSION}
KERNEL_NAME="KAI-DC-Builder"
REQ_FILE=/home/jovyan/requirements.txt
MODULES_PATH=/home/jovyan/modules

# 1) Ensure the venv exists
if [ ! -x "$VENV_PATH/bin/python" ]; then
  python -m venv "$VENV_PATH"
fi

# 2) Upgrade pip/setuptools/wheel (safer builds), then install requirements if present
"$VENV_PATH/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_PATH/bin/python" -m pip install -q ipykernel
if [ -f "$REQ_FILE" ]; then
  echo "Installing Python packages from ${REQ_FILE} into ${VENV_PATH}..."
  "$VENV_PATH/bin/python" -m pip install --find-links="$MODULES_PATH" -r "$REQ_FILE"
fi

# 3) Register (or update) the kernel spec to point at this venv
#    --name is the stable ID; --display-name is what shows in the UI.
"$VENV_PATH/bin/python" -m ipykernel install --user --name="$KERNEL_NAME" --display-name="Python ($KERNEL_NAME)"

# 4) Launch Jupyter with Blah as the default for NEW notebooks
jupyter labextension disable "@jupyterlab/apputils-extension:announcements"
exec start-notebook.sh --MappingKernelManager.default_kernel_name="$KERNEL_NAME"