import subprocess
import socket
import threading
import time
import json
from datetime import datetime
from typing import List, Dict, Optional
import ipaddress
import psutil
import ping3

class NetworkMonitor:
    """
    Core network monitoring class that handles device discovery and bandwidth tracking.
    
    This class implements several networking concepts:
    1. Network discovery through ping sweeps and ARP table analysis
    2. Bandwidth monitoring through system network interface statistics
    3. Connection quality measurement through ping latency testing
    """

    def __init__(self, network_range: str = None):
        """
        Initialize the network monitor.
        
        Args:
            network_range: Network CIDR (e.g., '192.168.1.0/24'). 
                          If None, will auto-detect local network.
        """
        self.network_range = network_range or self._get_local_network()
        self.devices = {}
        self.monitoring = False
        self.monitoring_thread = None
    
    def _get_local_network(self) -> str:
        """
        Auto-detect the local network range.
        
        How this works:
        1. Get the default gateway (your router's IP)
        2. Get your device's IP address
        3. Calculate the network range (usually /24 for home networks)
        
        Returns:
            Network CIDR string (e.g., '192.168.1.0/24')
        """
        try:
            # get default gateway (router IP)
            result = subprocess.run(['ip', 'route', 'show', 'default'],
                                    capture_output=True, text=True)
            gateway = result.stdout.split()[2]

            # get local IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect((gateway, 80))
            local_ip = sock.getsockname()[0]
            sock.close()

            # calculate network (assuming /24 subnet)
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            
            return str(network.network_address) + "/24"
        except Exception as e:
            # fallback to common home network range
            print(f"Could not auto-detect network using default: {e}")
            return "192.168.1.0/24"
    
    
