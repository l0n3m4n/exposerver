#!/usr/bin/env python3

import http.server
import socketserver
import subprocess
import threading
import logging
import socket 
import argparse
import textwrap
import requests
import cgi 
import time 
import os
import sys
import shutil
import json
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

# ANSI terminal colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

# Logging setup
logging.basicConfig(
    filename="headers.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

def print_banner():
    banner = rf"""{CYAN}
     .->    (`-')  _<-.(`-')  (`-').->                      <-.(`-')  
 (`(`-')/`) ( OO).-/ __( OO)  (OO )__      .->        .->    __( OO)  
,-`( OO).',(,------.'-'---.\ ,--. ,'-'(`-')----. (`-')----. '-'. ,--. 
|  |\\  |  | |  .---'| .-. (/ |  | |  |( OO).-.  '( OO).-.  '|  .'   / 
|  | '.|  |(|  '--. | '-' `.)|  `-'  |( _) | |  |( _) | |  ||      /) 
|  |.'.|  | |  .--' | /`'.  ||  .-.  | \\|  |)|  | \\|  |)|  ||  .   '  
|   ,'.   | |  `---.| '--'  /|  | |  |  '  '-'  '  '  '-'  '|  |\\   \\ 
`--'   '--' `------'`------' `--' `--'   `-----'    `-----' `--' '--' 
     Author: l0n3m4n | Version: 1.1.3 | Tunneling local Server 
{RESET}"""
    print(banner)

# Check if a port is available
def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False

tunnel_processes = []

def shutdown_server():
    print(f"\n{YELLOW}[!] Shutting down server due to timer...{RESET}")
    if httpd_server_instance:
        httpd_server_instance.shutdown()
    for p in tunnel_processes:
        if p.poll() is None: # If process is still running
            p.terminate()
            p.wait()
    sys.exit(0)

# auto-detect missing binaries 
def require_binary(binary_name, install_hint=None):
    """Check if a binary exists. If not, print install instructions and exit."""
    if shutil.which(binary_name) is None:
        print(f"{RED}[!] Required binary '{binary_name}' not found.{RESET}")
        if install_hint:
            print(f"{YELLOW}[i] Install it with:{RESET}\n  {install_hint}")
        sys.exit(1)

def check_dependencies(args):
    """Check and enforce required binaries based on selected tunnel."""
    if args.serveo:
        require_binary("ssh", "sudo apt install openssh-client")
    elif args.cloudflared:
        require_binary("cloudflared", "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")
    elif args.ngrok:
        require_binary("ngrok", "https://ngrok.com/download")
    elif args.localtunnel:
        require_binary("lt", "npm install -g localtunnel")
    if args.exiftool: # Check exiftool independently
        require_binary("exiftool", "sudo apt install libimage-exiftool-perl")



def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'kb', 'mb', 'gb', 'tb']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


