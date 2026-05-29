#!/bin/bash
# update_deps.sh
set -e # Exit immediately if any command fails

DIR=$1

echo "🔍 Compiling dependencies for ${DIR}..."
pip-compile "${DIR}/requirements.in" --output-file="${DIR}/requirements.txt"

echo "📌 Pinning versions back to ${DIR}/requirements.in..."
./pin_in_file.sh "${DIR}"

echo "✅ Dependencies updated and locked for ${DIR}"