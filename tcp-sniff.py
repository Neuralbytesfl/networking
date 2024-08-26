import scapy.all as scapy
import psutil
import os
import time
import logging
import socket
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box
from threading import Thread, Event

# Initialize rich console
console = Console()

# Configure logging
logging.basicConfig(filename="network_activity.log", level=logging.INFO, 
                    format="%(asctime)s - %(message)s", filemode="w")

# Dictionary to store packets count and process information
packet_stats = defaultdict(lambda: {"count": 0, "pid": None, "process_name": None, "local_port": None, "new": True, "last_seen": time.time()})

# Cache for resolving and storing hostnames
hostname_cache = {}

# Time after which an inactive connection will be removed (in seconds)
INACTIVITY_TIMEOUT = 60  # Adjust this value as needed

# Event to stop the packet sniffer thread
stop_event = Event()

def resolve_hostname(ip):
    if ip not in hostname_cache:
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except socket.herror:
            hostname = ip
        hostname_cache[ip] = hostname
    return hostname_cache[ip]

def get_process_info(ip, port):
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.ip == ip and conn.laddr.port == port:
                return conn.pid
    except psutil.AccessDenied:
        return None
    return None

def update_packet_stats(packet):
    try:
        if packet.haslayer(scapy.IP):
            src_ip = packet[scapy.IP].src
            dst_ip = packet[scapy.IP].dst
            protocol = packet[scapy.IP].proto

            # Resolve hostnames
            src_hostname = resolve_hostname(src_ip)
            dst_hostname = resolve_hostname(dst_ip)

            # Assume TCP/UDP packets, try to retrieve port numbers and use them
            sport = packet[scapy.TCP].sport if protocol == 6 else packet[scapy.UDP].sport if protocol == 17 else None
            dport = packet[scapy.TCP].dport if protocol == 6 else packet[scapy.UDP].dport if protocol == 17 else None

            if sport is not None:
                pid = get_process_info(src_ip, sport)
                if pid is None and dport is not None:
                    pid = get_process_info(dst_ip, dport)
                
                process_name = psutil.Process(pid).name() if pid else "Unknown"
                
                key = (src_hostname, dst_hostname, pid, sport)
                if key not in packet_stats:
                    packet_stats[key]["new"] = True
                    logging.info(f"New connection: {src_hostname}:{sport} -> {dst_hostname}, PID: {pid}, Process: {process_name}")
                
                # Update the packet stats
                packet_stats[key]["count"] += 1
                packet_stats[key]["pid"] = pid
                packet_stats[key]["process_name"] = process_name
                packet_stats[key]["local_port"] = sport
                packet_stats[key]["last_seen"] = time.time()
    except Exception as e:
        logging.error(f"Error updating packet stats: {e}")

def remove_inactive_connections():
    current_time = time.time()
    keys_to_remove = [key for key, value in packet_stats.items() if current_time - value["last_seen"] > INACTIVITY_TIMEOUT]
    for key in keys_to_remove:
        del packet_stats[key]

def create_packet_stats_table():
    table = Table(title="Network Activity Monitor", box=box.SQUARE)
    table.add_column("Source Hostname", style="cyan", no_wrap=True)
    table.add_column("Destination Hostname", style="magenta")
    table.add_column("Local Port", style="blue")
    table.add_column("Process Name", style="green")
    table.add_column("PID", style="yellow")
    table.add_column("Packets", style="red")

    for key, value in packet_stats.items():
        src_hostname, dst_hostname, pid, local_port = key
        process_name = value["process_name"] if value["process_name"] else "Unknown"
        pid_str = str(pid) if pid is not None else "N/A"
        count = value["count"]
        row_style = "bold" if value["new"] else ""
        table.add_row(src_hostname, dst_hostname, str(local_port), process_name, pid_str, str(count), style=row_style)
        value["new"] = False
    
    return table

def packet_sniffer(interface):
    try:
        scapy.sniff(iface=interface, prn=update_packet_stats, store=False, stop_filter=lambda x: stop_event.is_set())
    except PermissionError:
        console.print("[bold red]You need to run this script as an administrator or root.[/bold red]")
    except Exception as e:
        logging.error(f"Error in packet sniffer: {e}")

def list_interfaces():
    interfaces = psutil.net_if_addrs()
    console.print("Available Network Interfaces:", style="bold green")
    for i, interface in enumerate(interfaces.keys()):
        console.print(f"{i}. {interface}", style="cyan")
    return list(interfaces.keys())

def main():
    available_interfaces = list_interfaces()
    choice = int(console.input("[bold yellow]Enter the number of the interface you want to monitor: [/bold yellow]"))

    if 0 <= choice < len(available_interfaces):
        interface = available_interfaces[choice]
        console.print(f"Monitoring interface: [bold magenta]{interface}[/bold magenta]")
        os.system("cls")
        # Start the packet sniffer in a separate thread
        sniffer_thread = Thread(target=packet_sniffer, args=(interface,))
        sniffer_thread.start()

        try:
            with Live(create_packet_stats_table(), refresh_per_second=1, console=console) as live:
                while True:
                    remove_inactive_connections()  # Remove old connections before updating the table
                    live.update(create_packet_stats_table())
                    time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[bold red]Stopping packet sniffer...[/bold red]")
            stop_event.set()
            sniffer_thread.join()
            console.print("[bold green]Done.[/bold green]")
    else:
        console.print("[bold red]Invalid choice. Exiting.[/bold red]")

if __name__ == "__main__":
    main()
