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
    """Check if Node.js and npm are available in the system PATH."""
    return shutil.which("node") and shutil.which("npm")


def ensure_npx():
    """Ensure npx is available by updating npm if necessary."""
    if shutil.which("npx"):
        return  # npx is already available

    if not shutil.which("npm"):
        print("npm is not available")
        sys.exit(1)

    print("npx is not available, updating npm to latest version...")
    try:
        # Update npm to latest version which includes npx
        subprocess.run(["npm", "install", "-g", "npm@latest"], check=True)
        print("npm updated successfully")

        # Check if npx is now available
        if not shutil.which("npx"):
            print("npx still not available, installing manually...")
            subprocess.run(["npm", "install", "-g", "npx"], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Failed to update npm: {e}")
        sys.exit(1)


def install_node_linux_mac():
    """Install Node.js on Linux or macOS systems."""
    system = platform.system().lower()
    arch = platform.machine()

    # Map architecture names to Node.js distribution naming
    if arch in ("x86_64", "amd64"):
        arch = "x64"
    elif arch in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        print(f"Unsupported architecture: {arch}")
        sys.exit(1)

    filename = f"node-v{NODE_VERSION}-{system}-{arch}.tar.xz"
    url = f"{NODE_DIST_URL}/v{NODE_VERSION}/{filename}"

    print(f"Downloading Node.js from {url}")
    urllib.request.urlretrieve(url, filename)

    print("Extracting Node.js...")
    with tarfile.open(filename) as tar:
        tar.extractall("nodejs")
    os.remove(filename)

    # Find the extracted directory and add its bin folder to PATH
    extracted = next(d for d in os.listdir("nodejs") if d.startswith("node-v"))
    node_bin = os.path.abspath(f"nodejs/{extracted}/bin")
    os.environ["PATH"] = node_bin + os.pathsep + os.environ["PATH"]

    # Re-execute the script with Node.js available
    os.execv(sys.executable, [sys.executable] + sys.argv)


def install_node_windows():
    """Install Node.js on Windows using MSI installer."""
    print("Downloading Node.js MSI installer for Windows...")
    filename = os.path.join(tempfile.gettempdir(), "node-installer.msi")
    url = f"{NODE_DIST_URL}/v{NODE_VERSION}/node-v{NODE_VERSION}-x64.msi"
    urllib.request.urlretrieve(url, filename)

    print("Running silent installer (requires admin privileges)...")
    try:
        subprocess.run(["msiexec", "/i", filename, "/quiet", "/norestart"], check=True)
    except subprocess.CalledProcessError as e:
        print("Node.js installation failed.")
        print(e)
        sys.exit(1)

    print("Node.js installed successfully.")
    node_path = "C:\\Program Files\\nodejs"
    os.environ["PATH"] = node_path + os.pathsep + os.environ["PATH"]

    # Re-execute script to continue with Node.js available
    os.execv(sys.executable, [sys.executable] + sys.argv)


def ensure_ccusage_available():
    """Ensure ccusage is available via npx."""
    try:
        # Check if ccusage is available
        result = subprocess.run(
            ["npx", "--no-install", "ccusage", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✓ ccusage is available")
            return  # ccusage is available

        print("Installing ccusage...")
        # Try global installation first
        try:
            subprocess.run(
                ["npm", "install", "-g", "ccusage"], check=True, capture_output=True
            )
            print("✓ ccusage installed globally")
        except subprocess.CalledProcessError:
            # If global fails, install locally
            print("Global installation failed, trying local installation...")
            subprocess.run(["npm", "install", "ccusage"], check=True)
            print("✓ ccusage installed locally")
    except Exception as e:
        print(f"Failed to install ccusage: {e}")
        print("You may need to install ccusage manually: npm install -g ccusage")
        sys.exit(1)


def ensure_node_installed():
    """Ensure Node.js, npm, npx, and ccusage are all available."""
    print("Checking dependencies...")

    if not is_node_available():
        # Install Node.js if not present
        system = platform.system()
        if system in ("Linux", "Darwin"):
            install_node_linux_mac()
        elif system == "Windows":
            install_node_windows()
        else:
            print(f"Unsupported OS: {system}")
            sys.exit(1)
    else:
        print("✓ Node.js and npm are available")
        # Node.js and npm are present, but check npx
        ensure_npx()

    # Ensure ccusage is available
    ensure_ccusage_available()
    print("✓ All dependencies are ready")