# Custom handler to print and log headers
class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/logs':
            try:
                with open('headers.log', 'r') as f:
                    logs = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(logs.encode('utf-8'))
            except FileNotFoundError:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'') # Send empty response if log file doesn't exist
            return

        headers_str = f"\n[Request] {self.client_address[0]} - Path: {self.path}\n"
        for key, value in self.headers.items():
            headers_str += f"{key}: {value}\n"
        logging.info(headers_str)

        if self.path.startswith('/metadata'):
            query_components = parse_qs(urlparse(self.path).query)
            file_path = query_components.get('file', [None])[0]

            if not file_path:
                self.send_error(400, "File parameter is missing")
                return

            # Security check to prevent directory traversal
            current_dir = os.getcwd()
            requested_path = os.path.join(current_dir, file_path.lstrip('/'))
            if not os.path.abspath(requested_path).startswith(current_dir):
                self.send_error(403, "Forbidden")
                return

        if self.path.startswith('/metadata'):
            query_components = parse_qs(urlparse(self.path).query)
            file_path = query_components.get('file', [None])[0]

            if not file_path:
                self.send_error(400, "File parameter is missing")
                return

            # Security check to prevent directory traversal
            current_dir = os.getcwd()
            requested_path = os.path.join(current_dir, file_path.lstrip('/'))
            if not os.path.abspath(requested_path).startswith(current_dir):
                self.send_error(403, "Forbidden")
                return

            try:
                metadata = {}
                # Check if exiftool is selected
                if hasattr(self.server, 'args') and self.server.args.exiftool:
                    print(f"{GREEN}[+] Extracting metadata using ExifTool for {file_path}{RESET}")
                    # Execute exiftool as a subprocess
                    process = subprocess.run(
                        ["exiftool", "-json", requested_path],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    metadata = json.loads(process.stdout)[0]
                    if metadata:
                        print(f"{GREEN}[+] Found metadata using ExifTool for {file_path}{RESET}")
                    else:
                        print(f"{YELLOW}[!] No metadata found using ExifTool for {file_path}{RESET}")
                else:
                    # Fallback to Pillow for image metadata if exiftool is not selected
                    print(f"{GREEN}[+] Extracting metadata using Pillow for {file_path}{RESET}")
                    image = Image.open(requested_path)
                    exif_data = image._getexif()
                    metadata = {}
                    if exif_data:
                        print(f"{GREEN}[+] Found EXIF data (Pillow) for {file_path}{RESET}")
                        for tag, value in exif_data.items():
                            tag_name = TAGS.get(tag, tag)
                            if isinstance(value, bytes):
                                try:
                                    metadata[tag_name] = value.decode('utf-8', errors='ignore')
                                except UnicodeDecodeError:
                                    metadata[tag_name] = repr(value)
                            else:
                                metadata[tag_name] = str(value)
                    else:
                        print(f"{YELLOW}[!] No EXIF data (Pillow) found for {file_path}{RESET}")

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(metadata).encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "File not found")
            except subprocess.CalledProcessError as e:
                print(f"{RED}[!] ExifTool failed for {file_path}: {e.stderr}{RESET}")
                self.send_error(500, f"ExifTool error: {e.stderr}")
            except Exception as e:
                print(f"{RED}[!] Error processing file {file_path}: {e}{RESET}")
                self.send_error(500, f"Error processing file: {e}")
            return

        if self.path.startswith('/assets/ui/'):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, self.path.lstrip('/'))
            
            # Security check to prevent directory traversal
            if not os.path.abspath(file_path).startswith(os.path.join(script_dir, 'assets', 'ui')):
                self.send_error(403, "Forbidden")
                return

            content_type_map = {
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.html': 'text/html',
            }
            _, ext = os.path.splitext(file_path)
            content_type = content_type_map.get(ext, 'application/octet-stream')

            try:
                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type', content_type)
                    self.end_headers()
                    self.wfile.write(f.read())
                return
            except FileNotFoundError:
                self.send_error(404, "File not found")
                return

        # Get the full path of the requested file/directory
        current_dir = os.getcwd()
        requested_path = os.path.join(current_dir, self.path.lstrip('/'))

        if os.path.isdir(requested_path):
            self.list_directory(requested_path)
        else:
            super().do_GET()

    def list_directory(self, path):
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        
        # Generate the file list HTML
        file_list_html = ''
        if self.path != '/':
            file_list_html += '<tr><td><a href=".."><span class="icon icon-dir"></span>..</a></td><td>Directory</td><td>-</td></tr>'

        file_icon_map = {
            # Documents
            'pdf': 'icon-pdf',
            'doc': 'icon-doc', 'docx': 'icon-doc',
            'xls': 'icon-xls', 'xlsx': 'icon-xls',
            'ppt': 'icon-ppt', 'pptx': 'icon-ppt',
            'odt': 'icon-odt', 'ods': 'icon-ods', 'odp': 'icon-odp',
            'rtf': 'icon-doc', 'csv': 'icon-csv',

            # Code/Text
            'txt': 'icon-text', 'log': 'icon-log', 'md': 'icon-markdown',
            'json': 'icon-json', 'xml': 'icon-xml',
            'py': 'icon-python', 'js': 'icon-javascript', 'html': 'icon-html', 'css': 'icon-css',
            'php': 'icon-php', 'c': 'icon-c', 'cpp': 'icon-cpp', 'java': 'icon-java',
            'go': 'icon-go', 'rb': 'icon-ruby', 'sh': 'icon-shell', 'bat': 'icon-shell', 'ps1': 'icon-shell',
            'yml': 'icon-yaml', 'yaml': 'icon-yaml', 'conf': 'icon-config', 'ini': 'icon-config',

            # Archives
            'zip': 'icon-archive', 'tar': 'icon-archive', 'gz': 'icon-archive',
            '7z': 'icon-archive', 'rar': 'icon-archive', 'iso': 'icon-archive',

            # Images
            'jpg': 'icon-image', 'jpeg': 'icon-image', 'png': 'icon-image', 'gif': 'icon-image',
            'svg': 'icon-image', 'bmp': 'icon-image', 'webp': 'icon-image', 'psd': 'icon-psd',

            # Audio/Video
            'mp3': 'icon-audio', 'wav': 'icon-audio', 'ogg': 'icon-audio',
            'mp4': 'icon-video', 'avi': 'icon-video', 'mov': 'icon-video', 'mkv': 'icon-video',

            # Cybersecurity/Binary
            'pcap': 'icon-network', 'cap': 'icon-network', 'pcapng': 'icon-network',
            'key': 'icon-key', 'pem': 'icon-key', 'crt': 'icon-cert', 'cer': 'icon-cert',
            'vpn': 'icon-vpn', 'ovpn': 'icon-vpn',
            'db': 'icon-database', 'sqlite': 'icon-database', 'sql': 'icon-database', 'dump': 'icon-database',
            'bin': 'icon-binary', 'exe': 'icon-binary', 'dll': 'icon-binary', 'elf': 'icon-binary', 'so': 'icon-binary',
            'apk': 'icon-android', 'jar': 'icon-java-archive',
            'config': 'icon-config',
        }

        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            icon_class = "icon-file"
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
                size = "-"
                type = "Directory"
                icon_class = "icon-dir"
                actions = ""
            else:
                size = human_readable_size(os.path.getsize(fullname))
                type = "File"
                extension = os.path.splitext(name)[1].lstrip('.').lower()
                icon_class = file_icon_map.get(extension, 'icon-file') # Default to generic file icon
                actions = f'<button class="copy-btn" data-url="{linkname}">Copy URL</button>'

            file_list_html += f'<tr><td><a href="{linkname}"><span class="icon {icon_class}"></span>{displayname}</a></td><td>{type}</td><td class="size-cell">{size}</td><td>{actions}</td></tr>'

        # Read the template and inject the data
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(script_dir, 'assets', 'ui', 'index.html')
            with open(template_path, 'r') as f:
                template = f.read()
        except FileNotFoundError:
            self.send_error(500, "Could not find template file")
            return

        content = template.replace('{directory_path}', self.path)
        content = content.replace('{file_list}', file_list_html)

        encoded_content = content.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_content)))
        self.end_headers()
        self.wfile.write(encoded_content)
    

    def do_POST(self):
        if self.path != "/upload":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found.\n")
            return

        ctype, pdict = cgi.parse_header(self.headers.get('content-type', ''))
        if ctype == 'multipart/form-data':
            pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
            pdict['CONTENT-LENGTH'] = int(self.headers['Content-Length'])
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                    environ={'REQUEST_METHOD':'POST'},
                                    keep_blank_values=True)

            if 'file' in form:
                file_item = form['file']
                filename = os.path.basename(file_item.filename)
                file_data = file_item.file.read()

                with open(filename, 'wb') as f:
                    f.write(file_data)

                self.send_response(200)
                self.end_headers()
                self.wfile.write(f"File '{filename}' received and saved.\n".encode())

                # Logging
                logging.info(f"\n[POST] {self.client_address[0]} uploaded file: {filename}")
                return

        # If not multipart/form-data or 'file' missing
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b"Bad Request: Expected multipart/form-data with file field.\n")

    def log_message(self, format, *args):
        message = format % args
        if message.startswith("code"):
            return
        parts = message.split()
        if len(parts) >= 3:
            status_code = parts[-2]
            request_path = parts[1] if len(parts) > 1 else ""
            color = GREEN if status_code.startswith("2") else RED
            status_text = f"{color}[{status_code}]{RESET}"
            if status_code == "404":
                print(f"{status_text} - Not Found: {request_path}", flush=True)
            else:
                print(f"{status_text} - {self.requestline}", flush=True)

