#!/usr/bin/env python3
"""
Interactive tool for selecting GGWiki data processing modules.
Allows user to choose which category to process (troops, items, buildings, dragons, etc.)
"""

import sys
from pathlib import Path
from typing import Dict, Callable


class GGWikiInteractiveTool:
    """Interactive CLI tool for GGWiki data processing."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.modules: Dict[str, Callable] = {
            '1': ('Buildings', self.process_buildings),
            '2': ('Dragons', self.process_dragons),
            '0': ('Exit', self.exit_tool),
        }
    
    def display_menu(self):
        """Display the main menu."""
        print("\n" + "=" * 50)
        print("GGWiki Data Processing Tool")
        print("=" * 50)
        print("\nSelect a module to process:")
        for key, (name, _) in self.modules.items():
            print(f"  [{key}] {name}")
        print("=" * 50)
    
    def process_buildings(self):
        """Process buildings data."""
        print("\nProcessing Buildings...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, str(self.base_dir / "buildings.py")],
                cwd=str(self.base_dir),
                capture_output=False
            )
            if result.returncode != 0:
                print(f"\nBuildings processing failed with return code {result.returncode}")
        except Exception as e:
            print(f"\nError running buildings.py: {e}")
    
    def process_dragons(self):
        """Process dragons data."""
        print("\nProcessing Dragons...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, str(self.base_dir / "dragons.py")],
                cwd=str(self.base_dir),
                capture_output=False
            )
            if result.returncode != 0:
                print(f"\nDragons processing failed with return code {result.returncode}")
        except Exception as e:
            print(f"\nError running dragons.py: {e}")
    
    def exit_tool(self):
        """Exit the tool."""
        print("\nExiting GGWiki Interactive Tool...")
        sys.exit(0)
    
    def run(self):
        """Run the interactive tool."""
        while True:
            self.display_menu()
            choice = input("\nEnter your choice: ").strip()
            
            if choice in self.modules:
                _, func = self.modules[choice]
                func()
                
                if choice != '0':
                    input("\nPress Enter to continue...")
            else:
                print("\nInvalid choice. Please try again.")


def main():
    """Main entry point."""
    tool = GGWikiInteractiveTool()
    tool.run()


if __name__ == "__main__":
    main()
