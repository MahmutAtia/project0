# --- YAML Formatting Rules ---
# 1.  **Quoting:**
#     -   For all single-line string values, use double quotes (""). Example: `city: "New York"`
#     -   If a single-line string value itself contains a double quote ("), use single quotes ('') to wrap it. Example: `name: 'His name is "John"'`
#     -   For all multi-line strings (like `description` or `about_candidate`), use the literal block scalar (`|`).
#
# 2.  **No Escaping:**
#     -   **Crucial:** Do NOT escape any characters. Do not add backslashes (`\`). YAML handles special characters like `:`, `'`, and `"` correctly when the right quoting style is used.
#
# 3.  **Structure:**
#     -   Strictly follow the indentation and structure of the provided YAML template.
#     -   Do not output any YAML comments (`#`).
#     -   Ensure all keys and values are on the same line unless using a block scalar (`|`).