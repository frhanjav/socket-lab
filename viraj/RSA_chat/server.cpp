// Compile: g++ server.cpp -o server.exe -lws2_32 -lstdc++
// Run:     .\server.exe

#define _WIN32_WINNT 0x0600

// Standard headers
#include <process.h>   // For _beginthreadex, _endthreadex
#include <stdio.h>     // For printf, scanf, fgets, fprintf, etc.
#include <string.h>    // For memset, strlen, strcspn
#include <windows.h>   // For HANDLE, CreateEvent, etc.
#include <winsock2.h>  // For socket functions

#include <map>        // For storing user IDs
#include <stdexcept>  // For exception handling
#include <string>     // Include C++ string
#include <vector>     // Include C++ vector

// Include our RSA header
#include "rsa_chat.hpp"

#pragma comment(lib, "ws2_32.lib")

#define BUFFER_SIZE 8192  // For encrypted messages

// Helper function to log crypto details
void LogCryptoData(const std::string& received_serialized) {
    printf("\n[CRYPTO] Received binary (%zu bytes): ",
           received_serialized.size());
    // Show up to 32 bytes of hex data with line breaks for readability
    for (size_t i = 0; i < received_serialized.size(); i++) {
        printf("%02X ", (unsigned char)received_serialized[i]);
        // Add a line break every 16 bytes for readability
        if ((i + 1) % 16 == 0 && i + 1 < received_serialized.size()) {
            printf("\n                              ");
        }
    }

    printf("\n[CRYPTO] Received string (ASCII): ");
    // Show all data with non-printable characters as dots
    for (size_t i = 0; i < received_serialized.size(); i++) {
        printf("%c",
               isprint(received_serialized[i]) ? received_serialized[i] : '.');
        // Add a line break every 64 characters for readability
        if ((i + 1) % 64 == 0 && i + 1 < received_serialized.size()) {
            printf("\n                              ");
        }
    }
    printf("\n");
}

// Simple lock guard class for CRITICAL_SECTION
class CSLock {
   private:
    CRITICAL_SECTION& cs;

   public:
    CSLock(CRITICAL_SECTION& critical_section) : cs(critical_section) {
        EnterCriticalSection(&cs);
    }
    ~CSLock() { LeaveCriticalSection(&cs); }
};

// Client session structure
struct ClientSession {
    SOCKET socket;
    std::vector<long long> public_key;
    HANDLE thread;
    HANDLE event;
    std::string user_id;
    bool connected;
};

class ChatServer {
   private:
    bool m_running;
    SOCKET m_server_socket;
    std::vector<long long> m_server_public_key;
    std::vector<long long> m_server_private_key;
    int m_port;
    std::map<SOCKET, ClientSession> m_clients;
    CRITICAL_SECTION m_clients_cs;

    struct ReceiverThreadArgs {
        ChatServer* server;
        SOCKET clientSocket;
        HANDLE hEvent;
    };

    // Internal methods
    bool initWinsock();
    bool createServerSocket();
    bool bindAndListen();
    bool acceptClients();
    bool exchangeKeys(SOCKET clientSocket);
    bool startClientReceiver(SOCKET clientSocket);
    void cleanupClient(SOCKET clientSocket);
    void cleanupAllClients();
    void stopServer();
    bool forwardMessageToClient(const std::string& recipient_id,
                                const std::string& sender_id,
                                const std::string& message,
                                SOCKET senderSocket);
    bool sendErrorToClient(SOCKET clientSocket,
                           const std::string& error_message);
    static unsigned __stdcall clientReceiverThreadFunc(void* args_ptr);
    void handleReceivedMessage(SOCKET clientSocket,
                               const std::string& received_msg);

   public:
    ChatServer(int port);
    ~ChatServer();
    bool initialize();
    void run();
    void shutdown() { stopServer(); }
};

// Constructor initializes member variables
ChatServer::ChatServer(int port)
    : m_running(false),
      m_server_socket(INVALID_SOCKET),
      m_server_public_key({5, 323}),     // {e, n}
      m_server_private_key({173, 323}),  // {d, n}
      m_port(port) {
    InitializeCriticalSection(&m_clients_cs);
}

