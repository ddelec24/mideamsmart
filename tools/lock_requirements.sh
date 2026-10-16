#!/bin/bash
# Regenerate resources/requirements.lock from resources/requirements.in.
# The lock is universal (every architecture) and hashed: the install script
# installs it with --require-hashes. Run it after changing a version in
# requirements.in, with the same uv and Python versions as resources/install_apt.sh.
#
# Usage: tools/lock_requirements.sh [path to uv]
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="${1:-uv}"
PYTHON_VERSION="$(sed -n 's/^PYTHON_VERSION=//p' "${PLUGIN_DIR}/resources/install_apt.sh")"

"${UV_BIN}" pip compile "${PLUGIN_DIR}/resources/requirements.in" \
	--universal \
	--python-version "${PYTHON_VERSION}" \
	--generate-hashes \
	--no-header \
	--output-file "${PLUGIN_DIR}/resources/requirements.lock"
