-- Pandoc Lua filter to convert table column alignments to paragraph columns
-- This forces text wrapping in LaTeX tables by converting l/c/r to p{width}

function Table(tbl)
  -- Calculate column widths based on number of columns
  local ncols = #tbl.colspecs
  if ncols == 0 then
    return tbl
  end
  
  -- Define width distribution based on column count
  -- For 4-column tables (common in our docs), use custom widths
  local widths = {}
  if ncols == 4 then
    -- Typical: Resource, Name, Purpose, Region
    -- Give maximum space to Name column for very long identifiers (up to 47 chars)
    -- 'ashnova-multicloud-auto-deploy-staging-frontend' needs extra space
    -- Region needs 16% for 'ap-northeast-1' (16 chars)
    widths = {0.14, 0.43, 0.27, 0.16}  -- Region:16% to prevent hyphen breaks
  else
    -- Equal distribution for other tables
    local col_width = 0.9 / ncols
    for i = 1, ncols do
      widths[i] = col_width
    end
  end
  
  -- Apply widths to all columns, forcing paragraph alignment
  for i, colspec in ipairs(tbl.colspecs) do
    tbl.colspecs[i] = {pandoc.AlignDefault, widths[i]}
  end
  
  return tbl
end
