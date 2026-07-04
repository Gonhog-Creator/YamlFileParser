#!/usr/bin/env python3
"""
Dragons data processing tool for GGWiki.
Processes dragon images and generates Lua data files for wiki.
"""

import os
import shutil
import yaml
from pathlib import Path
from typing import Dict, List, Any


class DragonsProcessor:
    """Process dragon data and images for GGWiki."""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.download_dir = self.find_latest_download()
        self.images_dir = self.download_dir / "images" / "images"
        self.data_dir = self.download_dir / "data" / "data"
        self.output_images_dir = self.base_dir / "outputImages"
        self.output_lua_dir = self.base_dir / "outputLua"
        self.detail_data_dir = self.base_dir / "detailData"
        self.reference_file = self.base_dir / "wikiRefrence" / "Module-GreatDragonData"
        
        # Dragon types to process (including great_dragon)
        self.dragon_types = ["great", "fire", "water", "stone"]
        
        # Image stage mapping
        self.stage_mapping = {
            "1": "baby",
            "2": "adolescent", 
            "3": "adult",
            "4": "armored"
        }
    
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
    
    def load_detail_data(self) -> Dict[str, Any]:
        """Load detail data from YAML file."""
        detail_file = self.detail_data_dir / "dragon_descriptions.yaml"
        
        if not detail_file.exists():
            print(f"Warning: Detail data file not found: {detail_file}")
            return {}
        
        try:
            with open(detail_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data.get('dragons', {})
        except Exception as e:
            print(f"Error loading detail data: {e}")
            return {}
    
    def load_reference_dragon(self, dragon_name: str) -> Dict[str, Any]:
        """Load dragon data from reference Lua file."""
        if not self.reference_file.exists():
            print(f"Warning: Reference file not found: {self.reference_file}")
            return None
        
        try:
            with open(self.reference_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple parsing to extract dragon entry
            # This is a basic parser - for production use, consider a proper Lua parser
            start_marker = f'["{dragon_name}"]'
            start_idx = content.find(start_marker)
            
            if start_idx == -1:
                return None
            
            # Find the end of this entry (next dragon or closing brace)
            end_idx = content.find('\n    },\n', start_idx + 1)
            if end_idx == -1:
                end_idx = content.find('\n    }\n', start_idx + 1)
            
            if end_idx == -1:
                return None
            
            entry_text = content[start_idx:end_idx + 6]
            
            # Parse key values from the entry
            dragon_data = {}
            dragon_data['name'] = dragon_name
            
            # Extract description
            desc_start = entry_text.find('description= "')
            if desc_start != -1:
                desc_end = entry_text.find('",', desc_start + 14)
                if desc_end != -1:
                    dragon_data['description'] = entry_text[desc_start + 14:desc_end]
            
            # Extract descriptionTech
            desc_tech_start = entry_text.find('descriptionTech = "')
            if desc_tech_start != -1:
                desc_tech_end = entry_text.find('",', desc_tech_start + 19)
                if desc_tech_end != -1:
                    dragon_data['descriptionTech'] = entry_text[desc_tech_start + 19:desc_tech_end]
            
            # Extract found_in
            found_start = entry_text.find('found_in = "')
            if found_start != -1:
                found_end = entry_text.find('",', found_start + 12)
                if found_end != -1:
                    dragon_data['found_in'] = entry_text[found_start + 12:found_end]
            
            return dragon_data
            
        except Exception as e:
            print(f"Error loading reference dragon: {e}")
            return None
    
    def find_dragon_images(self, dragon_type: str) -> Dict[str, Path]:
        """Find dragon images for a given type in outpost folder."""
        outpost_dir = self.images_dir / "buildings" / "outposts" / dragon_type
        images = {}
        
        if not outpost_dir.exists():
            print(f"Warning: Outpost directory not found for {dragon_type}")
            return images
        
        # Look for dragon_keep_default_X.webp files
        for stage_num, stage_name in self.stage_mapping.items():
            source_file = outpost_dir / f"dragon_keep_default_{stage_num}.webp"
            if source_file.exists():
                images[stage_name] = source_file
            else:
                print(f"Warning: Image not found for {dragon_type} stage {stage_name}: {source_file}")
        
        return images
    
    def copy_and_rename_images(self, dragon_type: str, images: Dict[str, Path]) -> Dict[str, str]:
        """Copy images to output directory with proper naming."""
        output_filenames = {}
        
        # Create dragons subfolder
        dragons_output_dir = self.output_images_dir / "dragons"
        dragons_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Capitalize dragon type for filename (e.g., Fire -> Fire)
        dragon_name_capitalized = dragon_type.capitalize()
        
        for stage_name, source_path in images.items():
            # Generate output filename: e.g., Firedragonbaby.webp
            output_filename = f"{dragon_name_capitalized}dragon{stage_name}.webp"
            output_path = dragons_output_dir / output_filename
            
            try:
                shutil.copy2(source_path, output_path)
                output_filenames[stage_name] = output_filename
                print(f"Copied: {source_path.name} -> dragons/{output_filename}")
            except Exception as e:
                print(f"Error copying {source_path}: {e}")
        
        return output_filenames
    
    def find_and_copy_armor_images(self, dragon_type: str) -> Dict[str, str]:
        """Find and copy dragon armor images to output directory."""
        armor_images = {}
        armor_parts = ["helmet", "body", "claws", "tail"]
        
        # Create dragons subfolder
        dragons_output_dir = self.output_images_dir / "dragons"
        dragons_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Capitalize dragon type for filename (e.g., Fire -> Fire)
        dragon_name_capitalized = dragon_type.capitalize()
        
        for part in armor_parts:
            # Source file pattern: item_fire_dragon_armor_helmet.webp
            source_file = self.images_dir / "icons" / "items" / f"item_{dragon_type}_dragon_armor_{part}.webp"
            
            if source_file.exists():
                # Target filename: Fire dragon armor helmet.webp
                output_filename = f"{dragon_name_capitalized} dragon armor {part}.webp"
                output_path = dragons_output_dir / output_filename
                
                try:
                    shutil.copy2(source_file, output_path)
                    armor_images[part] = output_filename
                    print(f"Copied armor: {source_file.name} -> dragons/{output_filename}")
                except Exception as e:
                    print(f"Error copying armor {source_file}: {e}")
            else:
                print(f"Warning: Armor image not found for {dragon_type} {part}: {source_file}")
        
        return armor_images
    
    def parse_dragon_yaml(self, dragon_type: str) -> Dict[str, Any]:
        """Parse dragon YAML data file."""
        yaml_file = self.data_dir / "troops" / f"{dragon_type}_dragon.yaml"
        
        if not yaml_file.exists():
            print(f"Warning: YAML file not found for {dragon_type}: {yaml_file}")
            return {}
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data
        except Exception as e:
            print(f"Error parsing YAML for {dragon_type}: {e}")
            return {}
    
    def generate_lua_entry(self, dragon_type: str, yaml_data: Dict[str, Any], 
                          image_filenames: Dict[str, str], detail_data: Dict[str, Any]) -> str:
        """Generate Lua table entry for a dragon."""
        dragon_name = f"{dragon_type.capitalize()} Dragon"
        dragon_name_capitalized = dragon_type.capitalize()
        dragon_id = self.dragon_types.index(dragon_type) + 1  # Start from 1
        
        # Extract max_level from stats (highest level key)
        max_level = 10
        if 'stats' in yaml_data:
            max_level = max(int(k) for k in yaml_data['stats'].keys())
        
        # Get description data from detail file or use defaults
        dragon_key = f"{dragon_type}_dragon"
        if dragon_key in detail_data:
            desc_data = detail_data[dragon_key]
            description = desc_data.get('description', f"TODO: Add description for {dragon_name}")
            description_tech = desc_data.get('descriptionTech', f"TODO: Add technical description for {dragon_name}")
            found_in = desc_data.get('found_in', f"{dragon_name_capitalized} Outpost")
        else:
            description = f"TODO: Add description for {dragon_name}"
            description_tech = f"TODO: Add technical description for {dragon_name}"
            found_in = f"{dragon_name_capitalized} Outpost"
        
        # Generate images table
        images_table = "        images = {\n"
        for i, (stage_name, filename) in enumerate(image_filenames.items()):
            # No trailing comma on last item
            comma = "," if i < len(image_filenames) - 1 else ""
            images_table += f'            {stage_name} = "{filename}"{comma}\n'
        images_table += "        },"
        
        # Generate armor_variations table (use armored dragon image)
        armor_variations = "        armor_variations = {\n"
        # Use the armored dragon image instead of separate armor image
        armored_image = image_filenames.get("armored", "")
        armor_variations += f'\t\t    {{ name = "Normal Armor", file = "{armored_image}" }}\n'
        armor_variations += "\t\t}"
        
        # Generate full entry with exact formatting from reference
        entry = f'''    ["{dragon_name}"] = {{
        id = {dragon_id},
        name = "{dragon_name}",
        max_level = {max_level},
        description= "{description}",
        descriptionTech = "{description_tech}",
        found_in = "{found_in}",
{images_table}
{armor_variations}
    }}'''
        
        return entry
    
    def generate_lua_file(self, dragons_data: List[Dict[str, Any]]) -> str:
        """Generate complete Lua data file."""
        lua_content = "return {\n"
        
        for dragon_entry in dragons_data:
            lua_content += dragon_entry + ",\n"
        
        lua_content += "}"
        return lua_content
    
    def process_all_dragons(self):
        """Process all dragon types."""
        print("Processing dragons...")
        print(f"Images source: {self.images_dir}")
        print(f"Data source: {self.data_dir}")
        print(f"Output images: {self.output_images_dir}")
        print(f"Output Lua: {self.output_lua_dir}")
        print("-" * 50)
        
        # Load detail data
        detail_data = self.load_detail_data()
        print(f"Loaded detail data for {len(detail_data)} dragons")
        
        dragons_entries = []
        
        for dragon_type in self.dragon_types:
            print(f"\nProcessing {dragon_type} dragon...")
            
            # Skip image processing for great_dragon (already have images)
            if dragon_type == "great":
                print("Skipping image processing for Great Dragon (using existing images)")
                image_filenames = {
                    "baby": "Greatdragonbaby.webp",
                    "adolescent": "Greatdragonadolescent.webp",
                    "adult": "Greatdragonadult.webp",
                    "armored": "Greatdragonarmored.webp"
                }
            else:
                # Find images
                images = self.find_dragon_images(dragon_type)
                if not images:
                    print(f"Skipping {dragon_type} - no images found")
                    continue
                
                # Copy and rename images
                image_filenames = self.copy_and_rename_images(dragon_type, images)
                if not image_filenames:
                    print(f"Skipping {dragon_type} - no images copied")
                    continue
            
            # Copy and rename armor images (for all dragons)
            armor_filenames = self.find_and_copy_armor_images(dragon_type)
            
            # Parse YAML data
            yaml_data = self.parse_dragon_yaml(dragon_type)
            if not yaml_data:
                print(f"Skipping {dragon_type} - no YAML data")
                continue
            
            # Generate Lua entry
            lua_entry = self.generate_lua_entry(dragon_type, yaml_data, image_filenames, detail_data)
            dragons_entries.append(lua_entry)
            print(f"Generated Lua entry for {dragon_type}")
        
        # Generate and write Lua file
        if dragons_entries:
            lua_content = self.generate_lua_file(dragons_entries)
            lua_output_path = self.output_lua_dir / "Module-GreatDragonData.lua"
            
            try:
                with open(lua_output_path, 'w', encoding='utf-8') as f:
                    f.write(lua_content)
                print(f"\nLua file written to: {lua_output_path}")
            except Exception as e:
                print(f"Error writing Lua file: {e}")
        else:
            print("\nNo dragon entries generated")


def main():
    """Main entry point."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    
    processor = DragonsProcessor(str(script_dir))
    processor.process_all_dragons()


if __name__ == "__main__":
    main()
