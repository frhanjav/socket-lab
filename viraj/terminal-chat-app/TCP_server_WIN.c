// filepath:
// e:\programming\NetworkingLAB\terminal-chat-app\server\TCP_server_WIN.c
// tcp_server.c
// gcc TCP_server_WIN.c -o server.exe -lws2_32; .\server.exe
#include <ctype.h>
#include <process.h>  // for _beginthreadex
#include <stdint.h>   // for uintptr_t
#include <stdio.h>
#include <winsock2.h>

#define MAX_CLIENT 5

#pragma comment(lib, "ws2_32.lib")  // Link with ws2_32.lib

// A simple struct to pass client socket into the thread
typedef struct {
    SOCKET client_socket;
    char userID[512];
    int index;  // Index in the connClientInfo array
} ClientInfo;

ClientInfo* connClientInfo[MAX_CLIENT] = {NULL};

int findNextEmpty_connClientInfo() {
    for (int i = 0; i < MAX_CLIENT; i++) {
        if (connClientInfo[i] == NULL) {
            return i;
        }
    }
    return -1;  // Return -1 if no empty slots are found
}

void cleanupClient(int index) {
    if (index >= 0 && index < MAX_CLIENT && connClientInfo[index] != NULL) {
        closesocket(connClientInfo[index]->client_socket);
        free(connClientInfo[index]);
        connClientInfo[index] = NULL;
        printf("[System] Client slot %d freed\n", index);
    }
}

// Function to find and send a message to a specific user
void sendToUser(const char* target_id, const char* message,
                const char* sender_id, SOCKET sender_socket) {
    int found = 0;
    char formatted_msg[1024];

    // Format the message with sender's ID
    sprintf(formatted_msg, "msg from [%s]: %s", sender_id, message);

    // Search for the target user in our connected clients array
    for (int i = 0; i < MAX_CLIENT; i++) {
        if (connClientInfo[i] != NULL &&
            strcmp(connClientInfo[i]->userID, target_id) == 0) {
            // Found the user, send the message
            send(connClientInfo[i]->client_socket, formatted_msg,
                 strlen(formatted_msg), 0);
            found = 1;
            break;
        }
    }

    // If user not found, inform the sender
    if (!found) {
        const char* error_msg = "User not found";
        send(sender_socket, error_msg, strlen(error_msg), 0);
    }
}

// Add a function to list all connected users
void listConnectedUsers(SOCKET requester) {
    char userList[1024] = "Connected users: ";
    int count = 0;

    for (int i = 0; i < MAX_CLIENT; i++) {
        if (connClientInfo[i] != NULL) {
            // Add a comma if not the first user
            if (count > 0) strcat(userList, ", ");

            // Append the user ID
            strcat(userList, connClientInfo[i]->userID);
            count++;
        }
    }

    // If no users, indicate that
    if (count == 0) strcat(userList, "none");

    // Send the list to the requester
    send(requester, userList, strlen(userList), 0);
}

