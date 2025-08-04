from pathlib import Path
import subprocess
import sys

from commands.common import print_help_for_command


def cmd_profile(args, state):
    if args:
        return print_help_for_command("profile", state)

    script_path = Path("update_provider_profile_urls/update_provider_profile_urls.py")
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return

    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run script: {e}")
