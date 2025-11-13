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
import time 
import os
import sys
import shutil
import re
import json
import base64
import binascii
import io
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

def get_assets_base_path():
    """Determines the base path for assets."""
    # Path 1: 'assets' directory relative to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, 'assets')
    if os.path.isdir(local_path):
        return local_path

    # Path 2: '.exposerver/assets' in the user's home directory
    home_dir = os.path.expanduser("~")
    user_path = os.path.join(home_dir, '.exposerver', 'assets')
    if os.path.isdir(user_path):
        return user_path

    # Fallback to the local path, allowing errors to be handled downstream
    return local_path

ASSETS_BASE_PATH = get_assets_base_path()


# ANSI terminal colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
        }
        if isinstance(record.msg, dict):
            log_record.update(record.msg)
        else:
            log_record["message"] = record.getMessage()
        return json.dumps(log_record)

class TextFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.msg, dict):
            headers_dict = record.msg.get("headers", {})
            headers_str = "\n".join([f"{key}: {value}" for key, value in headers_dict.items()])
            return f"\n[Request] {record.msg.get('client_address', '')[0]} - Path: {record.msg.get('path', '')}\n{headers_str}"
        else:
            return super().format(record)

def print_banner():
    banner = rf"""{CYAN}
___________                                                            
\_   _____/__  _________   ____  ______ ______________  __ ___________
 |    __)_\  \/  /\____ \ /  _ \/  ___// __ \_  __ \  \/ // __ \_  __ \
 |        \>    < |  |_> >  <_> )___ \\  ___/|  | \/\   /\  ___/|  | \/
/_______  /__/\_ \|   __/ \____/____  >\___  >__|    \_/  \___  >__|   
        \/      \/|__|              \/     \/                 \/       
     Author: l0n3m4n | Version: 1.3.4 | Tunneling local Server 
{RESET}"""
    print(banner)

def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False

def check_and_install_dependencies(args):
    """Check and install dependencies."""
    dependencies = [
        {"name": "requests", "type": "pip", "check": "requests"},
        {"name": "Pillow", "type": "pip", "check": "PIL"},
        {"name": "exiftool", "type": "package_manager", "check": "exiftool", "install": "libimage-exiftool-perl"},
    ]

    if args.verbose:
        print(f"{BLUE}[i] Checking for dependencies...{RESET}")
    for dep in dependencies:
        if args.verbose:
            print(f"{BLUE}[i] Checking for {dep['name']}...{RESET}")
        if dep["type"] == "pip":
            try:
                __import__(dep["check"])
                if args.verbose:
                    print(f"{GREEN}[+] {dep['name']} is already installed.{RESET}")
            except ImportError:
                print(f"{YELLOW}[!] {dep['name']} not found. Installing...{RESET}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep['name'], "--break-system-packages"])
        elif dep["type"] == "package_manager":
            if shutil.which(dep["check"]):
                if args.verbose:
                    print(f"{GREEN}[+] {dep['name']} is already installed.{RESET}")
            else:
                print(f"{YELLOW}[!] {dep['name']} not found. Attempting to install...{RESET}")
                package_managers = {
                    "apt-get": "sudo apt-get install -y {}",
                    "yum": "sudo yum install -y {}",
                    "pacman": "sudo pacman -S --noconfirm {}",
                    "brew": "brew install {}",
                }
                installed = False
                for pm, command in package_managers.items():
                    if shutil.which(pm):
                        try:
                            subprocess.check_call(command.format(dep['install']).split())
                            installed = True
                            break
                        except subprocess.CalledProcessError as e:
                            print(f"{RED}[!] Failed to install {dep['name']} using {pm}.{RESET}")
                            print(e)
                if not installed:
                    print(f"{RED}[!] Could not install {dep['name']}. Please install it manually.{RESET}")
                    if sys.platform == "darwin":
                        print(f"{YELLOW}[i] On macOS, you can use Homebrew: brew install {dep['install']}{RESET}")
                    elif sys.platform.startswith("linux"):
                        print(f"{YELLOW}[i] On Debian/Ubuntu: sudo apt-get install {dep['install']}{RESET}")
                        print(f"{YELLOW}[i] On Fedora/CentOS: sudo yum install {dep['install']}{RESET}")
                        print(f"{YELLOW}[i] On Arch Linux: sudo pacman -S {dep['install']}{RESET}")
                    sys.exit(1)

# auto-detect missing binaries 
def require_binary(binary_name, install_hint=None):
    """Check if a binary exists. If not, print install instructions and exit."""
    if shutil.which(binary_name) is None:
        print(f"{RED}[!] Required binary '{binary_name}' not found.{RESET}")
        if install_hint:
            print(f"{YELLOW}[i] Install it with:{RESET}\n  {install_hint}")
        sys.exit(1)

def check_tunnel_dependencies(args):
    """Check and enforce required binaries based on selected tunnel."""
    if args.serveo:
        require_binary("ssh", "sudo apt install openssh-client")
    elif args.cloudflared:
        require_binary("cloudflared", "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")
    elif args.ngrok:
        require_binary("ngrok", "https://ngrok.com/download")
    elif args.localtunnel:
        require_binary("lt", "npm install -g localtunnel")



def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'kb', 'mb', 'gb', 'tb']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


