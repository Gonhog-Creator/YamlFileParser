#!/usr/bin/env python3
"""
Parse loot pool YAML files and generate chest loot Lua data.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Any


class ChestLootGenerator:
    def __init__(self, data_dir: str, output_lua_dir: str):
        self.data_dir = Path(data_dir)
        self.output_lua_dir = Path(output_lua_dir)
        self.loot_pools_dir = self.data_dir / "data" / "data" / "loot_pools"
        self.items_dir = self.data_dir / "data" / "data" / "items"
        
        # Load economy.js for item names
        self.economy_descriptions = self.load_economy_descriptions()
        
        # Storage for chest data
        self.chest_loot_data = {}
        
    def load_economy_descriptions(self) -> Dict[str, str]:
        """Load item names from economy.js."""
        economy_file = self.data_dir / "economy.js"
        if not economy_file.exists():
            print(f"Warning: economy.js not found at {economy_file}")
            return {}
        
        import re
        descriptions = {}
        
        with open(economy_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract names from the names object
        names_pattern = r'names:\s*\{([^}]+)\}'
        names_match = re.search(names_pattern, content, re.DOTALL)
        if names_match:
            names_content = names_match.group(1)
            # Match key: "value" pairs
            for match in re.finditer(r'(\w+):\s*"([^"]+)"', names_content):
                item_id = match.group(1)
                item_name = match.group(2)
                descriptions[item_id] = item_name
        
        print(f"Loaded {len(descriptions)} item names from economy.js")
        return descriptions
    
    def get_item_name(self, item_id: str) -> str:
        """Get display name for an item ID."""
        # Try economy.js first
        if item_id in self.economy_descriptions:
            return self.economy_descriptions[item_id]
        
        # Fallback to formatted ID
        return item_id.replace('_', ' ').title()
    
    def parse_loot_pool(self, loot_pool_file: Path) -> Dict[str, Any]:
        """Parse a single loot pool YAML file."""
        with open(loot_pool_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return data
    
    def find_chest_items(self) -> Dict[str, str]:
        """Find all chest items and their associated loot pools or fixed loot."""
        chest_data = {}  # Changed to store more info than just pool_id
        
        if not self.items_dir.exists():
            print(f"Warning: Items directory not found at {self.items_dir}")
            return chest_data
        
        for item_file in self.items_dir.glob("*.yaml"):
            with open(item_file, 'r', encoding='utf-8') as f:
                item_data = yaml.safe_load(f)
            
            # Check if this is a chest with any loot effect
            if 'effects' in item_data:
                loot_effects = []
                for effect in item_data['effects']:
                    effect_name = effect.get('name')
                    
                    if effect_name == 'roll_loot_pool':
                        pool_id = effect.get('pool_id')
                        if pool_id:
                            chest_data[item_data['id']] = {
                                'type': 'loot_pool',
                                'pool_id': pool_id
                            }
                            break  # Only process first loot pool effect
                    
                    elif effect_name in ['give_item', 'give_random_item']:
                        # Collect all give_item/give_random_item effects
                        loot_effects.append({
                            'effect': effect_name,
                            'effect_data': effect
                        })
                
                # If we found give_item effects but no loot pool, store them
                if loot_effects and item_data['id'] not in chest_data:
                    chest_data[item_data['id']] = {
                        'type': 'fixed_loot',
                        'effects': loot_effects
                    }
        
        print(f"Found {len(chest_data)} chest items with loot data")
        return chest_data
    
    def process_all_loot_pools(self):
        """Process all loot pool files and build chest loot data."""
        if not self.loot_pools_dir.exists():
            print(f"Warning: Loot pools directory not found at {self.loot_pools_dir}")
            return
        
        # Find chest items and their loot data
        chest_data = self.find_chest_items()
        
        # Load all loot pools
        loot_pools = {}
        for loot_pool_file in self.loot_pools_dir.glob("*.yaml"):
            pool_data = self.parse_loot_pool(loot_pool_file)
            pool_id = pool_data['id']
            loot_pools[pool_id] = pool_data
        
        print(f"Loaded {len(loot_pools)} loot pools")
        
        # Build chest loot data
        for chest_id, chest_info in chest_data.items():
            chest_name = self.get_item_name(chest_id)
            
            if chest_info['type'] == 'loot_pool':
                # Process loot pool chest
                pool_id = chest_info['pool_id']
                if pool_id in loot_pools:
                    pool_data = loot_pools[pool_id]
                    
                    # Extract rewards
                    rewards = []
                    if 'rewards' in pool_data:
                        for tier_id, tier_data in pool_data['rewards'].items():
                            if 'items' in tier_data:
                                for item in tier_data['items']:
                                    item_id = item.get('id')
                                    amount = item.get('amount', 1)
                                    weight = item.get('weight', 100)
                                    item_name = self.get_item_name(item_id)
                                    
                                    rewards.append({
                                        'id': item_id,
                                        'name': item_name,
                                        'amount': amount,
                                        'weight': weight
                                    })
                    
                    self.chest_loot_data[chest_name] = {
                        'id': chest_id,
                        'pool_id': pool_id,
                        'rewards': rewards
                    }
            
            elif chest_info['type'] == 'fixed_loot':
                # Process fixed loot chest (may have multiple give_item effects)
                effects = chest_info['effects']
                
                rewards = []
                for effect_info in effects:
                    effect_data = effect_info['effect_data']
                    effect_name = effect_info['effect']
                    
                    item_ids = effect_data.get('item_id', [])
                    amount = effect_data.get('default', 1)
                    
                    # Handle both single item_id and list of item_ids
                    if isinstance(item_ids, str):
                        item_ids = [item_ids]
                    
                    for item_id in item_ids:
                        item_name = self.get_item_name(item_id)
                        
                        if effect_name == 'give_random_item':
                            # Random selection - set weight to equal for all
                            rewards.append({
                                'id': item_id,
                                'name': item_name,
                                'amount': amount,
                                'weight': 100
                            })
                        else:
                            # Fixed item - set weight to 1 for 100% chance
                            rewards.append({
                                'id': item_id,
                                'name': item_name,
                                'amount': amount,
                                'weight': 1
                            })
                
                self.chest_loot_data[chest_name] = {
                    'id': chest_id,
                    'pool_id': 'fixed',
                    'rewards': rewards
                }
        
        print(f"Built loot data for {len(self.chest_loot_data)} chests")
    
    def generate_lua_output(self):
        """Generate Lua data file for chest loot."""
        self.output_lua_dir.mkdir(parents=True, exist_ok=True)
        output_file = self.output_lua_dir / "Chests-data"
        
        lua_lines = [
            "-- Module:Chests/data",
            "-- Auto-generated by chests.py",
            "-- Contains loot data for all chests",
            "",
            "local chests = {",
        ]
        
        for chest_name, chest_data in sorted(self.chest_loot_data.items()):
            lua_lines.append(f'    ["{chest_name}"] = {{')
            lua_lines.append(f'        id = "{chest_data["id"]}",')
            lua_lines.append(f'        pool_id = "{chest_data["pool_id"]}",')
            lua_lines.append('        rewards = {')
            
            for reward in chest_data['rewards']:
                lua_lines.append(f'            {{ id = "{reward["id"]}", name = "{reward["name"]}", amount = {reward["amount"]}, weight = {reward["weight"]} }},')
            
            lua_lines.append('        },')
            lua_lines.append('    },')
        
        lua_lines.extend([
            '}',
            '',
            'return chests'
        ])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lua_lines))
        
        print(f"Lua file written to: {output_file}")


def main():
    # Setup paths
    script_dir = Path(__file__).parent
    data_dir = script_dir / "Download 2026-07-03T20-54-29-473Z"
    output_lua_dir = script_dir / "outputLua"
    
    print("Processing chest loot data...")
    print(f"Data source: {data_dir}")
    print(f"Output Lua: {output_lua_dir}")
    print("-" * 50)
    
    generator = ChestLootGenerator(data_dir, output_lua_dir)
    generator.process_all_loot_pools()
    generator.generate_lua_output()
    
    print("-" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
