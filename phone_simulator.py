import socket
import time
import argparse

def simulate_heartbeat(target_ip, target_port, continuous):
    """Simulates a phone sending a heartbeat to the PC."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    phone_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        phone_ip = s.getsockname()[0]
        s.close()
    except OSError as e:
        print(f"Network discovery failed: {e}")
        
    adb_port = 5555
    msg = f"HELLO_USER|{phone_ip}|{adb_port}"
    
    print(f"Starting heartbeat simulation to {target_ip}:{target_port}")
    
    try:
        while True:
            print(f"Sending heartbeat: {msg}")
            sock.sendto(msg.encode('utf-8'), (target_ip, target_port))
            
            if not continuous:
                break
                
            time.sleep(4)
    except KeyboardInterrupt:
        print("Simulation stopped by user.")
    finally:
        sock.close()

def main():
    """Main entry point for phone simulator."""
    parser = argparse.ArgumentParser(description="Phone Heartbeat Simulator")
    parser.add_argument("--ip", default="127.0.0.1", help="Target IP address")
    parser.add_argument("--port", type=int, default=5556, help="Target port")
    parser.add_argument("--continuous", action="store_true", help="Send heartbeats continuously")
    
    args = parser.parse_args()
    simulate_heartbeat(args.ip, args.port, args.continuous)

if __name__ == "__main__":
    main()
