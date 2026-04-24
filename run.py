import subprocess, sys, os

project_root = os.path.dirname(os.path.abspath(__file__))

result = subprocess.run(
    [sys.executable, "-m"] + sys.argv[1:],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=project_root,
)
output = result.stdout
if result.stderr.strip():
    output += "\n--- STDERR ---\n" + result.stderr
output += f"\nExit code: {result.returncode}\n"
with open(os.path.join(project_root, "run_output.txt"), "w", encoding="utf-8") as fh:
    fh.write(output)
sys.exit(result.returncode)
