import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

NODE_VERSION = "18.17.1"
NODE_DIST_URL = "https://nodejs.org/dist"


def is_node_available():
    return shutil.which("node") and shutil.which("npm") and shutil.which("npx")


def install_node_linux_mac():
    system = platform.system().lower()
    arch = platform.machine()

    if arch in ("x86_64", "amd64"):
        arch = "x64"
    elif arch in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        print(f"❌ Unsupported architecture: {arch}")
        sys.exit(1)

    filename = f"node-v{NODE_VERSION}-{system}-{arch}.tar.xz"
    url = f"{NODE_DIST_URL}/v{NODE_VERSION}/{filename}"

    print(f"⬇️ Downloading Node.js from {url}")
    urllib.request.urlretrieve(url, filename)

    print("📦 Extracting Node.js...")
    with tarfile.open(filename) as tar:
        tar.extractall("nodejs")
    os.remove(filename)

    extracted = next(d for d in os.listdir("nodejs") if d.startswith("node-v"))
    node_bin = os.path.abspath(f"nodejs/{extracted}/bin")
    os.environ["PATH"] = node_bin + os.pathsep + os.environ["PATH"]

    os.execv(sys.executable, [sys.executable] + sys.argv)


def install_node_windows():
    print("⬇️ Downloading Node.js MSI installer for Windows...")
    filename = os.path.join(tempfile.gettempdir(), "node-installer.msi")
    url = f"{NODE_DIST_URL}/v{NODE_VERSION}/node-v{NODE_VERSION}-x64.msi"
    urllib.request.urlretrieve(url, filename)

    print("⚙️ Running silent installer (requires admin)...")
    try:
        subprocess.run(["msiexec", "/i", filename, "/quiet", "/norestart"], check=True)
    except subprocess.CalledProcessError as e:
        print("❌ Node.js installation failed.")
        print(e)
        sys.exit(1)

    print("✅ Node.js installed successfully.")
    node_path = "C:\\Program Files\\nodejs"
    os.environ["PATH"] = node_path + os.pathsep + os.environ["PATH"]

    # Re-exec script to continue with Node available
    os.execv(sys.executable, [sys.executable] + sys.argv)


def ensure_node_installed():
    if is_node_available():
        return

    system = platform.system()
    if system in ("Linux", "Darwin"):
        install_node_linux_mac()
    elif system == "Windows":
        install_node_windows()
    else:
        print(f"❌ Unsupported OS: {system}")
        sys.exit(1)


def run_ccusage():
    try:
        print("🚀 Running ccusage via npx...")
        result = subprocess.run(
            ["npx", "ccusage", "--json"],  # Customize flags
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        print("✅ ccusage output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("❌ ccusage failed:")
        print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("❌ npx not found. Ensure Node.js installed.")
        sys.exit(1)
