#!/bin/bash
# Script to create an archive of the containerization package

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PACKAGE_DIR="$SCRIPT_DIR"
ARCHIVE_NAME="ai_system_containerization_package.tar.gz"

echo -e "${GREEN}Creating Archive of Containerization Package${NC}"
echo -e "${GREEN}=========================================${NC}"
echo

# Create archive
echo -e "${YELLOW}Creating archive $ARCHIVE_NAME...${NC}"
cd "$SCRIPT_DIR/.."
tar -czf "$ARCHIVE_NAME" containerization_package

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Archive created successfully: $ARCHIVE_NAME${NC}"
    echo -e "${YELLOW}Archive size: $(du -h "$ARCHIVE_NAME" | cut -f1)${NC}"
    echo -e "${YELLOW}Archive location: $(pwd)/$ARCHIVE_NAME${NC}"
else
    echo -e "${RED}Failed to create archive.${NC}"
    exit 1
fi

echo
echo -e "${GREEN}Archive creation complete!${NC}"
echo -e "${YELLOW}To extract the archive:${NC}"
echo -e "${GREEN}tar -xzf $ARCHIVE_NAME${NC}"
echo 