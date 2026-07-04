import yaml
from pathlib import Path
from typing import Dict, List, Any
import re
import shutil


class BuildingsProcessor:
    """Process building data and generate Lua Module-BuildingsData."""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.download_dir = self.find_latest_download()
        self.data_dir = self.download_dir / "data" / "data"
        self.buildings_dir = self.data_dir / "buildings"
        self.images_dir = self.download_dir / "images" / "images"
        self.detail_data_dir = self.base_dir / "detailData"
        self.reference_file = self.base_dir / "wikiRefrence" / "Module-BuildlingsData"
        self.output_lua_dir = self.base_dir / "outputLua"
        self.output_images_dir = self.base_dir / "outputImages"
        
        # Create output directories if they don't exist
        self.output_lua_dir.mkdir(exist_ok=True)
        self.output_images_dir.mkdir(exist_ok=True)
        
        # Load building configuration
        self.buildings_config = self.load_buildings_config()
    
    def find_latest_download(self) -> Path:
        """Find the most recent download folder."""
        download_folders = []
        
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.startswith("Download "):
                download_folders.append(item)
        
        if not download_folders:
            raise FileNotFoundError("No download folders found starting with 'Download '")
        
        download_folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest = download_folders[0]
        print(f"Using latest download folder: {latest.name}")
        return latest
    
    def load_buildings_config(self) -> Dict[str, Any]:
        """Load comprehensive building configuration from YAML file."""
        config_file = self.detail_data_dir / "buildings_config.yaml"
        
        if not config_file.exists():
            print(f"Warning: Buildings config file not found: {config_file}")
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data
        except Exception as e:
            print(f"Error loading buildings config: {e}")
            return {}
    
    def parse_building_yaml(self, yaml_file: str) -> Dict[str, Any]:
        """Parse a building YAML file."""
        building_file = self.buildings_dir / yaml_file
        
        if not building_file.exists():
            print(f"Warning: Building file not found: {building_file}")
            return {}
        
        try:
            with open(building_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data
        except Exception as e:
            print(f"Error parsing building YAML for {yaml_file}: {e}")
            return {}
    
    def find_and_copy_building_image(self, building_key: str, image_pattern: str, 
                                     location: str = None, custom_filename: str = None) -> str:
        """Find and copy building image to output directory."""
        if not image_pattern:
            return None
        
        # Determine search path based on location
        if location and location.endswith('_outpost'):
            outpost_key = location.replace('_outpost', '')
            search_path = self.images_dir / "buildings" / "outposts" / outpost_key
        else:
            # City/field buildings - search in buildings folder
            search_path = self.images_dir / "buildings"
        
        if not search_path.exists():
            print(f"    Image folder not found: {search_path}")
            return None
        
        # Look for the image file
        image_file = search_path / image_pattern
        
        if not image_file.exists():
            print(f"    Image file not found: {image_file}")
            return None
        
        # Use custom filename if provided, otherwise clean up the pattern
        if custom_filename:
            output_filename = custom_filename
        else:
            output_filename = image_pattern
            # Don't strip numbers for outpost_home files (these are variations)
            if 'outpost_home' not in output_filename:
                output_filename = output_filename.replace('_default_1', '')
                output_filename = output_filename.replace('_default_2', '')
                output_filename = output_filename.replace('_default_3', '')
                output_filename = output_filename.replace('_default_4', '')
                output_filename = output_filename.replace('_default_5', '')
        
        # Copy image to buildings subfolder in output directory
        buildings_output_dir = self.output_images_dir / "buildings"
        buildings_output_dir.mkdir(parents=True, exist_ok=True)
        output_path = buildings_output_dir / output_filename
        
        try:
            shutil.copy2(image_file, output_path)
            print(f"    Copied image: buildings/{output_filename}")
            return output_filename
        except Exception as e:
            print(f"    Error copying image: {e}")
            return None
    
    def convert_yaml_to_lua(self, building_key: str, building_config: Dict[str, Any], 
                           yaml_data: Dict[str, Any]) -> str:
        """Convert YAML building data to Lua format matching reference file."""
        building_name = building_key
        building_id = building_config.get('id', 1)
        first_levelup = building_config.get('first_levelup', 1)
        location = building_config.get('location', 'city')
        description = building_config.get('description', '')
        image_pattern = building_config.get('image_pattern', '')
        
        max_level = yaml_data.get('max_level', 10)
        
        # Handle image_override
        image_line = ""
        # Hardcode Dragon Keep image
        if building_key == 'dragon_keep':
            image_line = '\t\timage_override = "Dragon keep zolmec.webp",\n'
        elif image_pattern:
            copied_image = self.find_and_copy_building_image(building_key, image_pattern, location)
            if copied_image:
                image_line = f'\t\timage_override = "{copied_image}",\n'
        
        # Extract requirements - handle both nested and flat structures
        requirements = yaml_data.get('requirements', {})
        location_requirements = requirements.get(location, {})
        
        # If no requirements found for location, try direct level keys or 'city' fallback
        if not location_requirements:
            # Check if requirements are directly level keys (like fountain_of_life)
            # Keys might be integers or strings
            has_level_keys = any(str(i) in requirements or i in requirements for i in range(1, 11))
            if has_level_keys:
                location_requirements = requirements
            # For field buildings, try 'city' as fallback
            elif location == 'field' and 'city' in requirements:
                location_requirements = requirements['city']
        
        # Build requirements table
        requirements_lua = "\t\trequirements = {\n"
        for level in range(1, max_level + 1):
            # Check both string and integer keys
            level_data = location_requirements.get(str(level)) or location_requirements.get(level)
            if level_data:
                resources = level_data.get('resources', {})
                duration = level_data.get('duration', 0)
                items = level_data.get('items', {})
                
                req_line = f"\t\t\t[{level}] = {{"
                resource_parts = []
                
                if 'food' in resources:
                    resource_parts.append(f"food = {resources['food']}")
                if 'lumber' in resources:
                    resource_parts.append(f"lumber = {resources['lumber']}")
                if 'stone' in resources:
                    resource_parts.append(f"stone = {resources['stone']}")
                if 'metal' in resources:
                    resource_parts.append(f"metal = {resources['metal']}")
                if 'gold' in resources:
                    resource_parts.append(f"gold = {resources['gold']}")
                if 'population' in resources:
                    resource_parts.append(f"population = {resources['population']}")
                
                if resource_parts:
                    req_line += ", ".join(resource_parts)
                
                # Format build_time - use multiplication format for consistency
                if duration > 0:
                    req_line += f", build_time = {duration}"
                
                if items:
                    item_parts = []
                    for item, count in items.items():
                        item_parts.append(f'["{item}"] = {count}')
                    req_line += f", items = {{{', '.join(item_parts)}}}"
                
                req_line += "},\n"
                requirements_lua += req_line
            else:
                requirements_lua += f"\t\t\t[{level}] = {{}},\n"
        
        requirements_lua += "\t\t},"
        
        # Extract rewards/unlocks (rewards may be nested under location)
        rewards = yaml_data.get('rewards', {})
        
        # Check if rewards are location-specific
        location_rewards = rewards.get(location, {})
        
        unlocks_lua = "\t\tunlocks = {\n"
        for level in range(1, max_level + 1):
            # Check both string and integer keys, first in location-specific rewards, then in general rewards
            level_data = location_rewards.get(str(level)) or location_rewards.get(level) or rewards.get(str(level)) or rewards.get(level)
            if level_data:
                unlock_parts = []
                
                if 'power' in level_data:
                    unlock_parts.append(f"power = {level_data['power']}")
                if 'resistance' in level_data:
                    unlock_parts.append(f"resistance = {level_data['resistance']}")
                if 'happiness' in level_data:
                    unlock_parts.append(f"happiness = {level_data['happiness']}")
                if 'population' in level_data:
                    unlock_parts.append(f"population = {level_data['population']}")
                if 'generates' in level_data:
                    unlock_parts.append(f"generates = {level_data['generates']}")
                if 'storage' in level_data:
                    unlock_parts.append(f"storage = {level_data['storage']}")
                if 'troops' in level_data:
                    troops_list = level_data['troops']
                    if troops_list:
                        troops_str = ', '.join([f'"{t}"' for t in troops_list])
                        unlock_parts.append(f"troops = {{{troops_str}}}")
                
                if unlock_parts:
                    unlocks_lua += f"\t\t\t[{level}] = {{{', '.join(unlock_parts)}}},\n"
                else:
                    unlocks_lua += f"\t\t\t[{level}] = {{}},\n"
            else:
                unlocks_lua += f"\t\t\t[{level}] = {{}},\n"
        
        # Only add comma if there will be a generations field after
        if 'generations' in yaml_data and yaml_data['generations']:
            unlocks_lua += "\t\t},"
        else:
            unlocks_lua += "\t\t}"
        
        # Extract generations for field buildings (generations is not nested under location)
        generations_lua = ""
        if 'generations' in yaml_data:
            generations = yaml_data['generations']
            if generations:
                generations_lua = "\t\tgenerations = {\n"
                
                for level in range(1, max_level + 1):
                    # Check both string and integer keys
                    level_data = generations.get(str(level)) or generations.get(level)
                    if level_data:
                        gen_resources = level_data.get('resources', {})
                        capacity = level_data.get('capacity', 0)
                        
                        gen_line = f"\t\t\t[{level}] = {{"
                        resource_parts = []
                        
                        for resource, amount in gen_resources.items():
                            resource_parts.append(f"{resource} = {amount}")
                        
                        if resource_parts:
                            gen_line += ", ".join(resource_parts) + f", capacity = {capacity}}},\n"
                        else:
                            gen_line += f"capacity = {capacity}}},\n"
                        generations_lua += gen_line
                
                generations_lua += "\t\t},"
        
        # Build complete Lua entry matching reference format
        # Quote name if it contains spaces
        if ' ' in building_name:
            lua_entry = f"""\t["{building_name}"] = {{
\t\tid = {building_id},
\t\tfirst_levelup = {first_levelup},
\t\tmax_level = {max_level},
\t\tlocation = "{location}",
\t\tdescription = "{description}",
{image_line}
{requirements_lua}
{unlocks_lua}
{generations_lua}
\t}},"""
        else:
            lua_entry = f"""\t{building_name} = {{
\t\tid = {building_id},
\t\tfirst_levelup = {first_levelup},
\t\tmax_level = {max_level},
\t\tlocation = "{location}",
\t\tdescription = "{description}",
{image_line}
{requirements_lua}
{unlocks_lua}
{generations_lua}
\t}},"""
        
        return lua_entry
    
    def convert_outpost_building_to_lua(self, outpost_key: str, building_type: str, 
                                       yaml_data: Dict[str, Any], building_id: int) -> str:
        """Convert outpost building YAML to Lua format."""
        outposts = self.buildings_config.get('outposts', {})
        outpost_config = outposts[outpost_key]
        location = outpost_config['location']
        max_level = yaml_data.get('max_level', 10)
        resource_item = outpost_config['resource_item']
        
        # Determine building name and description
        building_names = outpost_config.get('building_names', {})
        building_descriptions = outpost_config.get('building_descriptions', {})
        if building_type == 'factory':
            building_name = building_names.get('factory', f"{outpost_key}_factory")
            description = building_descriptions.get('factory', f"Generates {resource_item}.")
        elif building_type == 'cache':
            # Use resource_item name for cache (e.g., fangtooth_respirator instead of water_cache)
            resource_key = outpost_config['resource_key']
            building_name = building_names.get('cache', f"{resource_key}_cache")
            description = building_descriptions.get('cache', f"Stores {resource_item}.")
        else:
            building_name = building_names.get('garrison', f"{outpost_key}_{building_type}")
            description = building_descriptions.get('garrison', f"{outpost_config['name']} building.")
        
        # Handle image override from config
        image_line = ""
        building_images = outpost_config.get('building_images', {})
        building_image = building_images.get(building_type)
        if building_image:
            image_line = f'\t\timage_override = "{building_image}",\n'
        else:
            # Fallback to image patterns for copying
            image_patterns = outpost_config.get('image_patterns', {})
            image_pattern = image_patterns.get(building_type, '')
            if image_pattern:
                copied_image = self.find_and_copy_building_image(building_name, image_pattern, location)
                if copied_image:
                    image_line = f'\t\timage_override = "{copied_image}",\n'
        
        # Extract requirements (outpost YAMLs use different keys: outpost:, water:, stone:, fire:)
        requirements = yaml_data.get('requirements', {})
        # Try multiple possible keys in order of preference
        location_requirements = requirements.get(outpost_key, {})
        if not location_requirements:
            location_requirements = requirements.get('outpost', {})
        if not location_requirements:
            location_requirements = requirements.get(location, {})
        
        # Build requirements table
        requirements_lua = "\t\trequirements = {\n"
        for level in range(1, max_level + 1):
            # Check both string and integer keys
            level_data = location_requirements.get(str(level)) or location_requirements.get(level)
            if level_data:
                resources = level_data.get('resources', {})
                duration = level_data.get('duration', 0)
                items = level_data.get('items', {})
                
                req_line = f"\t\t\t[{level}] = {{"
                resource_parts = []
                
                if 'food' in resources:
                    resource_parts.append(f"food = {resources['food']}")
                if 'lumber' in resources:
                    resource_parts.append(f"lumber = {resources['lumber']}")
                if 'stone' in resources:
                    resource_parts.append(f"stone = {resources['stone']}")
                if 'metal' in resources:
                    resource_parts.append(f"metal = {resources['metal']}")
                if 'gold' in resources:
                    resource_parts.append(f"gold = {resources['gold']}")
                
                if resource_parts:
                    req_line += ", ".join(resource_parts)
                
                if duration > 0:
                    req_line += f", build_time = {duration}"
                
                if items:
                    item_parts = []
                    for item, count in items.items():
                        item_parts.append(f'["{item}"] = {count}')
                    req_line += f", items = {{{', '.join(item_parts)}}}"
                
                req_line += "},\n"
                requirements_lua += req_line
            else:
                requirements_lua += f"\t\t\t[{level}] = {{}},\n"
        
        requirements_lua += "\t\t},"
        
        # Extract rewards/unlocks (rewards is not nested under location)
        rewards = yaml_data.get('rewards', {})
        
        unlocks_lua = "\t\tunlocks = {\n"
        for level in range(1, max_level + 1):
            # Check both string and integer keys
            level_data = rewards.get(str(level)) or rewards.get(level)
            if level_data:
                power = level_data.get('power', 0)
                unlocks_lua += f"\t\t\t[{level}] = {{power = {power}}},\n"
            else:
                unlocks_lua += f"\t\t\t[{level}] = {{}},\n"
        
        # Only add comma if there will be a generations field after
        if 'generations' in yaml_data and yaml_data['generations']:
            unlocks_lua += "\t\t},"
        else:
            unlocks_lua += "\t\t}"
        
        # Extract generations for factory/cache (generations is not nested under location)
        generations_lua = ""
        if 'generations' in yaml_data:
            generations = yaml_data['generations']
            if generations:
                generations_lua = "\t\tgenerations = {\n"
                
                for level in range(1, max_level + 1):
                    # Check both string and integer keys
                    level_data = generations.get(str(level)) or generations.get(level)
                    if level_data:
                        gen_resources = level_data.get('resources', {})
                        capacity = level_data.get('capacity', 0)
                        
                        gen_line = f"\t\t\t[{level}] = {{"
                        resource_parts = []
                        
                        for resource, amount in gen_resources.items():
                            resource_parts.append(f"{resource} = {amount}")
                        
                        if resource_parts:
                            gen_line += ", ".join(resource_parts) + f", capacity = {capacity}}},\n"
                        else:
                            gen_line += f"capacity = {capacity}}},\n"
                        generations_lua += gen_line
                
                generations_lua += "\t\t},"

        # Build complete Lua entry - quote name if it contains spaces
        if ' ' in building_name:
            lua_entry = f"""\t["{building_name}"] = {{
\t\tid = {building_id},
\t\tfirst_levelup = 1,
\t\tmax_level = {max_level},
\t\tlocation = "{location}",
\t\tdescription = "{description}",
{image_line}
{requirements_lua}
{unlocks_lua}
{generations_lua}
\t}},"""
        else:
            lua_entry = f"""\t{building_name} = {{
\t\tid = {building_id},
\t\tfirst_levelup = 1,
\t\tmax_level = {max_level},
\t\tlocation = "{location}",
\t\tdescription = "{description}",
{image_line}
{requirements_lua}
{unlocks_lua}
{generations_lua}
\t}},"""

        return lua_entry
    
    def convert_outpost_garrison_to_lua(self, outpost_key: str, garrison_yaml: Dict[str, Any], 
                                        building_id: int) -> str:
        """Convert shared garrison YAML to outpost-specific Lua format."""
        outposts = self.buildings_config.get('outposts', {})
        outpost_config = outposts[outpost_key]
        location = outpost_config['location']
        max_level = garrison_yaml.get('max_level', 10)
        building_names = outpost_config.get('building_names', {})
        building_name = building_names.get('garrison', f"garrison_{location}")
        description = f"Where troops are trained, unlocks [[{outpost_config['troop']}]] training at level 10."
        
        # Handle image override from config
        image_line = ""
        garrison_image = outpost_config.get('garrison_image')
        if garrison_image:
            # Use garrison_[outpost_type].webp format to match variations
            outpost_prefix = outpost_key.replace('_outpost', '')
            garrison_image = f"garrison_{outpost_prefix}.webp"
            image_line = f'\t\timage_override = "{garrison_image}",\n'
        
        # Handle garrison variations if present
        variations_line = ""
        garrison_variations = outpost_config.get('garrison_variations', [])
        if garrison_variations:
            copied_variations = []
            for var_pattern in garrison_variations:
                # Use garrison_[outpost_type] format for variation names
                outpost_prefix = outpost_key.replace('_outpost', '')
                var_filename = f"garrison_{outpost_prefix}.webp"
                copied_var = self.find_and_copy_building_image(building_name, var_pattern, location, var_filename)
                if copied_var:
                    copied_variations.append(f'"{copied_var}"')
            if copied_variations:
                variations_line = f"\t\tvariations = {{{', '.join(copied_variations)}}}"
        
        # Extract outpost-specific requirements
        requirements = garrison_yaml.get('requirements', {})
        outpost_requirements = requirements.get('outpost', {})
        
        # Build requirements table
        requirements_lua = "\t\trequirements = {\n"
        for level in range(1, max_level + 1):
            # Check both string and integer keys
            level_data = outpost_requirements.get(str(level)) or outpost_requirements.get(level)
            if level_data:
                resources = level_data.get('resources', {})
                duration = level_data.get('duration', 0)
                items = level_data.get('items', {})
                
                req_line = f"\t\t\t[{level}] = {{"
                resource_parts = []
                
                if 'food' in resources:
                    resource_parts.append(f"food = {resources['food']}")
                if 'lumber' in resources:
                    resource_parts.append(f"lumber = {resources['lumber']}")
                if 'stone' in resources:
                    resource_parts.append(f"stone = {resources['stone']}")
                if 'metal' in resources:
                    resource_parts.append(f"metal = {resources['metal']}")
                if 'gold' in resources:
                    resource_parts.append(f"gold = {resources['gold']}")
                
                if resource_parts:
                    req_line += ", ".join(resource_parts)
                
                if duration > 0:
                    req_line += f", build_time = {duration}"
                
                if items:
                    item_parts = []
                    for item, count in items.items():
                        item_parts.append(f'["{item}"] = {count}')
                    req_line += f", items = {{{', '.join(item_parts)}}}"
                
                req_line += "},\n"
                requirements_lua += req_line
            else:
                requirements_lua += f"\t\t\t[{level}] = {{}},\n"
        
        requirements_lua += "\t\t},"
        
        # Extract outpost-specific rewards
        rewards = garrison_yaml.get('rewards', {})
        outpost_rewards = rewards.get('outpost', {})
        
        unlocks_lua = "\t\tunlocks = {\n"
        for level in range(1, max_level + 1):
            # Check both string and integer keys
            level_data = outpost_rewards.get(str(level)) or outpost_rewards.get(level)
            if level_data:
                power = level_data.get('power', 0)
                
                if level == 10:
                    unlocks_lua += f"\t\t\t[{level}] = {{power = {power}, troops = {{\"[[{outpost_config['troop']}]]\"}}}},\n"
                else:
                    unlocks_lua += f"\t\t\t[{level}] = {{power = {power}}},\n"
            else:
                unlocks_lua += f"\t\t\t[{level}] = {{}},\n"
        
        unlocks_lua += "\t\t},"
        
        # Build complete Lua entry - quote name if it contains spaces
        if ' ' in building_name:
            lua_entry = f"""\t["{building_name}"] = {{
\t\tid = {building_id},
\t\tfirst_levelup = 1,
\t\tmax_level = {max_level},
\t\tlocation = "{location}",
\t\tdescription = "{description}",
{image_line}
{requirements_lua}
{unlocks_lua}
{variations_line}
\t}},"""
        else:
            lua_entry = f"""\t{building_name} = {{
\t\tid = {building_id},
\t\tfirst_levelup = 1,
\t\tmax_level = {max_level},
\t\tlocation = "{location}",
\t\tdescription = "{description}",
{image_line}
{requirements_lua}
{unlocks_lua}
{variations_line}
\t}},"""
        
        return lua_entry
    
    def generate_lua_file(self, all_buildings: List[str]) -> str:
        """Generate complete Lua Module-BuildingsData file matching reference format."""
        lua_content = "local buildings = {\n"
        
        # Add all buildings in order
        for building_entry in all_buildings:
            lua_content += building_entry + "\n"
        
        lua_content += "}\nreturn buildings"
        
        return lua_content
    
    def process_all_buildings(self):
        """Process all buildings (city, field, and outpost) and generate Lua data."""
        print("Processing buildings...")
        print(f"Buildings source: {self.buildings_dir}")
        print(f"Images source: {self.images_dir}")
        print(f"Output Lua: {self.output_lua_dir}")
        print(f"Output images: {self.output_images_dir}")
        print("-" * 50)
        
        all_buildings = []
        
        # Collect outpost variations to add to home and garrison later
        outpost_home_variations = []
        outpost_garrison_variations = []
        
        # Process city and field buildings from config
        buildings = self.buildings_config.get('buildings', {})
        for building_key, building_config in buildings.items():
            print(f"\nProcessing {building_key}...")
            
            yaml_file = building_config.get('yaml_file', '')
            if not yaml_file:
                print(f"  Skipping - no YAML file specified")
                continue
            
            yaml_data = self.parse_building_yaml(yaml_file)
            if not yaml_data:
                print(f"  Skipping - no YAML data")
                continue
            
            lua_entry = self.convert_yaml_to_lua(building_key, building_config, yaml_data)
            all_buildings.append(lua_entry)
            print(f"  Generated Lua entry for {building_key}")
        
        # Process outpost buildings
        outposts = self.buildings_config.get('outposts', {})
        shared_buildings = self.buildings_config.get('shared_buildings', {})
        
        # Load shared garrison data
        garrison_yaml = None
        if 'garrison' in shared_buildings:
            garrison_yaml = self.parse_building_yaml(shared_buildings['garrison'])
        
        # Get next available ID (starting from 20 since we have 19 buildings in config)
        next_id = 20
        
        for outpost_key, outpost_config in outposts.items():
            print(f"\nProcessing {outpost_key} outpost...")
            
            building_files = outpost_config.get('building_files', {})
            building_order = outpost_config.get('building_order', list(building_files.keys()))
            
            for building_type in building_order:
                if building_type == 'garrison':
                    # Generate garrison for this outpost if shared garrison data exists
                    if garrison_yaml:
                        print(f"  Processing garrison for {outpost_key} outpost...")
                        
                        # Collect garrison variations for main garrison entry
                        garrison_variations = outpost_config.get('garrison_variations', [])
                        if garrison_variations:
                            outpost_prefix = outpost_key.replace('_outpost', '')
                            for var_pattern in garrison_variations:
                                var_filename = f"garrison_{outpost_prefix}.webp"
                                outpost_garrison_variations.append(f'"{var_filename}"')
                        
                        lua_entry = self.convert_outpost_garrison_to_lua(
                            outpost_key, garrison_yaml, next_id
                        )
                        all_buildings.append(lua_entry)
                        next_id += 1
                        print(f"    Generated Lua entry for garrison")
                elif building_type in building_files:
                    yaml_file = building_files[building_type]
                    print(f"  Processing {building_type} from {yaml_file}...")
                    
                    yaml_data = self.parse_building_yaml(yaml_file)
                    if not yaml_data:
                        print(f"    Skipping {building_type} - no YAML data")
                        continue
                    
                    # Collect home variations for main home entry (only from factory)
                    if building_type == 'factory':
                        variations = outpost_config.get('variations', [])
                        if variations:
                            outpost_prefix = outpost_key.replace('_outpost', '')
                            for var_pattern in variations:
                                var_filename = f"{outpost_prefix}_{var_pattern}"
                                outpost_home_variations.append(f'"{var_filename}"')
                    
                    lua_entry = self.convert_outpost_building_to_lua(
                        outpost_key, building_type, yaml_data, next_id
                    )
                    all_buildings.append(lua_entry)
                    next_id += 1
                    print(f"    Generated Lua entry for {building_type}")
        
        # Add outpost variations to main home and garrison entries
        if outpost_home_variations:
            # Find and modify the home entry
            for i, entry in enumerate(all_buildings):
                if 'home = {' in entry or '["Home"] = {' in entry:
                    # Add variations line before the closing brace
                    variations_line = f'\t\tvariations = {{{", ".join(outpost_home_variations)}}}\n'
                    # Find the last occurrence of }, and insert before it
                    last_brace_idx = entry.rfind('\t},')
                    if last_brace_idx != -1:
                        # Trim whitespace before the brace
                        trimmed = entry[:last_brace_idx].rstrip()
                        # Check if last character is already a comma
                        if trimmed.endswith(','):
                            # Already has comma, just add variations
                            all_buildings[i] = trimmed + '\n' + variations_line + entry[last_brace_idx:]
                        else:
                            # Add comma and variations
                            all_buildings[i] = trimmed + ',\n' + variations_line + entry[last_brace_idx:]
                    break
        
        if outpost_garrison_variations:
            # Find and modify the garrison entry
            for i, entry in enumerate(all_buildings):
                if 'garrison = {' in entry or '["Garrison"] = {' in entry:
                    # Add variations line before the closing brace
                    variations_line = f'\t\tvariations = {{{", ".join(outpost_garrison_variations)}}}\n'
                    # Find the last occurrence of }, and insert before it
                    last_brace_idx = entry.rfind('\t},')
                    if last_brace_idx != -1:
                        # Trim whitespace before the brace
                        trimmed = entry[:last_brace_idx].rstrip()
                        # Check if last character is already a comma
                        if trimmed.endswith(','):
                            # Already has comma, just add variations
                            all_buildings[i] = trimmed + '\n' + variations_line + entry[last_brace_idx:]
                        else:
                            # Add comma and variations
                            all_buildings[i] = trimmed + ',\n' + variations_line + entry[last_brace_idx:]
                    break
        
        # Generate and write Lua file
        if all_buildings:
            lua_content = self.generate_lua_file(all_buildings)
            # Create Buildings subdirectory if it doesn't exist
            buildings_dir = self.output_lua_dir / "Buildings"
            buildings_dir.mkdir(parents=True, exist_ok=True)
            lua_output_path = buildings_dir / "data.lua"
            
            try:
                with open(lua_output_path, 'w', encoding='utf-8') as f:
                    f.write(lua_content)
                print(f"\nLua file written to: {lua_output_path}")
                print(f"Total buildings processed: {len(all_buildings)}")
            except Exception as e:
                print(f"Error writing Lua file: {e}")
        else:
            print("\nNo building entries generated")


def main():
    base_dir = r"C:\Users\josem\PycharmProjects\RoADashboard\Parsing Tools\GGWiki"
    
    processor = BuildingsProcessor(base_dir)
    processor.process_all_buildings()


if __name__ == "__main__":
    main()
