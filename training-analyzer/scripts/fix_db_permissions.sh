#!/bin/bash
#
# fix_db_permissions.sh
# Sets all .db files to 600 (owner read/write only) for security
#
# Usage: ./fix_db_permissions.sh [directory]
#   If no directory specified, defaults to the garmin_insights project root
#

set -e

# Default to project root (two directories up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(dirname "$(dirname "$SCRIPT_DIR")")}"

echo "Fixing database file permissions in: $PROJECT_ROOT"
echo "=================================================="

# Find all .db files and fix permissions
DB_FILES=$(find "$PROJECT_ROOT" -name "*.db" -type f 2>/dev/null)

if [ -z "$DB_FILES" ]; then
    echo "No .db files found in $PROJECT_ROOT"
    exit 0
fi

# Counter for fixed files
FIXED_COUNT=0

while IFS= read -r db_file; do
    # Get current permissions
    CURRENT_PERMS=$(stat -f "%Lp" "$db_file" 2>/dev/null || stat -c "%a" "$db_file" 2>/dev/null)

    if [ "$CURRENT_PERMS" != "600" ]; then
        echo "Fixing: $db_file"
        echo "  Before: $CURRENT_PERMS"
        chmod 600 "$db_file"
        NEW_PERMS=$(stat -f "%Lp" "$db_file" 2>/dev/null || stat -c "%a" "$db_file" 2>/dev/null)
        echo "  After:  $NEW_PERMS"
        ((FIXED_COUNT++))
    else
        echo "OK: $db_file (already 600)"
    fi
done <<< "$DB_FILES"

echo ""
echo "=================================================="
echo "Complete: $FIXED_COUNT file(s) fixed"
