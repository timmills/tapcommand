# Release Branch Creation Checklist

Follow this checklist when creating your first release or preparing new releases.

## First Time: Create Release Branch

```bash
# 1. Ensure main branch is clean and working
git checkout main
git status  # Should be clean

# 2. Create release branch
git checkout -b release

# 3. Create clean database template
cd backend
source venv/bin/activate
python create_template_db.py
deactivate
cd ..

# Expected output:
#   ✓ Template database created: tapcommand_template.db
#   Template database contents:
#     - Users: X
#     - Roles: X
#     - IR Codes: X

# 4. Add template to git
git add backend/tapcommand_template.db
git add .gitignore  # Already updated to allow template
git status  # Verify only template is being added

# 5. Commit
git commit -m "chore: Add clean database template for deployments"

# 6. Tag initial release
git tag -a v1.0.0 -m "Initial production release v1.0.0"

# 7. Push to GitHub
git push -u origin release
git push origin v1.0.0

# 8. Verify on GitHub
# Go to your repo → Branches → Should see 'release'
# Go to Releases → Should see v1.0.0 tag
```

---

## For Each New Release (v1.1.0, v1.2.0, etc.)

```bash
# 1. Ensure main branch has all tested changes
git checkout main
git pull
git log --oneline -5  # Review recent changes

# 2. Switch to release branch
git checkout release
git pull

# 3. Merge main into release
git merge main

# If merge conflicts, resolve them:
#   - Edit conflicted files
#   - git add <resolved-files>
#   - git merge --continue

# 4. Regenerate database template (if schema changed)
cd backend
source venv/bin/activate
python create_template_db.py

# Compare with existing template
ls -lh tapcommand_template.db

# 5. If template changed, commit it
git status
git add tapcommand_template.db
git commit -m "chore: Update database template for v1.X.X"

# 6. Update version in code (if you have a version file)
# Example: Edit backend/app/core/config.py or package.json

# 7. Tag the new release
VERSION="1.1.0"  # Change this
git tag -a "v${VERSION}" -m "Release version ${VERSION}"

# 8. Push everything
git push origin release
git push origin "v${VERSION}"

# 9. Verify
git log --oneline -5
git tag --list
```

---

## Pre-Release Testing

Before pushing to `release` branch, test on a clean VM:

```bash
# On test VM:
git clone -b release <your-repo-url> /tmp/test-install
cd /tmp/test-install
./install.sh

# Verify:
# - Installation completes without errors
# - Can access frontend at http://localhost
# - Backend health check works: curl http://localhost/api/health
# - Can login with default credentials
# - Database template is clean (no old data)

# Test update:
./update.sh

# Verify:
# - Update completes successfully
# - Services restart properly
# - Application still works
```

---

## What Gets Released

### Included in Release Branch:
- ✅ All application code (backend/, frontend-v2/)
- ✅ Installation scripts (install.sh, update.sh)
- ✅ Database migration tools (migrate_database.py)
- ✅ Clean database template (tapcommand_template.db)
- ✅ Documentation (DEPLOYMENT.md, QUICK_START.md)
- ✅ Systemd service templates (deploy/systemd/)
- ✅ Dependencies (requirements.txt, package.json)

### Excluded (via .gitignore):
- ❌ Development database (tapcommand.db)
- ❌ Environment files (.env, .env.local)
- ❌ Virtual environments (venv/, node_modules/)
- ❌ Build artifacts (dist/, __pycache__/)
- ❌ Logs (*.log)
- ❌ Backups (backups/)

---

## Rollback a Bad Release

If a release has issues:

```bash
# 1. Find previous good tag
git tag --list

# 2. Reset release branch to previous tag
git checkout release
git reset --hard v1.0.0  # Use previous good version

# 3. Force push (WARNING: This overwrites history)
git push origin release --force

# Sites can then pull the reverted version
```

---

## GitHub Release Notes (Optional)

After pushing tag, create a GitHub Release:

1. Go to GitHub → Releases → "Draft a new release"
2. Choose tag: v1.X.X
3. Release title: "TapCommand v1.X.X"
4. Description:
   ```markdown
   ## What's New
   - Feature 1
   - Feature 2
   - Bug fix 3

   ## Installation
   See [DEPLOYMENT.md](DEPLOYMENT.md)

   ## Upgrade from v1.0.0
   ```bash
   cd /opt/tapcommand
   ./update.sh
   ```
   ```
5. Publish release

---

## Branch Strategy Summary

```
main (development)
  ├── New features
  ├── Bug fixes
  ├── Experiments
  └── Active work
       ↓
     [merge when stable]
       ↓
release (production)
  ├── Stable, tested code
  ├── Clean database template
  ├── Version tags (v1.0.0, v1.1.0, etc.)
  └── What customers deploy from
       ↓
     [git clone -b release]
       ↓
Customer Sites
  ├── Site A: git pull to update
  ├── Site B: git pull to update
  └── Site C: git pull to update
```

---

## Helpful Commands

```bash
# View all branches
git branch -a

# View all tags
git tag --list

# View commits in release but not in main
git log main..release --oneline

# View commits in main but not in release
git log release..main --oneline

# View changes in database template
git log -p backend/tapcommand_template.db

# Compare main and release branches
git diff main release

# Show tag details
git show v1.0.0
```

---

## Questions?

- **How often to release?** - When you have stable changes ready for production
- **How to handle hotfixes?** - Apply to both main and release branches
- **What if I forget to update template?** - Sites will create fresh DB on first install
- **Can I delete old tags?** - Not recommended, keep for rollback capability
