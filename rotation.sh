#!/bin/bash

script_dir="$(dirname "$(readlink -f "$0")")"

source "$script_dir/venv/bin/activate"

python "$script_dir/rotation.py" "$1"

deactivate