# Custom handler to print and log headers
class RequestHandler(SimpleHTTPRequestHandler):
    def is_authenticated(self):
        if not hasattr(self.server, 'args') or not self.server.args.auth:
            return True # No auth configured

        auth_header = self.headers.get('Authorization')
        if auth_header is None:
            logging.info(f"\n[AUTH] No credentials provided from {self.client_address[0]}")
            self.do_AUTHHEAD()
            return False

        if not auth_header.startswith('Basic '):
            logging.info(f"\n[AUTH] Invalid auth header format from {self.client_address[0]}")
            self.do_AUTHHEAD()
            return False

        try:
            encoded_credentials = auth_header.split(' ', 1)[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            user, passwd = decoded_credentials.split(':', 1)
        except (ValueError, TypeError, binascii.Error):
            logging.info(f"\n[AUTH] Malformed credentials from {self.client_address[0]}")
            self.do_AUTHHEAD()
            return False

        if user == self.server.args.auth_user and passwd == self.server.args.auth_pass:
            if self.path != '/logs':
                logging.info(f"\n[AUTH] Successful login for user '{user}' from {self.client_address[0]}")
            return True
        
        logging.info(f"\n[AUTH] Failed login attempt for user '{user}' from {self.client_address[0]}")
        self.do_AUTHHEAD()
        return False

    def _is_safe_path(self, base_dir, requested_path):
        # Ensure the requested path is within the base directory
        abs_base_dir = os.path.abspath(base_dir)
        abs_requested_path = os.path.abspath(requested_path)
        return abs_requested_path.startswith(abs_base_dir)

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="ExpoServer"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    def do_GET(self):
        if not self.is_authenticated():
            self.wfile.write(b'Unauthorized')
            return
        
        # Handle single file serving
        if hasattr(self.server.args, 'single_file_to_serve') and self.server.args.single_file_to_serve:
            target_file = self.server.args.single_file_to_serve
            # If the request is for the root or the exact filename, serve the file
            if self.path == '/' or self.path == f'/{target_file}':
                file_path = os.path.join(self.server.args.directory, target_file)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    try:
                        with open(file_path, 'rb') as f:
                            self.send_response(200)
                            self.send_header('Content-type', self.guess_type(file_path))
                            self.send_header('Content-Length', str(os.path.getsize(file_path)))
                            self.end_headers()
                            self.wfile.write(f.read())
                        return
                    except Exception as e:
                        logging.error(f"Error serving single file {file_path}: {e}")
                        self.send_error(500, f"Error serving file: {e}")
                        return
                else:
                    self.send_error(404, "File not found")
                    return
            else:
                self.send_error(404, "Not Found")
                return

        if self.path == '/logs':
            try:
                with open(self.server.args.outfile, 'r') as f:
                    logs = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(logs.encode('utf-8'))
            except FileNotFoundError:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'') 
            return

        log_data = {
            "client_address": self.client_address,
            "path": self.path,
            "headers": dict(self.headers),
        }
        logging.info(log_data)

        if self.path.startswith('/metadata'):
            query_components = parse_qs(urlparse(self.path).query)
            file_path = query_components.get('file', [None])[0]

            if not file_path:
                self.send_error(400, "File parameter is missing")
                return

            current_dir = os.getcwd()
            requested_path = os.path.join(current_dir, file_path.lstrip('/'))

            # Security check to prevent directory traversal
            if not self._is_safe_path(current_dir, requested_path):
                self.send_error(403, "Forbidden")
                return
            
            try:
                metadata = {}
                # Check if exiftool is available
                if shutil.which('exiftool'):
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
                    # Fallback to Pillow for image metadata if exiftool is not available
                    print(f"{YELLOW}[i] exiftool not found. Falling back to Pillow for metadata extraction.{RESET}")
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
            path_inside_assets = self.path.split('/assets/', 1)[1]
            file_path = os.path.join(ASSETS_BASE_PATH, path_inside_assets)
            
            # Security check to prevent directory traversal
            if not self._is_safe_path(os.path.join(ASSETS_BASE_PATH, 'ui'), file_path):
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

        # For any other GET request, use the default handler, but first check if it's a directory.
        # If it is, use our custom directory listing.
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            self.list_directory(path)
        else:
            super().do_GET()

    def translate_path(self, path):
        # A simple version of translate_path that uses the current working directory
        # set by start_http_server
        return os.path.join(os.getcwd(), path.lstrip('/'))

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
            template_path = os.path.join(ASSETS_BASE_PATH, 'ui', 'index.html')
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
        log_data = {
            "client_address": self.client_address,
            "path": self.path,
            "headers": dict(self.headers),
        }
        logging.info(log_data)

        if not self.is_authenticated():
            self.wfile.write(b'Unauthorized')
            return
        if self.path != "/upload":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found.\n")
            return

        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Expected multipart/form-data.\n")
            return

        try:
            # Extract boundary
            boundary_match = re.search(r'boundary=([^;]+)', content_type)
            if not boundary_match:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: No boundary found in Content-Type.\n")
                return
            boundary = boundary_match.group(1).encode('latin-1') # Boundaries are typically latin-1 encoded

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: Content-Length is 0.\n")
                return

            # Read the entire request body
            body = self.rfile.read(content_length)

            # Split by boundary
            parts = body.split(b'--' + boundary)
            
            # The first part is usually empty, the last is the closing boundary
            # We are interested in the parts in between
            file_item = None
            for part in parts:
                if b'Content-Disposition: form-data;' in part and b'filename=' in part:
                    file_item = part
                    break

            if not file_item:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: No file found in multipart/form-data.\n")
                return

            # Extract filename
            filename_match = re.search(b'filename="([^"]+)"', file_item)
            if not filename_match:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: Could not extract filename.\n")
                return
            original_filename = filename_match.group(1).decode('utf-8', errors='ignore')

            # Extract file content
            # Find the double CRLF that separates headers from content
            headers_end = file_item.find(b'\r\n\r\n')
            if headers_end == -1:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: Malformed multipart part (no header/content separator).\n")
                return
            
            file_content = file_item[headers_end + 4:] # +4 for \r\n\r\n
            
            # Remove trailing \r\n if present (from the part boundary)
            if file_content.endswith(b'\r\n'):
                file_content = file_content[:-2]

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{original_filename}"
            
            upload_path = os.path.join('upload', filename)

            logging.debug(f"Original filename: {original_filename}")
            logging.debug(f"Timestamp: {timestamp}")
            logging.debug(f"Generated filename: {filename}")
            logging.debug(f"Upload path: {upload_path}")

            with open(upload_path, 'wb') as f:
                f.write(file_content)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"File '{original_filename}' uploaded and saved as '{filename}'.\n".encode())

            # Logging
            logging.info(f"\n[POST] {self.client_address[0]} uploaded file: {original_filename} as {filename}")
            return

        except Exception as e:
            logging.error(f"Error processing POST request: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Internal Server Error: {e}\n".encode())
            return

    def log_message(self, format, *args):
        if self.path == '/logs':
            return
        message = format % args
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

