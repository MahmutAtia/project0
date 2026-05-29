#!/bin/bash

# Check if a directory argument was provided
if [ -z "$1" ]; then
    echo "Usage: $0 <path/to/requirements/directory>"
    echo "Example: $0 project0/api"
    exit 1
fi

# Define file paths based on the provided argument ($1)
REQUIREMENTS_DIR="$1"
IN_FILE="${REQUIREMENTS_DIR}/requirements.in"
TXT_FILE="${REQUIREMENTS_DIR}/requirements.txt"

# Check if the files exist
if [ ! -f "$IN_FILE" ] || [ ! -f "$TXT_FILE" ]; then
    echo "ERROR: requirements.in or requirements.txt not found in ${REQUIREMENTS_DIR}"
    exit 1
fi

# 1. Create a temporary file to hold the new, pinned .in content
TEMP_IN_FILE="${IN_FILE}.new"
> "$TEMP_IN_FILE"

echo "Processing $IN_FILE..."

# 2. Loop through each top-level dependency in the original .in file
while IFS= read -r line; do
    # Skip empty lines, comments, and lines that are already pinned
    if [[ -z "$line" || "$line" =~ ^# || "$line" =~ == ]]; then
        echo "$line" >> "$TEMP_IN_FILE"
        continue
    fi

    # Extract the package name (ignoring extras like [server])
    # The sed command handles trimming everything after '['
    PKG_NAME=$(echo "$line" | sed 's/\[.*\]//')
    
    # 3. Search the .txt file for the version chosen for this package
    # The version is usually the first non-comment, non-hash line for the package
    VERSION_LINE=$(grep -E "^${PKG_NAME}==" "$TXT_FILE" | head -n 1)

    if [[ -n "$VERSION_LINE" ]]; then
        # If found, append the full, pinned line to the new .in file
        echo "$VERSION_LINE" >> "$TEMP_IN_FILE"
    else
        # If not found (e.g., package name is different in .txt), keep the original line
        echo "$line" >> "$TEMP_IN_FILE"
    fi
done < "$IN_FILE"

# 4. Overwrite the original .in file with the new, pinned content
mv "$TEMP_IN_FILE" "$IN_FILE"

echo "✅ Successfully pinned versions in $IN_FILE."