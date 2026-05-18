#!/usr/bin/env python3
"""
YAML to Lua Converter

Converts buildings.yaml to proper Lua format for wikibuildingsdata
"""

import yaml
import re

def format_build_time(base_time, level):
    """Format build time using the exponential formula like the original Lua."""
    # Convert seconds to minutes for display
    minutes = base_time // 60
    
    if level == 1:
        return f"{minutes} * 60"
    else:
        return f"{minutes} * 60 * 2^{level - 1}"

def format_resources(resources):
    """Format resources for Lua output."""
    parts = []
    for resource, value in resources.items():
        parts.append(f"{resource} = {value}")
    return ", ".join(parts)

def format_items(items):
    """Format items for Lua output."""
    if not items:
        return ""
    item_parts = []
    for item, count in items.items():
        # Convert snake_case to Title Case for display names
        display_name = item.replace('_', ' ').title()
        item_parts.append(f'["{display_name}"] = {count}')
    return f', items = {{{", ".join(item_parts)}}}'

def generate_lua_requirements(requirements, building_name, target_settlement_type='city'):
    """Generate requirements section for Lua."""
    lua_lines = []
    
    if not requirements:
        return lua_lines
    
    # Only process the target settlement type
    if target_settlement_type in requirements:
        levels = requirements[target_settlement_type]
        if not levels:
            return lua_lines
            
        # Check if levels is a dict with numeric keys (level numbers)
        if isinstance(levels, dict):
            for level, level_data in levels.items():
                if not str(level).isdigit() or not level_data:
                    continue
                    
                level_int = int(level)
                
                # Start the level entry
                line_parts = []
                
                # Add resources if present
                if 'resources' in level_data:
                    resources_str = format_resources(level_data['resources'])
                    line_parts.append(resources_str)
                
                # Add build time if present
                if 'duration' in level_data:
                    base_time = level_data['duration']
                    build_time_str = f"build_time = {format_build_time(base_time, level_int)}"
                    line_parts.append(build_time_str)
                
                # Add items if present
                if 'items' in level_data:
                    items_str = format_items(level_data['items'])
                    if items_str:
                        line_parts.append(items_str[2:])  # Remove ', ' prefix
                
                # Add buildings if present
                if 'buildings' in level_data:
                    buildings_str = ", ".join([f"{building} = {level}" for building, level in level_data['buildings'].items()])
                    line_parts.append(buildings_str)
                
                # Join all parts
                if line_parts:
                    lua_lines.append(f'\t\t\t[{level_int}] = {{{", ".join(line_parts)}}},')
                else:
                    lua_lines.append(f'\t\t\t[{level_int}] = {{}},')
    
    return lua_lines

def generate_lua_unlocks(rewards, building_name, target_settlement_type='city'):
    """Generate unlocks section for Lua."""
    lua_lines = []
    
    if not rewards:
        return lua_lines
    
    # Check if rewards are nested by settlement type or direct level mapping
    has_settlement_types = any(key in ['city', 'outpost'] for key in rewards.keys())
    
    if has_settlement_types:
        # Nested format: rewards -> settlement_type -> level -> data
        if target_settlement_type in rewards:
            levels = rewards[target_settlement_type]
            if not levels:
                return lua_lines
                
            # Direct level mapping
            for level, level_data in levels.items():
                if not str(level).isdigit() or not level_data:
                    continue
                    
                level_int = int(level)
                
                line_parts = []
                
                # Add power if present
                if 'power' in level_data:
                    line_parts.append(f"power = {level_data['power']}")
                
                # Add other reward types
                for key, value in level_data.items():
                    if key != 'power':
                        if isinstance(value, list):
                            # Handle troops arrays
                            if value:
                                troops_str = '", "'.join(str(v) for v in value)
                                line_parts.append(f'troops = {{"{troops_str}"}}')
                            else:
                                line_parts.append('troops = {}')
                        else:
                            line_parts.append(f"{key} = {value}")
                
                # Join all parts
                if line_parts:
                    lua_lines.append(f'\t\t\t[{level_int}] = {{{", ".join(line_parts)}}},')
                else:
                    lua_lines.append(f'\t\t\t[{level_int}] = {{}},')
    else:
        # Direct format: rewards -> level -> data
        for level, level_data in rewards.items():
            if not str(level).isdigit() or not level_data:
                continue
                
            level_int = int(level)
            
            line_parts = []
            
            # Add power if present
            if 'power' in level_data:
                line_parts.append(f"power = {level_data['power']}")
            
            # Add other reward types
            for key, value in level_data.items():
                if key != 'power':
                    if isinstance(value, list):
                        # Handle troops arrays
                        if value:
                            troops_str = '", "'.join(str(v) for v in value)
                            line_parts.append(f'troops = {{"{troops_str}"}}')
                        else:
                            line_parts.append('troops = {}')
                    else:
                        line_parts.append(f"{key} = {value}")
            
            # Join all parts
            if line_parts:
                lua_lines.append(f'\t\t\t[{level_int}] = {{{", ".join(line_parts)}}},')
            else:
                lua_lines.append(f'\t\t\t[{level_int}] = {{}},')
    
    return lua_lines

