"""
log_update.py
─────────────────────────────────────────────────────────────────
Simple script to append a project update to your existing txt file
in your GitHub repo and push it automatically.

HOW TO USE:
  1. Put this script inside your cloned GitHub repo folder
  2. Set LOG_FILE below to your txt file name
  3. Run:  python log_update.py
─────────────────────────────────────────────────────────────────
"""

import os
import subprocess
from datetime import datetime

# ── SETTINGS ──────────────────────────────────────────────────
LOG_FILE = "log.txt"   # ← Change this to your exact txt file name
# ──────────────────────────────────────────────────────────────


def ask(question):
    """Ask a question and return the answer."""
    answer = input(f"\n{question}\n> ").strip()
    return answer


def write_to_file(entry):
    """Append the entry to the txt file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"\n  ✅ Written to {LOG_FILE}")


def git_push():
    """Stage, commit, and push using basic git commands."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        subprocess.run(["git", "add", LOG_FILE],          check=True)
        subprocess.run(["git", "commit", "-m",
                        f"log: update {date_str}"],       check=True)
        subprocess.run(["git", "push"],                   check=True)
        print("\n  🚀 Pushed to GitHub successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n  ⚠  Git error: {e}")
        print("  Try running these commands manually:")
        print(f"    git add {LOG_FILE}")
        print(f"    git commit -m 'log: update {date_str}'")
        print("    git push")


def main():
    print("\n" + "=" * 50)
    print("  Project Log Updater")
    print("=" * 50)

    now      = datetime.now().strftime("%Y-%m-%d %H:%M")
    week     = datetime.now().isocalendar()[1]

    # Ask the user simple questions
    completed = ask("What did you complete?")
    planned   = ask("What will you work on next?")
    blockers  = ask("Any blockers? (press Enter to skip)")
    notes     = ask("Any other notes? (press Enter to skip)")

    # Build the entry
    entry = f"""
============================================================
Date    : {now}
Week    : {week}
------------------------------------------------------------
Completed : {completed}
Next      : {planned}
"""
    if blockers:
        entry += f"Blockers  : {blockers}\n"
    if notes:
        entry += f"Notes     : {notes}\n"

    entry += "============================================================\n"

    # Preview
    print("\n--- Preview ---")
    print(entry)

    confirm = input("Write this to your log file and push? (y/n): ").strip().lower()
    if confirm == "y":
        write_to_file(entry)
        git_push()
    else:
        print("\n  Cancelled. Nothing was written.")

    print("\n  Done!\n")


if __name__ == "__main__":
    main()