def start_http_server(directory, port, args):
    os.chdir(directory)
    handler = RequestHandler
    bind_address = "127.0.0.1" if args.single_host else "0.0.0.0"
    with socketserver.TCPServer((bind_address, port), handler) as httpd:
        httpd.args = args 
        print(f"{GREEN}[+] Serving {directory} on {bind_address}:{port}{RESET}")
        httpd.serve_forever()


def start_serveo_tunnel(port):
    require_binary("ssh", "sudo apt install openssh-client")

    while True:
        print(f"{BLUE}[i] Attempting to open Serveo tunnel on port {port}...{RESET}", flush=True)
        try:
            subprocess.run(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-R", f"80:localhost:{port}", "serveo.net"],
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"{YELLOW}[!] Serveo tunnel failed. Retrying in 5 seconds...\n{RESET}")
            time.sleep(5)


def start_cloudflared_tunnel(port):
    require_binary("cloudflared", "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")

    while True:
        print(f"{BLUE}[i] Starting cloudflared tunnel on port {port}...{RESET}", flush=True)
        
        cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )

            url_found = False
            url_pattern = re.compile(r'https?://[a-zA-Z0-9-]+\.trycloudflare\.com')

            for line in iter(process.stderr.readline, ''):
                if not url_found:
                    match = url_pattern.search(line)
                    if match:
                        print(f"{GREEN}[+] Tunnel URL: {WHITE}{match.group(0)}{RESET}")
                        url_found = True
            
            retcode = process.wait()
            if retcode != 0:
                print(f"{RED}[!] cloudflared tunnel exited with code {retcode}. Retrying in 5 seconds...{RESET}")
                time.sleep(5)

        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            print(f"{RED}[!] cloudflared tunnel failed: {e}. Retrying in 5 seconds...{RESET}")
            time.sleep(5)