def start_http_server(directory, httpd_server):
    os.chdir(directory)
    print(f"{GREEN}[+] Serving {directory} on port {httpd_server.server_address[1]}{RESET}")
    httpd_server.serve_forever()


def start_serveo_tunnel(port):
    require_binary("ssh", "sudo apt install openssh-client")

    print(f"{BLUE}[i] Attempting to open Serveo tunnel on port {port}...{RESET}", flush=True)
    try:
        process = subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-R", f"80:localhost:{port}", "serveo.net"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        tunnel_processes.append(process)
        # Serveo prints the URL to stderr
        for line in iter(process.stderr.readline, b''):
            line = line.decode('utf-8')
            if "Forwarding complete" in line:
                print(f"{GREEN}[+] Serveo tunnel is live!{RESET}")
            if "https://" in line:
                print(f"{CYAN}[*] Public URL: {WHITE}{line.strip()}{RESET}")
            if process.poll() is not None: # If process exited
                break
        # process.wait() # Removed to prevent blocking
    except Exception as e:
        print(f"{YELLOW}[!] Serveo tunnel failed: {e}. Falling back to cloudflared...\n{RESET}")
        start_cloudflared_tunnel(port)


def start_cloudflared_tunnel(port):
    require_binary("cloudflared", "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")

    print(f"{BLUE}[i] Starting cloudflared tunnel on port {port}...{RESET}", flush=True)
    try:
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        tunnel_processes.append(process)

        # Create threads to read stdout and stderr concurrently
        def read_stream(stream, is_stderr=False):
            for line in iter(stream.readline, ''):
                print(f"[cloudflared {'stderr' if is_stderr else 'stdout'}]: {line.strip()}") # Debug print
                if "https://" in line:
                    print(f"{GREEN}[+] Cloudflared tunnel is live!{RESET}")
                    print(f"{CYAN}[*] Public URL: {WHITE}{line.strip().split(' ')[-1]}{RESET}")
                    # No break here, let it continue printing other info

        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout,))
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, True))

        stdout_thread.start()
        stderr_thread.start()

        # The main thread should not wait for these, as they are background processes
        # The process itself is managed by tunnel_processes and shutdown_server
        # process.wait() # Removed to prevent blocking
    except Exception as e:
        print(f"{RED}[!] cloudflared tunnel failed: {e}. Exiting.{RESET}")
        sys.exit(1)