// Destructor ensures cleanup
ChatServer::~ChatServer() {
    shutdown();
    DeleteCriticalSection(&m_clients_cs);
}

// Initialize Winsock
bool ChatServer::initWinsock() {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "WSAStartup failed. Error: %d\n", WSAGetLastError());
        return false;
    }
    return true;
}

// Create server socket
bool ChatServer::createServerSocket() {
    if ((m_server_socket = socket(AF_INET, SOCK_STREAM, 0)) == INVALID_SOCKET) {
        fprintf(stderr, "Socket creation failed. Error: %d\n",
                WSAGetLastError());
        return false;
    }
    return true;
}

// Bind socket and start listening
bool ChatServer::bindAndListen() {
    struct sockaddr_in server_addr = {0};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(m_port);

    if (bind(m_server_socket, (struct sockaddr*)&server_addr,
             sizeof(server_addr)) == SOCKET_ERROR ||
        listen(m_server_socket, SOMAXCONN) == SOCKET_ERROR) {
        fprintf(stderr, "Bind/Listen failed. Error: %d\n", WSAGetLastError());
        return false;
    }

    printf("Server is listening on port %d...\n", m_port);
    return true;
}

// Exchange keys with client
bool ChatServer::exchangeKeys(SOCKET clientSocket) {
    char comm_buffer[BUFFER_SIZE];
    char client_user_id[256] = {0};
    std::vector<long long> client_public_key;

    try {
        // Send server's public key
        snprintf(comm_buffer, sizeof(comm_buffer), "%lld %lld",
                 m_server_public_key[0], m_server_public_key[1]);
        if (send(clientSocket, comm_buffer, strlen(comm_buffer), 0) <= 0)
            throw std::runtime_error("Send server key failed");

        // Receive client's public key and user ID
        memset(comm_buffer, 0, sizeof(comm_buffer));
        int key_recv_len =
            recv(clientSocket, comm_buffer, sizeof(comm_buffer) - 1, 0);
        if (key_recv_len <= 0)
            throw std::runtime_error("Receive client key failed");
        comm_buffer[key_recv_len] = '\0';

        long long client_e, client_n;
        if (sscanf(comm_buffer, "%lld %lld %255s", &client_e, &client_n,
                   client_user_id) >= 2) {
            client_public_key = {client_e, client_n};
            std::string user_id =
                strlen(client_user_id) > 0 ? client_user_id : "(unknown)";

            // Store client information
            {
                CSLock lock(m_clients_cs);
                m_clients[clientSocket].public_key = client_public_key;
                m_clients[clientSocket].user_id = user_id;

                printf(
                    "[System] Client connected: %s (Socket: %llu), Key: "
                    "{e=%lld, n=%lld}\n",
                    user_id.c_str(), (unsigned long long)clientSocket,
                    client_public_key[0], client_public_key[1]);

                // Show connected users
                printf("[System] Connected users: ");
                for (const auto& client : m_clients)
                    if (client.second.connected)
                        printf("%s ", client.second.user_id.c_str());
                printf("\n");
            }
        } else {
            throw std::runtime_error("Parse client key failed");
        }
    } catch (const std::exception& e) {
        fprintf(stderr, "[System] Key exchange error: %s (WSAError: %d)\n",
                e.what(), WSAGetLastError());
        return false;
    }

    return true;
}

