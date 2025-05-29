#### Setting up server-to-server communication through WireGurad
# Servers can communicate through WireGuard, encrypting packets on network level. It removes the necessity to use HTTPS aplication-level encryption between servers.

### Setting up WireGuard tunnel
# Between server "benjamin-franklin" with public static ip "7.7.7.7"
# And server "tomasz-jefferson" with public static ip "8.8.8.8"
# Using example 10.0.1.0, 10.0.2.0 adresses for WireGuard interafce wg0, listening on port 8000

## Check normal connection using public ip and default network interface eth0
# benjamin-franklin
sudo tcpdump -i eth0 udp 'port 8000'
# tomasz-jefferson
nc -vz -u 7.7.7.7 8000

## On "benjamin-franklin" server

# Enable ip forwarding
Uncomment "net.ipv4.ip_forward = 1" in file "/etc/sysctl.conf"
# Apply changes
```sudo sysctl -p```
# Check settings - the follownig command should output "1"
```cat /proc/sys/net/ipv4/ip_forward```

## Install and run WireGuard
# Root privledges required
```
sudo su
apt install wireguard
cd /etc/wireguard/
```
# Generate private-public key pair 
```
wg genkey | tee franklin-privatekey | wg pubkey > franklin-publickey
chmod 600 franklin-*
```
# Create file "wg0.conf" with the following content:
```bash
[Interface]
## Local Address : A private IP address for wg0 interface.
Address = 10.0.1.0/24
ListenPort = 8000

## Benjamin Franklin
# paste generated private key
PrivateKey = 

[Peer]
## Tomasz Jefferson
# paste peer's public key
PublicKey = 
Endpoint = 8.8.8.8:8000
AllowedIPs = 10.0.1.0/24
```

# Create WireGuard network interface "wg0"
```bash
chmod 600 wg0.conf
systemctl start wg-quick@wg0
systemctl enable wg-quick@wg0
```

# Each time after adding a peer, reload
```systemctl reload wg-quick@wg0```

## On "tomasz-jefferson" server
# Repeat the steps made on benjamin-franklin
# File "wg0.conf" should look like this:
```bash
[Interface]
## Local Address : A private IP address for wg0 interface.
Address = 10.0.3.0/24
ListenPort = 8000

## Tomasz Jefferson
# paste generated private key
PrivateKey = 

[Peer]
## Benjamin Franklin
# paste peer's public key
PublicKey = 
Endpoint = 7.7.7.7:8000
AllowedIPs = 10.0.1.0/24
```

## Check WireGuard connection
# benjamin-franklin
sudo tcpdump -i wg0
# tomasz-jefferson
nc -vz -u 10.0.1.0 8000

### Running the backend
# If you run the backend on port 8000, use WireGuard for server-server communication, but use public ips for client-server communication, file ".env" should look like this:
```bash
TRUSTED_IPS = 'None, None, None'
SERVERS = 'http://7.7.7.7:8000, http://8.8.8.8:8000, http://9.9.9.9:8000'
WIREGUARD_IPS = '10.0.1.0, 10.0.2.0, 10.0.3.0'
WIREGUARD_SERVERS = '10.0.1.0:8000, 10.0.2.0:8000, 10.0.3.0:8000'
```

# Run the server
```uv run uvicorn api.__init__:app --host 0.0.0.0 --port 8000```