def start_ngrok_tunnel(port):
    require_binary("ngrok", "https://ngrok.com/download")

    while True:
        print(f"{BLUE}[i] Starting ngrok tunnel on port {port}...{RESET}")

        try:
            # Start ngrok in the background
            ngrok_process = subprocess.Popen(["ngrok", "http", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Wait for ngrok's web interface to become available with retries
            ngrok_api_url = "http://localhost:4040/api/tunnels"
            max_retries = 10
            retry_delay = 1  # seconds
            for i in range(max_retries):
                try:
                    resp = requests.get(ngrok_api_url, timeout=1)
                    if resp.status_code == 200:
                        break # ngrok API is up
                except requests.ConnectionError:
                    pass
                time.sleep(retry_delay)
            else:
                print(f"{RED}[!] Ngrok API did not become available after {max_retries} retries. Restarting...{RESET}")
                ngrok_process.terminate()
                time.sleep(5)
                continue

            # Try to get the tunnel URL from the ngrok API
            try:
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
                time.sleep(5)
                continue

            # Keep the process running so ngrok stays alive
            ngrok_process.wait()
            print(f"{RED}[!] ngrok tunnel exited. Retrying in 5 seconds...{RESET}")
            time.sleep(5)

        except subprocess.CalledProcessError:
            print(f"{RED}[!] ngrok tunnel failed. Retrying in 5 seconds...{RESET}")
            time.sleep(5)

def start_localtunnel(port):
    require_binary("lt", "npm install -g localtunnel")

    try:
        public_ip_process = subprocess.run(["curl", "ifconfig.me"], capture_output=True, text=True, check=True)
        public_ip = public_ip_process.stdout.strip()
        print(f"{YELLOW}[i] Localtunnel password is your public IP: {GREEN}{public_ip}{RESET}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{YELLOW}[i] Could not determine public IP. You may need to find it manually.{RESET}")

    print(f"{YELLOW}[i] To bypass the password prompt, use a browser extension like 'ModHeader' to set the following request header:{RESET}")
    print(f"{YELLOW}[i]   Header Name: {CYAN}bypass-localtunnel-lt{RESET}")
    print(f"{YELLOW}[i]   Header Value: {CYAN}true{RESET}")

    while True:
        print(f"{BLUE}[i] Starting localtunnel tunnel on port {port}...{RESET}")
        try:
            subprocess.run(["lt", "--port", str(port)], check=True)
        except subprocess.CalledProcessError:
            print(f"{RED}[!] localtunnel failed. Retrying in 5 seconds...{RESET}")
            time.sleep(5)

def update_script():
    print(f"{BLUE}[i] Updating script from GitHub...{RESET}")
    try:
        url = "https://raw.githubusercontent.com/l0n3m4n/exposerver/master/exposerver.py"
        response = requests.get(url)
        response.raise_for_status()  

        script_path = os.path.abspath(__file__) 
        with open(script_path, 'w') as f:
            f.write(response.text)
        print(f"{GREEN}[+] Script updated successfully! Please restart the script for the changes to take effect.{RESET}")

        # After a successful update, check if the script exists in /usr/local/bin and update it.
        local_bin_path = '/usr/local/bin/exposerver'
        if os.path.exists(local_bin_path):
            print(f"{BLUE}[i] Found script in {local_bin_path}. Updating...{RESET}")
            try:
                subprocess.run(['sudo', 'cp', script_path, local_bin_path], check=True)
                print(f"{GREEN}[+] Script in {local_bin_path} updated successfully!{RESET}")
            except subprocess.CalledProcessError as e:
                print(f"{RED}[!] Failed to update script in {local_bin_path}: {e}{RESET}")
                print(f"{YELLOW}[i] Please try running the update command with sudo.{RESET}")
            except FileNotFoundError:
                print(f"{RED}[!] Failed to update script in {local_bin_path}. 'sudo' command not found.{RESET}")

    except requests.exceptions.RequestException as e:
        print(f"{RED}[!] Failed to download update from {url}: {e}{RESET}")
    except Exception as e:
        print(f"{RED}[!] An error occurred during update: {e}{RESET}")
    sys.exit(0)

def save_to_local_bin():
    script_path = os.path.abspath(__file__)
    destination_path = '/usr/local/bin/exposerver'
    print(f"{BLUE}[i] Saving script to {destination_path}...{RESET}")
    try:
        subprocess.run(['sudo', 'cp', script_path, destination_path], check=True)
        subprocess.run(['sudo', 'chmod', '+x', destination_path], check=True)
        print(f"{GREEN}[+] Script saved successfully! You can now run it as 'exposerver'.{RESET}")

        script_dir = os.path.dirname(script_path)
        asset_src_dir = os.path.join(script_dir, 'assets')
        if os.path.isdir(asset_src_dir):
            home_dir = os.path.expanduser('~')
            asset_dest_dir = os.path.join(home_dir, '.exposerver', 'assets')
            print(f"{BLUE}[i] Copying assets to {asset_dest_dir}...{RESET}")
            if os.path.exists(asset_dest_dir):
                shutil.rmtree(asset_dest_dir)
            shutil.copytree(asset_src_dir, asset_dest_dir)
            print(f"{GREEN}[+] Assets copied successfully!{RESET}")
        else:
            print(f"{YELLOW}[!] 'assets' directory not found next to script. Skipping asset copy.{RESET}")

    except subprocess.CalledProcessError as e:
        print(f"{RED}[!] Failed to save script: {e}{RESET}")
        print(f"{YELLOW}[i] Please try running the command with sudo.{RESET}")
    except FileNotFoundError:
        print(f"{RED}[!] Failed to save script. 'sudo' command not found.{RESET}")
    except Exception as e:
        print(f"{RED}[!] An error occurred during asset copy: {e}{RESET}")
    sys.exit(0)

def shutdown_server(timeout):
    print(f"\n{RED}[!] Server shutting down after {timeout} seconds.{RESET}")
    sys.exit(0)


def clear_log_file(log_path):
    if os.path.exists(log_path):
        os.remove(log_path)
        print(f"{GREEN}[+] Log file removed: {log_path}{RESET}")
    else:
        print(f"{YELLOW}[i] Log file not found, nothing to clear: {log_path}{RESET}")
    sys.exit(0)


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def format_help(self):
        help_text = super().format_help()
        return f"{GREEN}{help_text}{RESET}"


def main():
    parser = argparse.ArgumentParser(
    description="📡 Serve a local directory and expose it via a tunnel (Serveo, Cloudflared, Ngrok).",
    epilog=textwrap.dedent(f'''{GREEN}
Examples:
   python3 exposerver.py -p 8080 --serveo 
   python3 exposerver.py -p 80 -d /var/www/html --cloudflared
   python3 exposerver.py -p 3000 -d ~/my-site --ngrok
   python3 exposerver.py -p 8080 -d ~/my-site --localtunnel
   python3 exposerver.py -p 8080 --cloudflared --auth myuser:mypassword
   python3 exposerver.py -p 8000 -d ./my_local_site  
   python3 exposerver.py -p 8001 -f ./my_local_file.txt   
   python3 exposerver.py -p 9095 -f payload.txt -s 
   python3 exposerver.py -p 8080 -d ./site --ngrok -t 600
   python3 exposerver.py --clear-logs 
    {RESET}'''),
    formatter_class=lambda prog: CustomHelpFormatter(prog, max_help_position=50)
)
  
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("-p", "--port", type=int, default=80, help="Local port to serve (default: 80)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--directory", default=".", help="Directory to serve (default: .)")
    group.add_argument("-f", "--file", help="Serve a single file (e.g., -f payload.txt).")
    parser.add_argument("-s", "--single-host", action="store_true", help="Serve only on localhost (127.0.0.1).")
    parser.add_argument("-t", "--timeout", type=int, help="Automatically shut down the server after a specified time in seconds.")
    parser.add_argument("--auth", help="Enable basic authentication (format: username:password)")
    parser.add_argument("-o", "--outfile", default="headers.log", help="Specify a file to save the logs (e.g., logs.json, logs.txt).")

    tunnel_group = parser.add_argument_group('Tunnel Options')
    tunnel_exclusive_group = tunnel_group.add_mutually_exclusive_group(required=False)
    tunnel_exclusive_group.add_argument("--serveo", action="store_true", help="Use Serveo tunnel")
    tunnel_exclusive_group.add_argument("--cloudflared", action="store_true", help="Use Cloudflared tunnel")
    tunnel_exclusive_group.add_argument("--ngrok", action="store_true", help="Use Ngrok tunnel")
    tunnel_exclusive_group.add_argument("--localtunnel", action="store_true", help="Use LocalTunnel tunnel")

    management_group = parser.add_argument_group('Script Management')
    management_group.add_argument("-u", "--update", action="store_true", help="Update the script from GitHub.")
    management_group.add_argument("-sl", "--save-local", action="store_true", help="Save the script to /usr/local/bin")
    management_group.add_argument("--clear-logs", action="store_true", help="Clear the log file.")

    
    args = parser.parse_args()
    args.single_file_to_serve = None 
    if args.update:
        update_script()
    if args.save_local:
        save_to_local_bin()
    if args.clear_logs:
        clear_log_file(args.outfile)

    # Initialize logging and other setup only after handling exit-early commands
    LOG_FILE_PATH = args.outfile
    logging.basicConfig(
        filename=LOG_FILE_PATH,
        level=logging.DEBUG,
        format="%(asctime)s - %(message)s",
    )
    if not os.path.exists('upload'):
        os.makedirs('upload')

    if args.timeout:
        print(f"{YELLOW}[i] Server will automatically shut down in {args.timeout} seconds.{RESET}")
        timer = threading.Timer(args.timeout, shutdown_server, args=[args.timeout])
        timer.daemon = True
        timer.start()

    if args.auth:
        try:
            args.auth_user, args.auth_pass = args.auth.split(':', 1)
        except ValueError:
            print(f"{RED}[!] Invalid auth format. Use username:password.{RESET}")
            sys.exit(1)
    
    check_and_install_dependencies(args)
    check_tunnel_dependencies(args)
        
    if not is_port_available(args.port):
        print(f"{RED}[!] Port {args.port} is already in use. Choose a different port.{RESET}")
        sys.exit(1)
    
    threading.Thread(target=start_http_server, args=(args.directory, args.port, args), daemon=True).start()

    if not any([args.serveo, args.cloudflared, args.ngrok, args.localtunnel]):
        bind_address = "127.0.0.1" if args.single_host else "0.0.0.0"
        print(f"{YELLOW}[i] No tunnel selected. Serving locally on {bind_address}:{args.port}.{RESET}")
        if args.single_file_to_serve:
            print(f"{YELLOW}[i] Serving single file: {args.single_file_to_serve}{RESET}")
            print(f"{YELLOW}[i] Access it at: {WHITE}http://{bind_address}:{args.port}/{args.single_file_to_serve}{RESET}")
        else:
            print(f"{YELLOW}[i] Access it at: {WHITE}http://{bind_address}:{args.port}{RESET}")
        
        # Keep the main thread alive so the daemon HTTP server thread continues to run
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{RED}[!] Local server stopped by user. Exiting...{RESET}")
            sys.exit(0)
    else:
        # Start selected tunnel
        if args.serveo:
            start_serveo_tunnel(args.port)
        elif args.cloudflared:
            start_cloudflared_tunnel(args.port)
        elif args.ngrok:
            start_ngrok_tunnel(args.port)
        elif args.localtunnel:
            start_localtunnel(args.port)



if __name__ == "__main__":
    print_banner()
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}[!] Interrupted by user. Exiting...{RESET}")
        sys.exit(0)
