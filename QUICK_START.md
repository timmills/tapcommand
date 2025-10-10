# TapCommand Quick Start Guide

## Fresh Installation (5 minutes)

```bash
# 0. If git not installed (fresh Ubuntu server):
sudo apt-get update && sudo apt-get install -y git

# 1. Clone repository (release branch)
git clone -b release <your-repo-url> /opt/tapcommand
cd /opt/tapcommand

# 2. Run installer (installs everything else)
./install.sh

# 3. Access application
# Open browser to: http://<server-ip>
```

## Common Tasks

### Update to Latest Version
```bash
cd /opt/tapcommand
./update.sh
```

### View Backend Logs
```bash
sudo journalctl -u tapcommand-backend.service -f
```

### Restart Services
```bash
sudo systemctl restart tapcommand-backend.service
sudo systemctl reload nginx
```

### Backup Database
```bash
cp /opt/tapcommand/backend/tapcommand.db ~/tapcommand_backup_$(date +%Y%m%d).db
```

### Check Service Status
```bash
sudo systemctl status tapcommand-backend.service
sudo systemctl status nginx
```

### Access Application
```
http://<server-ip-address>
```

---

## Troubleshooting

**Backend won't start?**
```bash
sudo journalctl -u tapcommand-backend.service -n 50
```

**Frontend not loading?**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**After update, database errors?**
```bash
cd /opt/tapcommand/backend
source venv/bin/activate
python migrate_database.py
```

---

## File Locations

- **Application**: `/opt/tapcommand/`
- **Database**: `/opt/tapcommand/backend/tapcommand.db`
- **Backups**: `/opt/tapcommand/backups/`
- **Logs**: `sudo journalctl -u tapcommand-backend.service`
- **Nginx Config**: `/etc/nginx/sites-available/tapcommand`

---

## Default Settings

- **Backend Port**: 8000 (internal)
- **Frontend Port**: 80 (nginx)
- **Database**: SQLite (file-based)
- **API Endpoint**: `http://<server-ip>/api`

---

For detailed documentation, see [DEPLOYMENT.md](DEPLOYMENT.md)