def get_building_description(building_name):
    """Generate a description for the building based on its name."""
    descriptions = {
        'dragon_keep': 'Houses mighty dragons, unlocks powerful dragon troops and abilities.',
        'fortress': 'The heart of your [[City]], increases the maximum level of your buildings and Wildernesses you can occupy.',
        'wall': 'The last line of defense, helps protect against incoming [[Attacks]].',
        'factory': 'The industrial complex that drives progress, unlocks some troops and ability to research [[Mercantilism]].',
        'garrison': 'Where troops are trained, unlocks troops and ability to research [[Metallurgy]].',
        'home': 'Living space of your citizens, increases population.',
        'metalsmith': 'The forge feeding your factories, unlocks some troops and ability to research [[Metallurgy]].',
        'sentinel': 'Home of Oracles, gives an increasing amount of information about incoming marches.',
        'rookery': 'Houses lesser dragons, unlocks Swift Strike Dragons, Battle Dragons, and ability to research [[Dragonry]].'
    }
    return descriptions.get(building_name, f"The {building_name.replace('_', ' ').title()} building.")

def get_first_levelup(building_name):
    """Determine the first level up requirement for a building."""
    # Based on the original Lua patterns
    if building_name in ['fortress', 'wall']:
        return 2
    else:
        return 1

def get_next_building_id(existing_buildings):
    """Get the next available building ID."""
    # Use predefined building IDs based on the original Lua file
    building_ids = {
        'fortress': 1,
        'wall': 2,
        'factory': 4,
        'garrison': 5,
        'home': 7,
        'metalsmith': 8,
        'sentinel': 11,
        'rookery': 12,
        'dragon_keep': 13
    }
    
    max_id = 0
    for building_name, building_data in existing_buildings.items():
        if building_name in building_ids:
            building_id = building_ids[building_name]
        else:
            building_id = 100 + len(existing_buildings)  # Assign high numbers for new buildings
        
        if building_id > max_id:
            max_id = building_id
    
    return max_id + 1

def get_building_id(building_name, existing_buildings):
    """Get the specific building ID for a building."""
    building_ids = {
        'fortress': 1,
        'wall': 2,
        'factory': 4,
        'garrison': 5,
        'home': 7,
        'metalsmith': 8,
        'sentinel': 11,
        'rookery': 12,
        'dragon_keep': 13
    }
    
    if building_name in building_ids:
        return building_ids[building_name]
    else:
        # Generate a unique ID for new buildings
        return 100 + len(existing_buildings)

def convert_yaml_to_lua(yaml_file, output_file):
    """Convert YAML file to Lua format."""
    
    # Load YAML data
    with open(yaml_file, 'r') as file:
        yaml_data = yaml.safe_load(file)
    
    # Start Lua output
    lua_content = "local buildings = {\n"
    lua_content += "\t--city\n"
    
    # Process each building - only include city buildings
    for building_name, building_data in yaml_data.items():
        # Determine location (use first settlement type)
        settlement_types = building_data.get('settlement_types', ['city'])
        location = settlement_types[0] if settlement_types else 'city'
        
        # Skip outpost buildings for the main city list
        if location == 'outpost':
            continue
        
        # Get building properties
        building_id = get_building_id(building_name, yaml_data)
        max_level = building_data.get('max_level', 10)
        first_levelup = get_first_levelup(building_name)
        
        description = get_building_description(building_name)
        
        # Start building entry
        lua_content += f'\t{building_name} = {{\n'
        lua_content += f'\t\tid = {building_id},\n'
        lua_content += f'\t\tfirst_levelup = {first_levelup},\n'
        lua_content += f'\t\tmax_level = {max_level},\n'
        lua_content += f'\t\tlocation = "{location}",\n'
        lua_content += f'\t\tdescription = "{description}",\n'
        
        # Add requirements (only city requirements for main buildings)
        lua_content += '\t\trequirements = {\n'
        if 'requirements' in building_data:
            requirements_lines = generate_lua_requirements(building_data['requirements'], building_name, 'city')
            lua_content += '\n'.join(requirements_lines)
        lua_content += '\n\t\t},\n'
        
        # Add unlocks (rewards)
        lua_content += '\t\tunlocks = {\n'
        if 'rewards' in building_data:
            unlocks_lines = generate_lua_unlocks(building_data['rewards'], building_name, 'city')
            lua_content += '\n'.join(unlocks_lines)
        lua_content += '\n\t\t}\n'
        
        # End building entry
        lua_content += '\t},\n'
    
    # Close Lua structure
    lua_content += '}\n'
    
    # Write to output file
    with open(output_file, 'w') as file:
        file.write(lua_content)
    
    print(f"Successfully converted {yaml_file} to {output_file}")
    print(f"Generated Lua data for {len(yaml_data)} buildings")

def main():
    """Main conversion function."""
    yaml_file = 'buildings.yaml'
    output_file = 'wikibuildingsdata'
    
    try:
        convert_yaml_to_lua(yaml_file, output_file)
        print(f"Lua file generated: {output_file}")
    except FileNotFoundError:
        print(f"Error: {yaml_file} not found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
