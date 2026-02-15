-- Pandoc Lua filter to dynamically calculate table column widths
-- Based on actual cell content length for optimal text distribution

-- Helper function to calculate text length from cell content
local function calculate_cell_length(cell)
  local length = 0
  if cell.contents then
    for _, block in ipairs(cell.contents) do
      if block.t == "Plain" or block.t == "Para" then
        for _, inline in ipairs(block.content) do
          if inline.t == "Str" then
            length = length + #inline.text
          elseif inline.t == "Space" then
            length = length + 1
          elseif inline.t == "Code" then
            length = length + #inline.text
          end
        end
      end
    end
  end
  return length
end

-- Main function to process tables
function Table(tbl)
  local ncols = #tbl.colspecs
  if ncols == 0 then
    return tbl
  end
  
  -- Initialize column max lengths
  local col_max_lengths = {}
  for i = 1, ncols do
    col_max_lengths[i] = 0
  end
  
  -- Scan header rows
  if tbl.head and tbl.head.rows then
    for _, row in ipairs(tbl.head.rows) do
      if row.cells then
        for col_idx, cell in ipairs(row.cells) do
          if col_idx <= ncols then
            local len = calculate_cell_length(cell)
            if len > col_max_lengths[col_idx] then
              col_max_lengths[col_idx] = len
            end
          end
        end
      end
    end
  end
  
  -- Scan body rows
  if tbl.bodies then
    for _, body in ipairs(tbl.bodies) do
      if body.body then
        for _, row in ipairs(body.body) do
          if row.cells then
            for col_idx, cell in ipairs(row.cells) do
              if col_idx <= ncols then
                local len = calculate_cell_length(cell)
                if len > col_max_lengths[col_idx] then
                  col_max_lengths[col_idx] = len
                end
              end
            end
          end
        end
      end
    end
  end
  
  -- Calculate total length
  local total_length = 0
  for i = 1, ncols do
    total_length = total_length + col_max_lengths[i]
  end
  
  -- Avoid division by zero
  if total_length == 0 then
    -- Equal distribution fallback
    local equal_width = 0.9 / ncols
    for i = 1, ncols do
      tbl.colspecs[i] = {pandoc.AlignDefault, equal_width}
    end
    return tbl
  end
  
  -- Calculate proportional widths with constraints
  local widths = {}
  local total_width = 0.9  -- Use 90% of page width
  local min_width = 0.10   -- Minimum 10% per column
  local max_width = 0.50   -- Maximum 50% per column
  
  -- First pass: calculate raw proportions
  for i = 1, ncols do
    local proportion = col_max_lengths[i] / total_length
    local width = proportion * total_width
    
    -- Apply min/max constraints
    if width < min_width then
      width = min_width
    elseif width > max_width then
      width = max_width
    end
    
    widths[i] = width
  end
  
  -- Second pass: normalize to ensure sum is exactly total_width
  local actual_total = 0
  for i = 1, ncols do
    actual_total = actual_total + widths[i]
  end
  
  if actual_total > 0 then
    for i = 1, ncols do
      widths[i] = (widths[i] / actual_total) * total_width
    end
  else
    -- Fallback to equal distribution
    local equal_width = total_width / ncols
    for i = 1, ncols do
      widths[i] = equal_width
    end
  end
  
  -- Apply widths to column specs
  for i, colspec in ipairs(tbl.colspecs) do
    tbl.colspecs[i] = {pandoc.AlignDefault, widths[i]}
  end
  
  return tbl
end
