-- Pandoc filter: a Markdown block marked {.glance} becomes a coloured box in the PDF
function Div(el)
  if el.classes:includes("glance") then
    local blocks = { pandoc.RawBlock("latex", "\\begin{glancebox}") }
    for _, block in ipairs(el.content) do
      table.insert(blocks, block)
    end
    table.insert(blocks, pandoc.RawBlock("latex", "\\end{glancebox}"))
    return blocks
  end
end
