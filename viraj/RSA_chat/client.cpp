// Compile: g++ client.cpp -o client.exe -lws2_32 -lstdc++
// Run:     .\client.exe
#define _WIN32_WINNT 0x0600

#include <process.h>   // For _beginthreadex, _endthreadex
#include <stdio.h>     // For printf, scanf, fgets, fprintf, etc.
#include <string.h>    // For memset, strlen, strcspn, strcpy
#include <windows.h>   // For HANDLE, CreateEvent, etc.
#include <winsock2.h>  // For socket functions

#include <stdexcept>  // For exception handling
#include <string>     // Include C++ string
#include <vector>     // Include C++ vector

// Include our RSA header
#include "rsa_chat.hpp"

#pragma comment(lib, "ws2_32.lib")

#define DEFAULT_PORT 8080
#define DEFAULT_IP "127.0.0.1"
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

class ChatClient {
   private:
    bool m_connection_active;
    SOCKET m_sock;
    std::vector<long long> m_client_public_key;
    std::vector<long long> m_client_private_key;
    std::vector<long long> m_server_public_key;
    HANDLE m_recv_thread;
    HANDLE m_recv_event;

    struct ReceiverThreadArgs {
        ChatClient* client;
        HANDLE hEvent;
    };

    // Internal methods
    bool initWinsock();
    bool createSocket();
    bool connectToServer(const char* ip, int port);
    bool exchangeKeys_userID(const char* user_id);
    bool startReceiver();
    void messageLoop();
    void cleanup();

    // Thread receiver function
    static unsigned __stdcall receiverThreadFunc(void* args_ptr);
    void handleReceivedMessage(const std::string& received_msg);

   public:
    ChatClient();
    ~ChatClient();
    bool initialize(const char* server_ip, int server_port,
                    const char* user_id);
    bool run();
};

// Constructor initializes member variables
ChatClient::ChatClient()
    : m_connection_active(false),
      m_sock(INVALID_SOCKET),
      m_client_public_key({7, 299}),     // {e, n} p=13, q=23
      m_client_private_key({151, 299}),  // {d, n}
      m_recv_thread(NULL),
      m_recv_event(NULL) {}

// Destructor ensures cleanup
ChatClient::~ChatClient() { cleanup(); }

// Initialize Winsock
bool ChatClient::initWinsock() {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "WSAStartup failed. Error: %d\n", WSAGetLastError());
        return false;
    }
    return true;
}

// Create socket
bool ChatClient::createSocket() {
    if ((m_sock = socket(AF_INET, SOCK_STREAM, 0)) == INVALID_SOCKET) {
        fprintf(stderr, "Socket creation failed. Error: %d\n",
                WSAGetLastError());
        return false;
    }
    return true;
}

// Connect to server
bool ChatClient::connectToServer(const char* ip, int port) {
    struct sockaddr_in server_addr = {0};
    server_addr.sin_addr.s_addr = inet_addr(ip);
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    if (server_addr.sin_addr.s_addr == INADDR_NONE) {
        fprintf(stderr, "Invalid server IP address provided.\n");
        return false;
    }

    printf("Connecting to %s:%d...\n", ip, port);
    if (connect(m_sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) <
        0) {
        fprintf(stderr, "Connect failed. Error: %d\n", WSAGetLastError());
        return false;
    }

    printf("[System] Connected. Performing key exchange...\n");
    return true;
}

// Exchange keys with server
bool ChatClient::exchangeKeys_userID(const char* user_id) {
    char comm_buffer[BUFFER_SIZE];
    m_server_public_key.clear();

    try {
        // Receive server public key
        memset(comm_buffer, 0, sizeof(comm_buffer));
        int key_recv_len =
            recv(m_sock, comm_buffer, sizeof(comm_buffer) - 1, 0);
        if (key_recv_len <= 0)
            throw std::runtime_error("Receive server key failed");
        comm_buffer[key_recv_len] = '\0';

        long long server_e, server_n;
        if (sscanf(comm_buffer, "%lld %lld", &server_e, &server_n) == 2) {
            m_server_public_key.assign({server_e, server_n});
            printf("[System] Server public key received: {e=%lld, n=%lld}\n",
                   m_server_public_key[0], m_server_public_key[1]);
        } else
            throw std::runtime_error("Parse server key failed");

        // Send client public key with user ID
        snprintf(comm_buffer, sizeof(comm_buffer), "%lld %lld %s",
                 m_client_public_key[0], m_client_public_key[1], user_id);
        if (send(m_sock, comm_buffer, strlen(comm_buffer), 0) <= 0)
            throw std::runtime_error("Send client key failed");

    } catch (const std::exception& e) {
        fprintf(stderr, "[System] Key exchange error: %s. (WSAError: %d)\n",
                e.what(), WSAGetLastError());
        return false;
    }

    printf("[System] Key exchange successful. Chat session started.\n");
    return true;
}

