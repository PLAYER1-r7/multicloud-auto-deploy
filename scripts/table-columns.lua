-- Pandoc Lua filter to convert table column alignments to paragraph columns
-- This forces text wrapping in LaTeX tables by converting l/c/r to p{width}
-- Now supports dynamic column width based on table headers

function Table(tbl)
  -- Calculate column widths based on number of columns
  local ncols = #tbl.colspecs
  if ncols == 0 then
    return tbl
  end
  
  -- Try to detect table type by examining header content
  local widths = {}
  local header_text = ""
  
  -- Extract header text if available
  if tbl.head and tbl.head.rows and #tbl.head.rows > 0 then
    local first_row = tbl.head.rows[1]
    if first_row.cells then
      for _, cell in ipairs(first_row.cells) do
        if cell.contents and #cell.contents > 0 then
          for _, block in ipairs(cell.contents) do
            if block.t == "Plain" or block.t == "Para" then
              for _, inline in ipairs(block.content) do
                if inline.t == "Str" then
                  header_text = header_text .. inline.text .. " "
                end
              end
            end
          end
        end
      end
    end
  end
  
  -- Determine column widths based on header content and column count
  if ncols == 4 then
    -- Check if it's a resource table (リソース | 名前 | 目的 | リージョン)
    if header_text:match("リソース") and header_text:match("名前") and header_text:match("目的") then
      -- Resource tables need extra space for long names like 'ashnova-multicloud-auto-deploy-staging-frontend'
      widths = {0.14, 0.43, 0.27, 0.16}
    else
      -- Equal distribution for other 4-column tables
      local col_width = 0.9 / ncols
      for i = 1, ncols do
        widths[i] = col_width
      end
    end
  elseif ncols == 3 then
    -- Check if it's a Secret table (Secret名 | 説明 | 取得方法)
    if header_text:match("Secret") and header_text:match("説明") then
      -- Secret tables: Give more space to description column
      widths = {0.25, 0.50, 0.25}
    else
      -- Equal distribution for other 3-column tables (技術 | バージョン | 用途)
      local col_width = 0.9 / ncols
      for i = 1, ncols do
        widths[i] = col_width
      end
    end
  else
    -- Equal distribution for all other tables
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
