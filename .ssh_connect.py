import paramiko
import sys
import socket

host = "Andmax.local"
user = "andmax"
pw = "123456"

# Resolve hostname
try:
    ip = socket.getaddrinfo(host, 22, socket.AF_INET)[0][4][0]
    print(f"Resolved {host} -> {ip}")
except Exception:
    ip = host
    print(f"Using hostname directly: {host}")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {user}@{ip}...")
    client.connect(ip, port=22, username=user, password=pw, timeout=10)
    print("CONNECTED!\n")

    # Run commands
    commands = sys.argv[1] if len(sys.argv) > 1 else "hostname && uname -a && docker ps 2>&1"
    stdin, stdout, stderr = client.exec_command(commands)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("STDERR:", err)

except Exception as e:
    print(f"ERROR: {e}")
finally:
    client.close()
