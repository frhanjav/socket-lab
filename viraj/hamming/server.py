# server.py
import socket
import threading
import random
from rich.console import Console
from rich.text import Text

HOST = '0.0.0.0'
PORT = 5000

# Adjustable error probabilities (0.0 to 1.0)
SINGLE_BIT_ERROR_PROBABILITY = 0.5  # 10% chance of single bit error
DOUBLE_BIT_ERROR_PROBABILITY = 0.3  # 5% chance of double bit error

clients = {}  # user_id -> connection
lock = threading.Lock()

# Initialize Rich console for colored output
console = Console()

class ClientHandler(threading.Thread):
    def __init__(self, conn: socket.socket, addr):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.user_id = None

    def introduce_bit_errors(self, hamming_data):
        if not hamming_data or len(hamming_data) == 0:
            return hamming_data, {'errors_introduced': False, 'error_type': None, 'positions': []}
        
        data_list = list(hamming_data)
        error_info = {'errors_introduced': False, 'error_type': None, 'positions': []}
        
        # Check for double bit error first (more severe)
        if random.random() < DOUBLE_BIT_ERROR_PROBABILITY:
            # Introduce double bit error
            positions = random.sample(range(len(data_list)), min(2, len(data_list)))
            for pos in positions:
                data_list[pos] = '1' if data_list[pos] == '0' else '0'
            
            error_info = {
                'errors_introduced': True,
                'error_type': 'double',
                'positions': [p + 1 for p in positions]  # Convert to 1-indexed
            }
            
        elif random.random() < SINGLE_BIT_ERROR_PROBABILITY:
            # Introduce single bit error
            pos = random.randint(0, len(data_list) - 1)
            data_list[pos] = '1' if data_list[pos] == '0' else '0'
            
            error_info = {
                'errors_introduced': True,
                'error_type': 'single',
                'positions': [pos + 1]  # Convert to 1-indexed
            }
        
        return ''.join(data_list), error_info

    def run(self) -> None:
        try:
            # Ask for user ID
            prompt_msg = "Enter your user ID:\n"
            self.conn.sendall(prompt_msg.encode('utf-8'))
            data = self.conn.recv(1024).decode('utf-8').strip()
            self.user_id = data

            with lock:
                clients[self.user_id] = self.conn
            
            # Server message in cyan
            server_msg = Text(f"[SERVER] {self.user_id} connected from {self.addr}", style="cyan bold")
            console.print(server_msg)

            # Listen for messages and forward with potential errors
            while True:
                raw = self.conn.recv(4096)
                if not raw:
                    break
                
                try:
                    msg_text = raw.decode('utf-8')
                except UnicodeDecodeError:
                    error_msg = Text(f"[SERVER] Unicode decode error from {self.user_id}", style="red")
                    console.print(error_msg)
                    continue

                # Expect format: recipient_id|original_message|hamming_encoded_data
                parts = msg_text.split('|', 2)
                if len(parts) != 3:
                    error_msg = Text(f"[SERVER] Invalid message format from {self.user_id}", style="red")
                    console.print(error_msg)
                    continue
                
                recipient, original_msg, hamming_payload = parts
                
                # Log message forwarding
                forward_msg = Text(f"[SERVER] Forwarding from {self.user_id} → {recipient}", style="yellow")
                console.print(forward_msg)
                
                # Introduce potential bit errors during transmission
                corrupted_hamming, error_info = self.introduce_bit_errors(hamming_payload)
                
                # Log error introduction
                if error_info['errors_introduced']:
                    if error_info['error_type'] == 'single':
                        error_msg = Text(f"[SERVER] 🔴 Introduced SINGLE bit error at position {error_info['positions'][0]}", 
                                       style="red bold")
                    else:  # double
                        error_msg = Text(f"[SERVER] 🔴🔴 Introduced DOUBLE bit errors at positions {error_info['positions']}", 
                                       style="red bold on white")
                    console.print(error_msg)
                else:
                    clean_msg = Text(f"[SERVER] ✅ Clean transmission (no errors introduced)", style="green")
                    console.print(clean_msg)

                # Forward to recipient
                with lock:
                    target = clients.get(recipient)
                if target:
                    # Forward the payload with potential corruption: original_message|hamming_encoded_data
                    forward_payload = f"{original_msg}|{corrupted_hamming}"
                    target.sendall(forward_payload.encode('utf-8'))
                    
                    success_msg = Text(f"[SERVER] ✉️  Message delivered to {recipient}", style="green")
                    console.print(success_msg)
                else:
                    # Notify sender that recipient is not available
                    not_found_msg = f"SERVER_ERROR|User '{recipient}' not found or offline"
                    self.conn.sendall(not_found_msg.encode('utf-8'))
                    
                    error_msg = Text(f"[SERVER] ❌ Recipient {recipient} not found", style="red")
                    console.print(error_msg)
                    
        except Exception as e:
            error_msg = Text(f"[SERVER] Error handling client {self.user_id}: {e}", style="red bold")
            console.print(error_msg)
        finally:
            with lock:
                if self.user_id:
                    clients.pop(self.user_id, None)
            self.conn.close()
            
            disconnect_msg = Text(f"[SERVER] {self.user_id or 'Unknown'} disconnected", style="cyan")
            console.print(disconnect_msg)


def start_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        
        # Server startup message in bright green
        startup_msg = Text(f"[SERVER] Hamming Chat Server listening on {HOST}:{PORT}...", style="bright_green bold")
        console.print(startup_msg)
        
        # Show error simulation settings
        settings_msg = Text(f"[SERVER] Error Simulation Settings:", style="blue bold")
        console.print(settings_msg)
        console.print(Text(f"  • Single bit error probability: {SINGLE_BIT_ERROR_PROBABILITY:.1%}", style="yellow"))
        console.print(Text(f"  • Double bit error probability: {DOUBLE_BIT_ERROR_PROBABILITY:.1%}", style="red"))
        console.print(Text(f"[SERVER] Server ready - forwarding messages with potential bit errors", style="blue"))
        
        try:
            while True:
                conn, addr = s.accept()
                ClientHandler(conn, addr).start()
        except KeyboardInterrupt:
            shutdown_msg = Text("[SERVER] Server shutting down...", style="bright_red bold")
            console.print(shutdown_msg)

if __name__ == '__main__':
    start_server()