// Handle received messages
void ChatClient::handleReceivedMessage(const std::string& received_serialized) {
    // Display crypto debug info
    LogCryptoData(received_serialized);

    std::vector<long long> ciphertext =
        deserialize_ciphertext(received_serialized);

    if (ciphertext.empty()) {
        if (received_serialized.empty() || received_serialized == " ") {
            printf("[Server]: (empty message)\n> ");
        } else {
            printf("[System] Received invalid data: '%.50s'...\n> ",
                   received_serialized.c_str());
        }
        return;
    }

    std::string decrypted_message = decrypt(ciphertext, m_client_private_key);
    printf("[CRYPTO] Decrypted message: %s\n\n", decrypted_message.c_str());
    printf("[Server]: %s\n> ", decrypted_message.c_str());
}

// Receiver thread function
unsigned __stdcall ChatClient::receiverThreadFunc(void* args_ptr) {
    ReceiverThreadArgs* thread_args = (ReceiverThreadArgs*)args_ptr;
    ChatClient* client = thread_args->client;
    HANDLE hEvent = thread_args->hEvent;

    char recv_buffer[BUFFER_SIZE];
    int recv_len;

    printf("[Receiver] Thread started.\n");
    while (client->m_connection_active) {
        memset(recv_buffer, 0, BUFFER_SIZE);
        recv_len = recv(client->m_sock, recv_buffer, BUFFER_SIZE - 1, 0);

        if (recv_len > 0) {
            recv_buffer[recv_len] = '\0';
            std::string received_serialized(recv_buffer);
            client->handleReceivedMessage(received_serialized);
        } else if (recv_len == 0) {
            printf("\n[System] Server disconnected.\n> ");
            client->m_connection_active = false;
            break;
        } else {  // recv_len < 0
            int error_code = WSAGetLastError();
            if (client->m_connection_active) {
                printf(
                    "\n[System] recv failed (Error: %d). Connection lost.\n> ",
                    error_code);
                client->m_connection_active = false;
            }
            break;
        }
    }

    printf("[Receiver] Thread exiting.\n");
    if (hEvent) SetEvent(hEvent);
    delete thread_args;
    _endthreadex(0);
    return 0;
}

// Start receiver thread
bool ChatClient::startReceiver() {
    m_recv_event = CreateEvent(NULL, TRUE, FALSE, NULL);
    if (!m_recv_event) {
        fprintf(stderr, "[System] Failed to create event.\n");
        return false;
    }

    ReceiverThreadArgs* args = new ReceiverThreadArgs();
    if (!args) {
        fprintf(stderr, "[System] Thread resource allocation failed.\n");
        CloseHandle(m_recv_event);
        m_recv_event = NULL;
        return false;
    }

    args->client = this;
    args->hEvent = m_recv_event;

    m_recv_thread =
        (HANDLE)_beginthreadex(NULL, 0, &receiverThreadFunc, args, 0, NULL);
    if (m_recv_thread == NULL) {
        fprintf(stderr,
                "[System] Receiver thread creation failed. (Error: %lu)\n",
                GetLastError());
        delete args;
        CloseHandle(m_recv_event);
        m_recv_event = NULL;
        return false;
    }

    return true;
}