// Fix logic issue in the client_thread function
unsigned __stdcall client_thread(void* param) {
    ClientInfo* info = (ClientInfo*)param;
    SOCKET client = info->client_socket;
    int myIndex = info->index;

    char buf[1024];
    int recv_len;

    // Get the user id
    if ((recv_len = recv(client, buf, sizeof(buf) - 1, 0)) != SOCKET_ERROR &&
        recv_len > 0) {
        buf[recv_len] = '\0';
        // Store userID in the connClientInfo array
        strncpy(info->userID, buf, sizeof(info->userID) - 1);
        info->userID[sizeof(info->userID) - 1] =
            '\0';  // Ensure null-termination
        printf("[Thread %u] User ID: %s (slot %d)\n", GetCurrentThreadId(),
               info->userID, myIndex);
    } else {
        // Error handling for failed user ID reception
        printf("[Thread %u] Failed to receive user ID. Closing connection.\n",
               GetCurrentThreadId());
        cleanupClient(myIndex);
        return 0;
    }

    // Communicate until client sends "exit" or error
    while ((recv_len = recv(client, buf, sizeof(buf) - 1, 0)) != SOCKET_ERROR &&
           recv_len > 0) {
        buf[recv_len] = '\0';
        printf("[Thread %u] Received from %s: %s\n", GetCurrentThreadId(),
               info->userID, buf);

        if (strcmp(buf, "exit") == 0) {
            printf("[Thread %u] Client %s requested exit.\n",
                   GetCurrentThreadId(), info->userID);
            // Just send confirmation and break, don't try to process as a
            // message
            send(client, "Goodbye!", 8, 0);
            break;
        }

        // Parse message if it's in the format id/msg
        char id_part[512] = {0};
        char msg_part[512] = {0};
        int valid_format = 0;

        // Look for the separator '/'
        char* separator = strchr(buf, '/');
        if (separator != NULL) {
            // Calculate lengths
            int id_length = separator - buf;
            int msg_length =
                recv_len - id_length - 1;  // -1 for the '/' character

            // Extract the ID and message if valid
            if (id_length > 0 && msg_length > 0) {
                strncpy(id_part, buf, id_length);
                id_part[id_length] = '\0';

                strncpy(msg_part, separator + 1, msg_length);
                msg_part[msg_length] = '\0';

                printf("[Thread %u] Parsed ID: %s, Message: %s\n",
                       GetCurrentThreadId(), id_part, msg_part);
                valid_format = 1;

                // Only call sendToUser if format is valid
                sendToUser(id_part, msg_part, info->userID, client);
            }
        }

        // If not in the correct format, prepare error message
        if (!valid_format) {
            const char* error_msg = "Invalid format. Please use: id/message";
            send(client, error_msg, strlen(error_msg), 0);
        }
    }

    // Cleanup the client resources when thread exits
    cleanupClient(myIndex);
    printf("[Thread %u] Connection closed for %s.\n", GetCurrentThreadId(),
           info->userID);
    return 0;
}

// Fix the main function client handling logic
int main() {
    WSADATA wsa;
    SOCKET server_socket;
    struct sockaddr_in server;
    int port;

    printf("Enter port number to host on: ");
    scanf("%d", &port);

    WSAStartup(MAKEWORD(2, 2), &wsa);

    server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server_socket == INVALID_SOCKET) {
        printf("Socket failed: %d\n", WSAGetLastError());
        return 1;
    }

    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons(port);

    if (bind(server_socket, (struct sockaddr*)&server, sizeof(server)) ==
        SOCKET_ERROR) {
        printf("Bind failed: %d\n", WSAGetLastError());
        return 1;
    }

    listen(server_socket, SOMAXCONN);
    printf("Server listening on port %d...\n", port);

    while (1) {
        SOCKET client_socket = accept(server_socket, NULL, NULL);
        if (client_socket == INVALID_SOCKET) {
            printf("Accept failed: %d\n", WSAGetLastError());
            continue;
        }

        int nextIndex = findNextEmpty_connClientInfo();
        if (nextIndex != -1) {
            // Allocate and fill client info
            ClientInfo* info = (ClientInfo*)malloc(sizeof(ClientInfo));
            if (!info) {
                printf("Memory allocation failed\n");
                closesocket(client_socket);
                continue;
            }

            info->client_socket = client_socket;
            info->index = nextIndex;
            info->userID[0] = '\0';  // Initialize to empty string

            // Store in the global array
            connClientInfo[nextIndex] = info;

            printf("[System] New client connected (slot %d)\n", nextIndex);

            // Spawn a thread to handle the client
            uintptr_t thread_handle =
                _beginthreadex(NULL,           // security
                               0,              // stack size (0 = default)
                               client_thread,  // thread function
                               info,           // argument
                               0,              // creation flags
                               NULL            // thread id
                );

            if (thread_handle == 0) {
                printf("Failed to create thread.\n");
                cleanupClient(nextIndex);
            } else {
                CloseHandle((HANDLE)thread_handle);
            }
        } else {
            // Connection full, disconnect the requesting client
            printf("Maximum clients reached. Rejecting connection.\n");
            const char* msg = "Server is full. Try again later.";
            send(client_socket, msg, strlen(msg), 0);
            closesocket(client_socket);
        }
    }

    // Clean up any remaining clients
    for (int i = 0; i < MAX_CLIENT; i++) {
        cleanupClient(i);
    }

    closesocket(server_socket);
    WSACleanup();
    return 0;
}
