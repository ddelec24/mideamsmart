#!/bin/bash
# Installs the Python environment of the mideamsmart plugin.
# Launched as root by Jeedom (plugin dependencies), the first argument is the
# progress file read by the Jeedom UI.
#
# A standalone CPython is installed with uv inside the plugin, then the daemon
# libraries are installed from the hashed lock file into resources/python_venv.
# Nothing is installed in the system Python.

UV_VERSION=0.12.21
PYTHON_VERSION=3.13.15

PROGRESS_FILE="${1:-/tmp/jeedom_install_in_progress_mideamsmart}"
RESOURCES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${RESOURCES_DIR}/python_runtime"
VENV_DIR="${RESOURCES_DIR}/python_venv"
LOCK_FILE="${RESOURCES_DIR}/requirements.lock"
MARKER_FILE="${VENV_DIR}/.mideamsmart_dependencies"
WORK_DIR=""

progress() {
	echo "$1" > "${PROGRESS_FILE}"
	echo "*** [$1%] $2"
}

cleanup() {
	[ -n "${WORK_DIR}" ] && rm -rf "${WORK_DIR}"
	rm -f "${PROGRESS_FILE}"
}

fail() {
	echo "*** ERROR: $1"
	echo "*** Dependencies installation failed"
	exit 1
}

trap cleanup EXIT

echo "********************************************************"
echo "*   mideamsmart dependencies installation"
echo "*   $(date +'%Y-%m-%d %H:%M:%S')"
echo "********************************************************"
touch "${PROGRESS_FILE}"
progress 0 "Checking the system"

# The Debian architecture is used rather than the kernel one: a Raspberry Pi
# may run a 64-bit kernel with a 32-bit (armhf) system.
DEBIAN_ARCH="$(dpkg --print-architecture)"
case "${DEBIAN_ARCH}" in
	amd64)
		UV_TARGET="x86_64-unknown-linux-gnu"
		UV_SHA256="23f02075b652bb1df64178cfae41b5caf160822e720e2663568f3f5d63bc52c0"
		;;
	arm64)
		UV_TARGET="aarch64-unknown-linux-gnu"
		UV_SHA256="030b69227b40af8c1981b7301793dc66e71ed3c796ea8688209dd268bd91ec51"
		;;
	armhf)
		UV_TARGET="armv7-unknown-linux-gnueabihf"
		UV_SHA256="ddb4826a23a9a994da3d868c57b74b1fcb22e29691fc89f8b1702c6a1a9e0df7"
		;;
	*)
		fail "unsupported architecture: ${DEBIAN_ARCH} (supported: amd64, arm64, armhf)"
		;;
esac
echo "Architecture: ${DEBIAN_ARCH}, uv target: ${UV_TARGET}"

# Required system packages. A C compiler is only needed on armv7, where some
# libraries (pycryptodome) have no prebuilt wheel and are built from source.
APT_PACKAGES="ca-certificates curl"
if [ "${UV_TARGET}" = "armv7-unknown-linux-gnueabihf" ]; then
	APT_PACKAGES="${APT_PACKAGES} build-essential"
fi
MISSING_PACKAGES=""
for package in ${APT_PACKAGES}; do
	if ! dpkg -s "${package}" > /dev/null 2>&1; then
		MISSING_PACKAGES="${MISSING_PACKAGES} ${package}"
	fi
done
progress 10 "Installing system packages:${MISSING_PACKAGES:- none needed}"
if [ -n "${MISSING_PACKAGES}" ]; then
	apt-get update || fail "apt-get update failed"
	# shellcheck disable=SC2086
	apt-get install -y ${MISSING_PACKAGES} || fail "unable to install:${MISSING_PACKAGES}"
fi

WORK_DIR="$(mktemp -d)" || fail "unable to create a temporary directory"
UV_ARCHIVE="${WORK_DIR}/uv.tar.gz"
progress 20 "Downloading uv ${UV_VERSION}"
curl --fail --location --silent --show-error --retry 3 --output "${UV_ARCHIVE}" \
	"https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_TARGET}.tar.gz" \
	|| fail "unable to download uv"
echo "${UV_SHA256}  ${UV_ARCHIVE}" | sha256sum --check --status || fail "uv archive checksum mismatch"
tar -xzf "${UV_ARCHIVE}" -C "${WORK_DIR}" || fail "unable to extract uv"
UV_BIN="${WORK_DIR}/uv-${UV_TARGET}/uv"
"${UV_BIN}" --version || fail "uv does not run on this system"

# Keep every uv file inside the plugin or the temporary directory
export UV_PYTHON_INSTALL_DIR="${RUNTIME_DIR}"
export UV_CACHE_DIR="${WORK_DIR}/cache"
export UV_NO_CONFIG=1
export UV_LINK_MODE=copy

progress 35 "Installing Python ${PYTHON_VERSION}"
"${UV_BIN}" python install --no-bin "${PYTHON_VERSION}" || fail "unable to install Python ${PYTHON_VERSION}"

progress 55 "Creating the virtual environment"
rm -rf "${VENV_DIR}"
"${UV_BIN}" venv --python "${PYTHON_VERSION}" --managed-python "${VENV_DIR}" || fail "unable to create the virtual environment"

progress 65 "Installing Python libraries"
"${UV_BIN}" pip sync --python "${VENV_DIR}/bin/python3" --require-hashes "${LOCK_FILE}" \
	|| fail "unable to install the Python libraries"

progress 90 "Checking the installation"
"${VENV_DIR}/bin/python3" -c "import msmart, midealocal; print('Python', __import__('sys').version.split()[0], '- libraries OK')" \
	|| fail "the Python libraries cannot be imported"
"${UV_BIN}" pip list --python "${VENV_DIR}/bin/python3"

# Removes the Python versions previously installed by this script (never the system one)
"${UV_BIN}" python list --only-installed --managed-python --output-format json 2>/dev/null \
	| "${VENV_DIR}/bin/python3" -c "import json, sys; print('\n'.join(sorted({p['version'] for p in json.load(sys.stdin) if p['path'].startswith('${RUNTIME_DIR}/') and p['version'] != '${PYTHON_VERSION}'})))" \
	| while read -r old_version; do
		[ -n "${old_version}" ] && "${UV_BIN}" python uninstall "${old_version}"
	done

# The marker lets the plugin detect that the dependencies match this script and lock file
cat "${BASH_SOURCE[0]}" "${LOCK_FILE}" | sha256sum | cut -d ' ' -f 1 > "${MARKER_FILE}"
chown -R www-data:www-data "${RUNTIME_DIR}" "${VENV_DIR}" 2> /dev/null

progress 100 "Done"
echo "********************************************************"
echo "*   Dependencies installed successfully"
echo "********************************************************"
