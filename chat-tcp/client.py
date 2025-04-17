import socket
import threading
import sys

def receive(sock, username):
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print("\nServer disconnected")
                sock.close()
                sys.exit(0)
            print(f"\n{data.decode()}")
            print(f"You ({username}): ", end="", flush=True)
    except ConnectionResetError:
        print("\nServer disconnected")
    except OSError:
        # Socket was closed
        pass
    finally:
        print("\nDisconnected from server")
        sock.close()
        sys.exit(0)

def main():
    HOST = '127.0.0.1'
    PORT = 12345
    
    username = input("Enter your username: ")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        print(f"Connected to server as {username}")
        
        # Send username to server
        s.sendall(f"USERNAME:{username}".encode())
        
        # Start receive thread
        threading.Thread(target=receive, args=(s, username), daemon=True).start()
        
        # Main send loop
        try:
            while True:
                msg = input(f"You ({username}): ")
                if msg.lower() == 'exit':
                    print("Disconnecting...")
                    break
                s.sendall(msg.encode())
        except KeyboardInterrupt:
            print("\nDisconnecting...")
        finally:
            s.close()
            sys.exit(0)
            
    except ConnectionRefusedError:
        print("Could not connect to server. Is it running?")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()