// Handle received messages
void ChatServer::handleReceivedMessage(SOCKET clientSocket,
                                       const std::string& received_serialized) {
    // Display crypto debug info
    LogCryptoData(received_serialized);

    std::vector<long long> ciphertext =
        deserialize_ciphertext(received_serialized);

    if (ciphertext.empty()) {
        printf(received_serialized.empty() || received_serialized == " "
                   ? "\n[Client]: (empty message)\n"
                   : "\n[System] Received invalid data: '%.50s'...\n",
               received_serialized.c_str());
        return;
    }

    // Decrypt and process message
    std::string decrypted_message = decrypt(ciphertext, m_server_private_key);
    printf("[CRYPTO] Decrypted message: %s\n\n", decrypted_message.c_str());

    // Get sender ID
    std::string sender_id = "Client";
    {
        CSLock lock(m_clients_cs);
        auto it = m_clients.find(clientSocket);
        if (it != m_clients.end()) sender_id = it->second.user_id;
    }

    // Check if it's a direct message (recipient/message format)
    size_t separator_pos = decrypted_message.find('/');
    if (separator_pos != std::string::npos) {
        // Extract recipient and content
        std::string recipient_id = decrypted_message.substr(0, separator_pos);
        std::string message_content =
            decrypted_message.substr(separator_pos + 1);

        // Trim whitespace
        recipient_id.erase(0, recipient_id.find_first_not_of(" \t"));
        recipient_id.erase(recipient_id.find_last_not_of(" \t") + 1);

        printf("\n[%s→%s]: %s\n", sender_id.c_str(), recipient_id.c_str(),
               message_content.c_str());

        // Look for recipient and forward message
        bool recipient_found = false;
        {
            CSLock lock(m_clients_cs);
            for (const auto& client : m_clients) {
                if (client.second.user_id == recipient_id &&
                    client.second.connected) {
                    if (forwardMessageToClient(recipient_id, sender_id,
                                               message_content, clientSocket))
                        printf("[System] Message forwarded to %s\n",
                               recipient_id.c_str());
                    else {
                        printf("[System] Failed to forward to %s\n",
                               recipient_id.c_str());
                        sendErrorToClient(
                            clientSocket,
                            "Failed to deliver to " + recipient_id);
                    }
                    recipient_found = true;
                    break;
                }
            }
        }

        if (!recipient_found) {
            printf("[System] User '%s' not found\n", recipient_id.c_str());
            sendErrorToClient(clientSocket,
                              "Error: User '" + recipient_id + "' not found");
        }
    } else {
        // Regular message
        printf("\n[%s]: %s\n", sender_id.c_str(), decrypted_message.c_str());
    }
}

// Forward a message from one client to another
bool ChatServer::forwardMessageToClient(const std::string& recipient_id,
                                        const std::string& sender_id,
                                        const std::string& message,
                                        SOCKET senderSocket) {
    // Find recipient socket and public key
    SOCKET recipient_socket = INVALID_SOCKET;
    std::vector<long long> recipient_public_key;

    {
        CSLock lock(m_clients_cs);
        for (const auto& client : m_clients) {
            if (client.second.user_id == recipient_id &&
                client.second.connected) {
                recipient_socket = client.first;
                recipient_public_key = client.second.public_key;
                break;
            }
        }
    }

    if (recipient_socket == INVALID_SOCKET || recipient_public_key.empty())
        return false;

    // Format and encrypt the message
    std::string formatted_message = "[DM from " + sender_id + "]: " + message;
    std::vector<long long> ciphertext =
        encrypt(formatted_message, recipient_public_key);
    std::string serialized_ciphertext = serialize_ciphertext(ciphertext);

    return send(recipient_socket, serialized_ciphertext.c_str(),
                serialized_ciphertext.length(), 0) > 0;
}

// Send error message back to client
bool ChatServer::sendErrorToClient(SOCKET clientSocket,
                                   const std::string& error_message) {
    std::vector<long long> client_public_key;

    {
        CSLock lock(m_clients_cs);
        auto it = m_clients.find(clientSocket);
        if (it == m_clients.end() || !it->second.connected) return false;
        client_public_key = it->second.public_key;
    }

    if (client_public_key.empty()) return false;

    std::vector<long long> ciphertext =
        encrypt(error_message, client_public_key);
    std::string serialized_ciphertext = serialize_ciphertext(ciphertext);

    return send(clientSocket, serialized_ciphertext.c_str(),
                serialized_ciphertext.length(), 0) > 0;
}

