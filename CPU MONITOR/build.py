import subprocess
import os

def build():
    print("Starting PyInstaller compilation...")
    # Add assets folder. In Windows, PyInstaller expects 'source;destination' format separated by a semicolon.
    cmd = [
        "python", "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--add-data", "assets;assets",
        "main.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print("\n" + "="*50)
        print("BUILD SUCCESSFUL!")
        print("Standalone executable is located in: dist/main.exe")
        print("="*50)
    else:
        print("\n" + "="*50)
        print(f"BUILD FAILED with exit code {result.returncode}")
        print("="*50)

if __name__ == '__main__':
    build()
