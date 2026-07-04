--[[
Module:Chests
This module provides functions to display chest loot data.
]]

local p = {}
local chestData = require('Module:Chests/data')

--[[
Get loot data for a specific chest
@param chestName The name of the chest (e.g., "Abyssal Demon Chest")
@return Table containing chest loot data, or nil if not found
]]
function p.getChestData(frame)
    local chestName = frame.args[1] or frame.args.chest
    if not chestName then
        return "Error: No chest name provided"
    end
    
    local data = chestData[chestName]
    if not data then
        return "Error: Chest '" .. chestName .. "' not found in data"
    end
    
    return data
end

--[[
Generate a loot table for a chest
@param chestName The name of the chest
@return Wikitext formatted loot table
]]
function p.lootTable(frame)
    local chestName = frame.args[1] or frame.args.chest
    if not chestName then
        return "Error: No chest name provided"
    end
    
    local data = chestData[chestName]
    if not data then
        return "Error: Chest '" .. chestName .. "' not found in data"
    end
    
    -- Calculate total weight for percentage calculation
    local totalWeight = 0
    for _, reward in ipairs(data.rewards) do
        totalWeight = totalWeight + reward.weight
    end
    
    -- Build table
    local result = {| {| class="wikitable sortable"
        result = result .. "|+ Loot Table for " .. chestName .. "\n"
        result = result .. "! Item !! Amount !! Weight !! Chance\n"
        result = result .. "|-\n"
        
        for _, reward in ipairs(data.rewards) do
            local chance = string.format("%.2f%%", (reward.weight / totalWeight) * 100)
            result = result .. "| [[" .. reward.name .. "]] || " .. reward.amount .. " || " .. reward.weight .. " || " .. chance .. "\n|-\n"
        end
        
        result = result .. "|}\n"
    else
        result = "No rewards found for this chest."
    end
    
    return result
end

--[[
Generate a simple loot list for a chest
@param chestName The name of the chest
@return Wikitext formatted loot list
]]
function p.lootList(frame)
    local chestName = frame.args[1] or frame.args.chest
    if not chestName then
        return "Error: No chest name provided"
    end
    
    local data = chestData[chestName]
    if not data then
        return "Error: Chest '" .. chestName .. "' not found in data"
    end
    
    local result = ""
    
    if data.rewards and #data.rewards > 0 then
        result = result .. ";Possible rewards:\n"
        for _, reward in ipairs(data.rewards) do
            local amountStr = reward.amount > 1 and " x" .. reward.amount or ""
            result = result .. ": [[" .. reward.name .. "]]" .. amountStr .. "\n"
        end
    else
        result = "No rewards found for this chest."
    end
    
    return result
end

--[[
Get chest metadata (ID, pool ID)
@param chestName The name of the chest
@return Wikitext formatted metadata
]]
function p.metadata(frame)
    local chestName = frame.args[1] or frame.args.chest
    if not chestName then
        return "Error: No chest name provided"
    end
    
    local data = chestData[chestName]
    if not data then
        return "Error: Chest '" .. chestName .. "' not found in data"
    end
    
    local result = {| class="wikitable"
        result = result .. "|+ Chest Metadata\n"
        result = result .. "! Property !! Value\n"
        result = result .. "|-\n"
        result = result .. "| Chest ID || " .. data.id .. "\n|-\n"
        result = result .. "| Loot Pool ID || " .. data.pool_id .. "\n|-\n"
        result = result .. "| Number of Rewards || " .. #data.rewards .. "\n"
        result = result .. "|}\n"
    else
        result = "No metadata available."
    end
    
    return result
end

return p