def start_ngrok_tunnel(port):
    require_binary("ngrok", "https://ngrok.com/download")

    print(f"{BLUE}[i] Starting ngrok tunnel on port {port}...{RESET}")

    try:
        # Start ngrok in the background
        ngrok_process = subprocess.Popen(["ngrok", "http", str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tunnel_processes.append(ngrok_process)

        # Wait for ngrok's web interface to become available
        time.sleep(3)  # give ngrok time to start

        # Try to get the tunnel URL from the ngrok API
        try:
            resp = requests.get("http://localhost:4040/api/tunnels")
            tunnels = resp.json()["tunnels"]
            public_urls = [t["public_url"] for t in tunnels if t["proto"] == "http" or t["proto"] == "https"]

            if public_urls:
                print(f"{GREEN}[+] Ngrok tunnel is live!{RESET}")
                for url in public_urls:
                    print(f"{CYAN}[*] Public URL: {WHITE}{url}{RESET}")
            else:
                print(f"{YELLOW}[!] No public URLs found from ngrok API.{RESET}")

        except requests.ConnectionError:
            print(f"{RED}[!] Unable to connect to ngrok API (http://localhost:4040).{RESET}")
            ngrok_process.terminate()
            sys.exit(1)

        # Keep the process running so ngrok stays alive
        # ngrok_process.wait() # Removed to prevent blocking

    except subprocess.CalledProcessError:
        print(f"{RED}[!] ngrok tunnel failed. Exiting.{RESET}")
        sys.exit(1)

def start_localtunnel(port):
    require_binary("lt", "npm install -g localtunnel")

    print(f"{BLUE}[i] Starting localtunnel tunnel on port {port}...{RESET}")
    try:
        process = subprocess.Popen(
            ["lt", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        tunnel_processes.append(process)
        for line in iter(process.stdout.readline, ''):
            if "your url is:" in line:
                print(f"{GREEN}[+] LocalTunnel is live!{RESET}")
                print(f"{CYAN}[*] Public URL: {WHITE}{line.split('your url is: ')[-1].strip()}{RESET}")
                break
        # process.wait() # Removed to prevent blocking
    except Exception as e:
        print(f"{RED}[!] localtunnel failed: {e}. Exiting.{RESET}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
    description="📡 Serve a local directory and expose it via a tunnel (Serveo, Cloudflared, Ngrok, LocalTunnel).",
    epilog=textwrap.dedent(f"""{CYAN}
    Examples:
      python3 webhook.py -p 8080 --serveo --exiftool -d ~/my-site -shutdown-timer 600 
      python3 webhook.py -p 80 -d ~/my-site --cloudflared --exiftool
      python3 webhook.py -p 3000 -d ~/my-site --ngrok
      python3 webhook.py -p 8080 -d ~/my-site --localtunnel
    {RESET}"""),
    formatter_class=argparse.RawDescriptionHelpFormatter
)
  
    parser.add_argument("-p", "--port", type=int, default=80, help="Local port to serve (default: 80)")
    parser.add_argument("-d", "--directory", default=".", help="Directory to serve (default: current dir)")
    parser.add_argument("--shutdown-timer", type=int, help="Automatically shut down after N seconds")
    
    tunnel_group = parser.add_mutually_exclusive_group(required=True)
    tunnel_group.add_argument("--serveo", action="store_true", help="Use Serveo tunnel")
    tunnel_group.add_argument("--cloudflared", action="store_true", help="Use Cloudflared tunnel")
    tunnel_group.add_argument("--ngrok", action="store_true", help="Use Ngrok tunnel")
    tunnel_group.add_argument("--localtunnel", action="store_true", help="Use LocalTunnel tunnel")

    parser.add_argument("--exiftool", action="store_true", help="Use ExifTool for metadata extraction")

    
    args = parser.parse_args()
    check_dependencies(args)
     
     
    if not is_port_available(args.port):
        print(f"{RED}[!] Port {args.port} is already in use. Choose a different port.{RESET}")
        sys.exit(1)
    
    global httpd_server_instance
    handler = RequestHandler
    httpd_server_instance = socketserver.TCPServer(('', args.port), handler)
    httpd_server_instance.args = args # Pass args to the server
    threading.Thread(target=start_http_server, args=(args.directory, httpd_server_instance), daemon=True).start()

    if args.shutdown_timer:
        print(f"{BLUE}[i] Server will automatically shut down in {args.shutdown_timer} seconds.{RESET}")
        timer = threading.Timer(args.shutdown_timer, shutdown_server)
        timer.daemon = True
        timer.start()

    # Start selected tunnel
    if args.serveo:
        start_serveo_tunnel(args.port)
    elif args.cloudflared:
        start_cloudflared_tunnel(args.port)
    elif args.ngrok:
        start_ngrok_tunnel(args.port)
    elif args.localtunnel:
        start_localtunnel(args.port)

    # Keep the main thread alive until shutdown
    while True:
        time.sleep(1)


if __name__ == "__main__":
    print_banner()
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}[!] Interrupted by user. Exiting...{RESET}")
        sys.exit(0)