// Client receiver thread function
unsigned __stdcall ChatServer::clientReceiverThreadFunc(void* args_ptr) {
    ReceiverThreadArgs* thread_args = (ReceiverThreadArgs*)args_ptr;
    ChatServer* server = thread_args->server;
    SOCKET clientSocket = thread_args->clientSocket;
    HANDLE hEvent = thread_args->hEvent;

    char recv_buffer[BUFFER_SIZE];
    int recv_len;
    std::string user_id = "Unknown";
    bool client_connected = true;

    // Get user ID for this connection
    {
        CSLock lock(server->m_clients_cs);
        auto it = server->m_clients.find(clientSocket);
        if (it != server->m_clients.end()) {
            user_id = it->second.user_id;
        }
    }

    printf("[Receiver] Thread started for client %s (Socket %llu).\n",
           user_id.c_str(), (unsigned long long)clientSocket);

    while (client_connected && server->m_running) {
        memset(recv_buffer, 0, BUFFER_SIZE);
        recv_len = recv(clientSocket, recv_buffer, BUFFER_SIZE - 1, 0);

        if (recv_len > 0) {
            recv_buffer[recv_len] = '\0';
            std::string received_serialized(recv_buffer);
            server->handleReceivedMessage(clientSocket, received_serialized);
        } else if (recv_len == 0) {
            printf("\n[System] Client %s disconnected gracefully.\n",
                   user_id.c_str());
            client_connected = false;
        } else {  // recv_len < 0
            int error_code = WSAGetLastError();
            printf(
                "\n[System] recv failed for %s (Error: %d). Connection lost.\n",
                user_id.c_str(), error_code);
            client_connected = false;
        }
    }

    printf("[Receiver] Thread for client %s exiting.\n", user_id.c_str());

    // Mark client as disconnected and clean up
    server->cleanupClient(clientSocket);

    if (hEvent) SetEvent(hEvent);
    delete thread_args;
    _endthreadex(0);
    return 0;
}

// Start receiver thread for a client
bool ChatServer::startClientReceiver(SOCKET clientSocket) {
    HANDLE hEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    if (!hEvent) {
        fprintf(stderr, "[System] Failed to create event for client.\n");
        return false;
    }

    ReceiverThreadArgs* args = new ReceiverThreadArgs();
    if (!args) {
        fprintf(stderr, "[System] Thread resource allocation failed.\n");
        CloseHandle(hEvent);
        return false;
    }

    args->server = this;
    args->clientSocket = clientSocket;
    args->hEvent = hEvent;

    // Store thread info in the client map
    {
        CSLock lock(m_clients_cs);
        m_clients[clientSocket].event = hEvent;
        m_clients[clientSocket].connected = true;
    }

    HANDLE hThread = (HANDLE)_beginthreadex(NULL, 0, &clientReceiverThreadFunc,
                                            args, 0, NULL);
    if (hThread == NULL) {
        fprintf(stderr,
                "[System] Receiver thread creation failed. (Error: %lu)\n",
                GetLastError());
        delete args;
        CloseHandle(hEvent);

        CSLock lock(m_clients_cs);
        m_clients[clientSocket].event = NULL;
        m_clients[clientSocket].connected = false;
        return false;
    }

    // Store thread handle
    {
        CSLock lock(m_clients_cs);
        m_clients[clientSocket].thread = hThread;
    }

    return true;
}

// Accept new client connections
bool ChatServer::acceptClients() {
    fd_set read_fds;
    struct timeval tv;

    printf("[System] Server running. Press Ctrl+C to shut down.\n");

    while (m_running) {
        // Clear the socket set
        FD_ZERO(&read_fds);
        FD_SET(m_server_socket, &read_fds);

        // Set timeout
        tv.tv_sec = 1;  // 1 second timeout for responsiveness
        tv.tv_usec = 0;

        // Wait for activity on the server socket
        int activity = select(0, &read_fds, NULL, NULL, &tv);

        if (activity == SOCKET_ERROR) {
            fprintf(stderr, "[System] Select failed. Error: %d\n",
                    WSAGetLastError());
            break;
        }

        // Handle new connection if there's activity on the server socket
        if (activity > 0 && FD_ISSET(m_server_socket, &read_fds)) {
            struct sockaddr_in client_addr_info;
            int client_addr_len = sizeof(client_addr_info);

            SOCKET new_client_socket =
                accept(m_server_socket, (struct sockaddr*)&client_addr_info,
                       &client_addr_len);

            if (new_client_socket == INVALID_SOCKET) {
                fprintf(stderr, "[System] Accept failed. Error: %d\n",
                        WSAGetLastError());
                continue;
            }

            // Initialize client session
            {
                CSLock lock(m_clients_cs);
                m_clients[new_client_socket] = ClientSession{
                    new_client_socket,  // socket
                    {},                 // public_key (empty for now)
                    NULL,               // thread
                    NULL,               // event
                    "",                 // user_id (empty for now)
                    false               // connected
                };
            }

            printf("[System] New client connection accepted.\n");

            // Exchange keys and start client thread
            if (exchangeKeys(new_client_socket)) {
                if (startClientReceiver(new_client_socket)) {
                    printf("[System] Client session started successfully.\n");
                } else {
                    fprintf(stderr,
                            "[System] Failed to start client thread.\n");
                    cleanupClient(new_client_socket);
                }
            } else {
                fprintf(stderr, "[System] Key exchange failed with client.\n");
                cleanupClient(new_client_socket);
            }
        }
    }

    return true;
}

