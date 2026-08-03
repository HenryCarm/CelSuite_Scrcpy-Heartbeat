import os
import sys
import subprocess
import shutil

def main():
    """Compiles the application using Nuitka, falling back to a terminal if available."""
    python_exe = sys.executable
    output_dir = "dist/"
    
    cmd = [
        python_exe, "-m", "nuitka",
        "--standalone",
        f"--output-dir={output_dir}",
        "main.py"
    ]
    
    terminals = ["xfce4-terminal", "gnome-terminal", "x-terminal-emulator"]
    term_cmd = None
    
    for term in terminals:
        if shutil.which(term):
            if term == "xfce4-terminal":
                term_cmd = [term, "-x", "bash", "-c", f"{' '.join(cmd)}; read -p 'Press enter to continue...'"]
            elif term == "gnome-terminal":
                term_cmd = [term, "--", "bash", "-c", f"{' '.join(cmd)}; read -p 'Press enter to continue...'"]
            else:
                term_cmd = [term, "-e", f"bash -c \"{' '.join(cmd)}; read -p 'Press enter to continue...'\""]
            break
            
    if term_cmd:
        print(f"Running compilation in {term_cmd[0]}...")
        try:
            subprocess.Popen(term_cmd)
        except OSError as e:
            print(f"Failed to launch terminal: {e}")
            print("Running compilation in current terminal...")
            subprocess.run(cmd, check=True)
    else:
        print("Running compilation in current terminal...")
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()