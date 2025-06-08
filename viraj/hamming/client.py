# client.py
import socket
import threading
import logging
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt
from rich.panel import Panel
from hamming_utils import HammingCode

HOST = '127.0.0.1'
PORT = 5000

console = Console()
hamming = HammingCode()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('client_hamming.log')
    ]
)

def receive(sock: socket.socket, user_id: str) -> None:
    try:
        while True:
            raw = sock.recv(4096).decode('utf-8')
            if not raw:
                break
            
            if raw.startswith("SERVER_ERROR|"):
                error_content = raw.split("|", 1)[1]
                error_msg = Text(f"[ERROR] {error_content}", style="red bold")
                console.print(error_msg)
                console.print(Text("[CLIENT] You: ", style="bright_blue bold", end=""))
                continue
            
            parts = raw.split('|', 1)
            if len(parts) != 2:
                error_msg = Text("[CLIENT] Invalid message format received", style="red")
                console.print(error_msg)
                console.print(Text("[CLIENT] You: ", style="bright_blue bold", end=""))
                continue
            
            original_msg, hamming_payload = parts
            
            try:
                decoded_msg, error_info = hamming.decode(hamming_payload)
                
                if not error_info['repairable']:
                    error_panel = Panel(
                        Text("Non-repairable transmission error detected!\nMessage corrupted and cannot be recovered.", 
                             style="red bold"),
                        title="[red]TRANSMISSION ERROR[/red]",
                        border_style="red"
                    )
                    console.print(error_panel)
                    console.print(Text("[CLIENT] You: ", style="bright_blue bold", end=""))
                    continue
                
                # Display the message
                if error_info['error_detected'] and error_info['error_corrected']:
                    # Message with corrected error
                    corrected_panel = Panel(
                        Text(f"{decoded_msg}", style="bright_white"),
                        title=f"[yellow]MESSAGE (Error Corrected at bit {error_info['error_position']})[/yellow]",
                        border_style="yellow"
                    )
                    console.print(corrected_panel)
                else:
                    # Clean message
                    message_panel = Panel(
                        Text(f"{decoded_msg}", style="bright_white"),
                        title="[green]MESSAGE[/green]",
                        border_style="green"
                    )
                    console.print(message_panel)
                
                # Verify message integrity by comparing with original
                if decoded_msg != original_msg:
                    warning_msg = Text(
                        f"[WARNING] Decoded message differs from original transmission!",
                        style="yellow bold"
                    )
                    console.print(warning_msg)
                
            except Exception as e:
                error_msg = Text(f"[CLIENT] Error decoding message: {e}", style="red bold")
                console.print(error_msg)
            
            # Show input prompt again
            console.print(Text("[CLIENT] You: ", style="bright_blue bold", end=""))
            
    except ConnectionResetError:
        disconnect_msg = Text("[CLIENT] Connection lost to server", style="red bold")
        console.print(disconnect_msg)
    except Exception as e:
        error_msg = Text(f"[CLIENT] Receive error: {e}", style="red bold")
        console.print(error_msg)


def start_client() -> None:
    """Start the Hamming chat client"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Connect to server
            s.connect((HOST, PORT))
            
            # Welcome message
            welcome_panel = Panel(
                Text("Welcome to Hamming Chat Client!\nError detection and correction enabled.", 
                     style="bright_cyan"),
                title="[bright_green]HAMMING CHAT[/bright_green]",
                border_style="bright_green"
            )
            console.print(welcome_panel)
            
            # Receive and handle server prompt for user ID
            data = s.recv(1024)
            prompt = data.decode('utf-8').strip()
            
            # Get user ID with Rich prompt
            user_id = Prompt.ask("[bright_yellow]Enter your user ID[/bright_yellow]")
            s.sendall(user_id.encode('utf-8'))
            
            # Start receive thread
            threading.Thread(target=receive, args=(s, user_id), daemon=True).start()
            
            # Show usage instructions
            usage_panel = Panel(
                Text("Usage: recipient_id/Your message here\nType '/quit' to exit", 
                     style="bright_white"),
                title="[blue]INSTRUCTIONS[/blue]",
                border_style="blue"
            )
            console.print(usage_panel)
            
            # Main message loop
            while True:
                try:
                    text = Prompt.ask("[bright_blue][CLIENT] You[/bright_blue]")
                    
                    if text.lower() == '/quit':
                        break
                    
                    # Parse recipient and message
                    if '/' not in text:
                        error_msg = Text("Invalid format! Use: recipient_id/message", style="red")
                        console.print(error_msg)
                        continue
                    
                    recipient, message = text.split('/', 1)
                    
                    if not recipient.strip() or not message.strip():
                        error_msg = Text("Both recipient and message are required!", style="red")
                        console.print(error_msg)
                        continue
                    
                    # Encode message with Hamming code
                    try:
                        hamming_encoded = hamming.encode(message)
                        
                        # Construct payload: recipient|original_message|hamming_encoded_data
                        payload = f"{recipient.strip()}|{message}|{hamming_encoded}"
                        s.sendall(payload.encode('utf-8'))
                        
                        # Show encoding confirmation
                        encode_msg = Text(
                            f"Message sent to {recipient} ({len(hamming_encoded)} bits encoded)",
                            style="green"
                        )
                        console.print(encode_msg)
                        
                    except Exception as e:
                        error_msg = Text(f"Encoding error: {e}", style="red bold")
                        console.print(error_msg)
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    error_msg = Text(f"Input error: {e}", style="red")
                    console.print(error_msg)
    
    except ConnectionRefusedError:
        error_panel = Panel(
            Text(f"Cannot connect to server at {HOST}:{PORT}\nMake sure the server is running!", 
                 style="red bold"),
            title="[red]CONNECTION ERROR[/red]",
            border_style="red"
        )
        console.print(error_panel)
    except Exception as e:
        error_msg = Text(f"Client error: {e}", style="red bold")
        console.print(error_msg)
    finally:
        goodbye_msg = Text("Goodbye! Hamming Chat Client closed.", style="bright_cyan")
        console.print(goodbye_msg)


if __name__ == '__main__':
    start_client()