// Clean up resources for a specific client
void ChatServer::cleanupClient(SOCKET clientSocket) {
    HANDLE hThread = NULL;
    HANDLE hEvent = NULL;
    std::string user_id;

    {
        CSLock lock(m_clients_cs);
        auto it = m_clients.find(clientSocket);
        if (it != m_clients.end()) {
            hThread = it->second.thread;
            hEvent = it->second.event;
            user_id = it->second.user_id;

            // Mark as disconnected first
            it->second.connected = false;

            // Close socket
            if (clientSocket != INVALID_SOCKET) {
                ::shutdown(clientSocket,
                           SD_BOTH);  // Use global namespace to avoid collision
                closesocket(clientSocket);
            }

            // Remove client from the map
            m_clients.erase(it);
        }
    }

    // Wait for thread to finish outside of lock to avoid deadlocks
    if (hThread) {
        WaitForSingleObject(hThread, 2000);
        CloseHandle(hThread);
    }

    if (hEvent) {
        CloseHandle(hEvent);
    }

    if (!user_id.empty()) {
        printf("[System] User '%s' disconnected and cleaned up.\n",
               user_id.c_str());

        // Show remaining connected users
        CSLock lock(m_clients_cs);
        printf("[System] Remaining connected users: ");
        if (m_clients.empty()) {
            printf("none");
        } else {
            for (const auto& client : m_clients) {
                if (client.second.connected) {
                    printf("%s ", client.second.user_id.c_str());
                }
            }
        }
        printf("\n");
    }
}

// Clean up all client resources
void ChatServer::cleanupAllClients() {
    std::vector<SOCKET> client_sockets;

    // First collect all client sockets to avoid modifying the map while
    // iterating
    {
        CSLock lock(m_clients_cs);
        for (auto const& client : m_clients) {
            client_sockets.push_back(client.first);
        }
    }

    // Clean up each client
    for (auto socket : client_sockets) {
        cleanupClient(socket);
    }
}

// Shut down the server (renamed implementation)
void ChatServer::stopServer() {
    m_running = false;
    printf("[System] Shutting down server...\n");

    cleanupAllClients();

    if (m_server_socket != INVALID_SOCKET) {
        closesocket(m_server_socket);
        m_server_socket = INVALID_SOCKET;
    }

    WSACleanup();
    printf("[System] Server shut down complete.\n");
}

// Initialize the server
bool ChatServer::initialize() {
    if (!initWinsock() || !createServerSocket() || !bindAndListen())
        return false;

    m_running = true;
    return true;
}

// Run the server
void ChatServer::run() {
    if (!m_running) {
        fprintf(stderr, "[System] Server not initialized properly.\n");
        return;
    }

    acceptClients();
}

// --- Main Server Logic ---
int main() {
    int port;
    printf("Enter port number to host on: ");
    if (scanf("%d", &port) != 1) {
        fprintf(stderr, "Invalid port.\n");
        return 1;
    }

    // Clear stdin buffer
    int c;
    while ((c = getchar()) != '\n' && c != EOF);

    ChatServer server(port);
    return server.initialize() ? (server.run(), 0) : 1;
}