// Main message loop
void ChatClient::messageLoop() {
    char comm_buffer[BUFFER_SIZE];
    printf("Chat commands:\n");
    printf("- Direct message: userID/your message here\n");
    printf("- Exit: exit\n");
    printf("> ");

    while (m_connection_active) {
        if (fgets(comm_buffer, sizeof(comm_buffer), stdin) != NULL) {
            comm_buffer[strcspn(comm_buffer, "\n")] = 0;
            std::string plaintext_message(comm_buffer);

            if (!m_connection_active) break;

            if (m_server_public_key.empty()) {
                printf(
                    "[System] Server public key not available. Cannot "
                    "send.\n> ");
                continue;
            }

            // Encrypt and send the message
            std::vector<long long> ciphertext =
                encrypt(plaintext_message, m_server_public_key);
            std::string serialized_ciphertext =
                serialize_ciphertext(ciphertext);

            if (send(m_sock, serialized_ciphertext.c_str(),
                     serialized_ciphertext.length(), 0) <= 0) {
                if (m_connection_active) {
                    fprintf(stderr, "[System] send failed. Error: %d\n",
                            WSAGetLastError());
                    m_connection_active = false;
                }
                break;
            }

            if (plaintext_message == "exit") {
                printf("[System] Disconnecting...\n");
                m_connection_active = false;
                break;
            }
            printf("> ");
        } else {
            printf("\n[System] Console input error/EOF. Disconnecting...\n");
            m_connection_active = false;
            break;
        }
    }
}

// Clean up resources
void ChatClient::cleanup() {
    m_connection_active = false;

    if (m_sock != INVALID_SOCKET) {
        shutdown(m_sock, SD_SEND);
    }

    if (m_recv_thread) {
        printf("[System] Waiting for receiver thread to finish...\n");
        if (m_recv_event) {
            WaitForSingleObject(m_recv_event, 2000);
        } else {
            WaitForSingleObject(m_recv_thread, 2000);
        }
        CloseHandle(m_recv_thread);
        m_recv_thread = NULL;
    }

    if (m_recv_event) {
        CloseHandle(m_recv_event);
        m_recv_event = NULL;
    }

    if (m_sock != INVALID_SOCKET) {
        closesocket(m_sock);
        m_sock = INVALID_SOCKET;
    }

    WSACleanup();
}

// Initialize the client
bool ChatClient::initialize(const char* server_ip, int server_port,
                            const char* user_id) {
    if (!initWinsock() || !createSocket() ||
        !connectToServer(server_ip, server_port)) {
        cleanup();
        return false;
    }

    m_connection_active = true;
    if (!exchangeKeys_userID(user_id) || !startReceiver()) {
        cleanup();
        return false;
    }

    return true;
}

// Run the client
bool ChatClient::run() {
    if (!m_connection_active) {
        printf("[System] Client not initialized properly.\n");
        return false;
    }

    messageLoop();
    cleanup();
    printf("[System] Connection closed.\n");
    return true;
}

// --- Main Client Logic ---
int main() {
    char server_ip_str[16] = DEFAULT_IP;
    int server_port_num = DEFAULT_PORT;
    char clientUserId[32];

    // Get server IP
    printf("Enter server IP (blank for %s): ", DEFAULT_IP);
    if (fgets(server_ip_str, sizeof(server_ip_str), stdin) != NULL) {
        server_ip_str[strcspn(server_ip_str, "\n")] = 0;
        if (server_ip_str[0] == '\0') strcpy(server_ip_str, DEFAULT_IP);
    }
    printf("Using IP: %s\n", server_ip_str);

    // Get server port
    printf("Enter server port (blank for %d): ", DEFAULT_PORT);
    char port_str[10];
    if (fgets(port_str, sizeof(port_str), stdin) != NULL) {
        port_str[strcspn(port_str, "\n")] = 0;
        if (port_str[0] != '\0' &&
            sscanf(port_str, "%d", &server_port_num) == 1) {
            // Port was successfully parsed
        }
    }
    printf("Using port: %d\n", server_port_num);

    // Get user ID
    printf("Enter userID: ");
    if (fgets(clientUserId, sizeof(clientUserId), stdin) == NULL) {
        fprintf(stderr, "User ID error\n");
        return 1;
    }
    clientUserId[strcspn(clientUserId, "\n")] = 0;

    // Connect and run client
    ChatClient client;
    return client.initialize(server_ip_str, server_port_num, clientUserId)
               ? (client.run() ? 0 : 1)
               : 1;
}