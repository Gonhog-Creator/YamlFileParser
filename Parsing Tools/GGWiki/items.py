#!/usr/bin/env python3
"""
Items data processing tool for GGWiki.
Processes item YAML files and generates Lua data files for wiki.
"""

import os
import shutil
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any


class ItemsProcessor:
    """Process item data and images for GGWiki."""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.download_dir = self.find_latest_download()
        self.images_dir = self.download_dir / "images" / "images"
        self.data_dir = self.download_dir / "data" / "data"
        self.output_images_dir = self.base_dir / "outputImages"
        self.output_lua_dir = self.base_dir / "outputLua"
        self.detail_data_dir = self.base_dir / "detailData"
        self.items_config_file = self.detail_data_dir / "items_config.yaml"
        
        # Load items configuration
        self.items_config = self.load_items_config()
        
        # Load economy.js for item descriptions
        self.economy_descriptions = self.load_economy_descriptions()
    
    def find_latest_download(self) -> Path:
        """Find the most recent download folder."""
        download_folders = []
        
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.startswith("Download "):
                download_folders.append(item)
        
        if not download_folders:
            raise FileNotFoundError("No download folders found starting with 'Download '")
        
        # Sort by modification time, most recent first
        download_folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest = download_folders[0]
        print(f"Using latest download folder: {latest.name}")
        return latest
    
    def load_items_config(self) -> Dict[str, Any]:
        """Load items configuration from YAML file."""
        if not self.items_config_file.exists():
            print(f"Warning: Items config file not found: {self.items_config_file}")
            return {}
        
        try:
            with open(self.items_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f"Error loading items config: {e}")
            return {}
    
    def load_economy_descriptions(self) -> Dict[str, str]:
        """Load item descriptions from economy.js file."""
        economy_file = self.download_dir / "economy.js"
        
        if not economy_file.exists():
            print(f"Warning: economy.js not found: {economy_file}")
            return {}
        
        try:
            with open(economy_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the JavaScript file to extract descriptions
            descriptions = {}
            
            # Simple approach: find all "key: "value"" patterns in the file
            # and filter for ones that look like item descriptions
            item_pattern = r'(\w+):\s*"([^"]+)"'
            all_matches = re.findall(item_pattern, content)
            
            # Filter to only include items that are in our config
            items_mapping = self.items_config.get('items', {})
            
            for item_id, description in all_matches:
                if item_id in items_mapping:
                    descriptions[item_id] = description
            
            print(f"Loaded {len(descriptions)} descriptions from economy.js")
            return descriptions
        except Exception as e:
            print(f"Error loading economy.js: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def parse_item_yaml(self, item_id: str) -> Dict[str, Any]:
        """Parse item YAML data file."""
        yaml_file = self.data_dir / "items" / f"{item_id}.yaml"
        
        if not yaml_file.exists():
            print(f"Warning: YAML file not found for {item_id}: {yaml_file}")
            return {}
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data
        except Exception as e:
            print(f"Error parsing YAML for {item_id}: {e}")
            return {}
    
    def get_image_filename(self, item_id: str) -> str:
        """Get the image filename for an item from config or default pattern."""
        image_patterns = self.items_config.get('image_patterns', {})
        special_mappings = image_patterns.get('special_mappings', {})
        
        # Check special mappings first
        if item_id in special_mappings:
            filename = special_mappings[item_id]
            # Remove item_ prefix for Lua output
            if filename.startswith('item_'):
                filename = filename[5:]
            return filename
        
        # Use default pattern
        default_pattern = image_patterns.get('default_pattern', 'item_{item_id}.webp')
        filename = default_pattern.format(item_id=item_id)
        # Remove item_ prefix for Lua output
        if filename.startswith('item_'):
            filename = filename[5:]
        return filename
    
    def find_and_copy_image(self, item_id: str, image_filename: str) -> bool:
        """Find and copy item image to output directory."""
        # Create items subfolder
        items_output_dir = self.output_images_dir / "items"
        items_output_dir.mkdir(parents=True, exist_ok=True)
        
        # The image_filename is for Lua output (without item_ prefix)
        # For source lookup, we need to add item_ prefix back (unless it's a resource)
        if image_filename.startswith('resource_'):
            source_filename = image_filename
        elif not image_filename.startswith('item_'):
            source_filename = f"item_{image_filename}"
        else:
            source_filename = image_filename
        
        # Try to find the image in various locations
        possible_paths = [
            self.images_dir / "icons" / "items" / source_filename,
            self.images_dir / "icons" / "stores" / source_filename,
            self.images_dir / "icons" / source_filename,
            self.images_dir / "icons" / "resources" / source_filename,  # For resource images
        ]
        
        # If not found, try with resource_ prefix for certain items
        if not any(path.exists() for path in possible_paths):
            resource_source = f"resource_{image_filename}"
            possible_paths.append(self.images_dir / "icons" / "resources" / resource_source)
        
        for source_path in possible_paths:
            if source_path.exists():
                output_path = items_output_dir / image_filename
                try:
                    shutil.copy2(source_path, output_path)
                    print(f"Copied: {source_path.name} -> items/{image_filename}")
                    return True
                except Exception as e:
                    print(f"Error copying {source_path}: {e}")
        
        print(f"Warning: Image not found for {item_id}: {image_filename}")
        return False
    
    def get_category_display_name(self, category_key: str) -> str:
        """Get display name for a category."""
        categories = self.items_config.get('categories', {})
        if category_key in categories:
            return categories[category_key].get('display_name', category_key)
        return category_key
    
    def generate_lua_entry(self, item_id: str, item_config: Dict[str, Any], 
                          yaml_data: Dict[str, Any]) -> str:
        """Generate Lua table entry for an item."""
        display_name = item_config.get('display_name', item_id.replace('_', ' ').title())
        category_key = item_config.get('category', 'unknown')
        category_display = self.get_category_display_name(category_key)
        image_filename = self.get_image_filename(item_id)
        
        # Priority for descriptions: config > economy.js > YAML auto-gen > default
        description = item_config.get('description', '')
        
        if not description and item_id in self.economy_descriptions:
            # Use description from economy.js
            description = self.economy_descriptions[item_id]
            
            # Post-process descriptions for time skip items to add [[]] brackets
            if category_key == 'time_skip':
                description = description.replace('Building', '[[Building]]')
                description = description.replace('Research', '[[Research]]')
                description = description.replace('Great Dragon', '[[Great Dragon]]')
                description = description.replace('Troop training', '[[Troop training]]')
                description = description.replace('March', '[[March]]')
        
        if not description and yaml_data:
            # Try to generate description from YAML
            effects = yaml_data.get('effects', [])
            if effects:
                effect = effects[0]
                effect_name = effect.get('name', '')
                if effect_name == 'action_time_reduction':
                    default = effect.get('default', 0)
                    default_unit = effect.get('default_unit', '')
                    if default_unit == 'flat':
                        minutes = default // 60
                        if minutes == 1:
                            description = f"Shortens time by 1 minute."
                        else:
                            description = f"Shortens time by {minutes} minutes."
                    else:
                        description = f"Shortens time by {default}%."
        
        # Default description if still empty
        if not description:
            description = f"A {category_display} item."
        
        # Generate found_in from config or default based on category
        found_in = item_config.get('found_in', '')
        if not found_in:
            # Generate default based on category
            if category_key == 'time_skip':
                found_in = "[[Wilds]], [[Anthropus Camps]]"
            elif category_key == 'building_item':
                found_in = "[[Fortuna's Vault]], [[Chests]], [[Events]]"
            elif category_key == 'consumable_resource':
                found_in = "[[Chests]] and [[Events]]"
            elif category_key == 'march_speed_boosts':
                found_in = "[[Fortuna's Vault]], [[Chests]], [[Events]]"
            elif category_key == 'training_speed_boosts':
                found_in = "[[Fortuna's Vault]], [[Chests]], [[Events]]"
            elif category_key == 'revival_time_speed_boosts':
                found_in = "[[Fortuna's Vault]], [[Chests]], [[Events]]"
            elif category_key == 'city_items':
                found_in = "[[Fortuna's Vault]], [[Chests]], [[Events]]"
            elif category_key == 'chests':
                found_in = "[[Fortuna's Vault]], [[Fortuna's Chance]], [[Events]]"
            elif category_key == 'elite_items':
                found_in = "Generated by outpost factories"
            elif category_key == 'demon_tower_items':
                found_in = "[[Demon Tower]]"
            elif category_key == 'dragon_armor':
                found_in = "[[Wilds]] with [[Dragons]]"
            else:
                found_in = "N/A"
        
        # Generate Lua entry
        if ' ' in display_name:
            entry = f'''    ["{display_name}"] = {{
        description = "{description}",
        found_in = "{found_in}",
        image = "{image_filename}",
        type = "{category_display}",
        cost = "N/A",
    }}'''
        else:
            entry = f'''    {display_name} = {{
        description = "{description}",
        found_in = "{found_in}",
        image = "{image_filename}",
        type = "{category_display}",
        cost = "N/A",
    }}'''
        
        return entry
    
    def generate_lua_file(self, items_data: List[Dict[str, Any]]) -> str:
        """Generate complete Lua data file."""
        lua_content = "-- Module:Items/data\nlocal items = {\n"
        
        for item_entry in items_data:
            lua_content += item_entry + ",\n"
        
        lua_content += "}\n\nreturn items"
        return lua_file
    
    def process_all_items(self):
        """Process all items from configuration."""
        print("Processing items...")
        print(f"Images source: {self.images_dir}")
        print(f"Data source: {self.data_dir}")
        print(f"Output images: {self.output_images_dir}")
        print(f"Output Lua: {self.output_lua_dir}")
        print("-" * 50)
        
        items_entries = []
        processed_display_names = set()
        
        items_mapping = self.items_config.get('items', {})
        
        for item_id, item_config in items_mapping.items():
            # Skip if not included
            if not item_config.get('include', False):
                print(f"Skipping {item_id} (not included)")
                continue
            
            display_name = item_config.get('display_name', item_id)
            
            # Skip if we've already processed this display name (avoid duplicates)
            if display_name in processed_display_names:
                print(f"Skipping {item_id} (duplicate display name: {display_name})")
                continue
            
            print(f"\nProcessing {item_id} ({display_name})...")
            
            # Check if this is a manual item (not from YAML)
            if item_config.get('manual', False):
                print(f"  Manual item (no YAML)")
                yaml_data = {}
            else:
                # Parse YAML data
                yaml_data = self.parse_item_yaml(item_id)
                if not yaml_data:
                    print(f"  Skipping {item_id} - no YAML data")
                    continue
            
            # Find and copy image (skip for dragon armor - handled in dragons folder)
            category_key = item_config.get('category', '')
            image_filename = self.get_image_filename(item_id)
            if category_key == 'dragon_armor':
                print(f"  Skipping image copy for dragon armor (handled in dragons folder)")
                image_copied = False
            else:
                image_copied = self.find_and_copy_image(item_id, image_filename)
            
            # Generate Lua entry
            lua_entry = self.generate_lua_entry(item_id, item_config, yaml_data)
            items_entries.append(lua_entry)
            processed_display_names.add(display_name)
            print(f"  Generated Lua entry for {display_name}")
        
        # Sort entries by display name
        items_entries.sort()
        
        # Generate and write Lua file
        if items_entries:
            lua_content = "-- Module:Items/data\nlocal items = {\n"
            for item_entry in items_entries:
                lua_content += item_entry + ",\n"
            lua_content += "}\n\nreturn items"
            
            lua_output_path = self.output_lua_dir / "Items-data"
            
            try:
                with open(lua_output_path, 'w', encoding='utf-8') as f:
                    f.write(lua_content)
                print(f"\nLua file written to: {lua_output_path}")
            except Exception as e:
                print(f"Error writing Lua file: {e}")
        else:
            print("\nNo item entries generated")
        
        print(f"Total items processed: {len(items_entries)}")


def main():
    """Main entry point."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    
    processor = ItemsProcessor(str(script_dir))
    processor.process_all_items()


if __name__ == "__main__":
    main()
