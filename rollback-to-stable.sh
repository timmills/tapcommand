#!/bin/bash

# SmartVenue Safe Rollback Script
# Returns to guaranteed working state from September 2025

echo "🛡️ SmartVenue Safe Rollback Script"
echo "=================================="
echo ""

# Show current branch
echo "Current branch: $(git branch --show-current)"
echo "Current commit: $(git rev-parse --short HEAD)"
echo ""

# Offer rollback options
echo "Rollback options:"
echo "1) Switch to stable branch (safe, non-destructive)"
echo "2) Reset current branch to stable (DESTRUCTIVE - loses current changes)"
echo "3) Create new branch from stable"
echo "4) Just show stable branch info"
echo "5) Cancel"
echo ""

read -p "Choose option (1-5): " choice

case $choice in
    1)
        echo "Switching to stable branch..."
        git checkout stable-working-sept-2025
        echo "Restoring database backup..."
        cp backup-database-sept-2025.db backend/smartvenue.db
        echo "✅ Now on stable working state with database restored"
        echo "Your application should work exactly as before analysis"
        ;;
    2)
        echo "⚠️  WARNING: This will PERMANENTLY delete current changes!"
        read -p "Type 'YES' to confirm destructive reset: " confirm
        if [ "$confirm" = "YES" ]; then
            git reset --hard stable-working-sept-2025
            echo "Restoring database backup..."
            cp backup-database-sept-2025.db backend/smartvenue.db
            echo "✅ Branch reset to stable state with database restored"
        else
            echo "❌ Reset cancelled"
        fi
        ;;
    3)
        read -p "Enter new branch name: " branch_name
        git checkout stable-working-sept-2025
        git checkout -b "$branch_name"
        echo "Restoring database backup..."
        cp backup-database-sept-2025.db backend/smartvenue.db
        echo "✅ Created new branch '$branch_name' from stable state with database restored"
        ;;
    4)
        echo "Stable branch info:"
        git log stable-working-sept-2025 --oneline -5
        echo ""
        echo "To switch to stable: git checkout stable-working-sept-2025"
        ;;
    5)
        echo "Rollback cancelled"
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "Current branch: $(git branch --show-current)"
echo "Current commit: $(git rev-parse --short HEAD)"
echo ""
echo "✅ Rollback operation complete"