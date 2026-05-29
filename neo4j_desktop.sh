#!/bin/bash

set -e

VERSION="2.1.4"
APPIMAGE="$HOME/neo4j-desktop-$VERSION-x86_64.AppImage"

# check if Neo4j Desktop exists
if [ ! -f "$APPIMAGE" ]; then
    echo "Neo4j Desktop AppImage not found."
    echo ""
    echo "Please download it manually from:"
    echo "https://neo4j.com/download/"
    echo ""
    echo "Expected location:"
    echo "$APPIMAGE"
    exit 1
fi

# ensure executable
chmod +x "$APPIMAGE"

# fix for Linux UI issues
export NO_AT_BRIDGE=1

echo "Starting Neo4j Desktop..."
"$APPIMAGE" --no-sandbox