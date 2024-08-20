const net = require('net');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

const port = 8080;
let clients = {};
let clientOutputs = {};  // Store outputs from each client

const server = net.createServer((socket) => {
    const clientId = `${socket.remoteAddress}:${socket.remotePort}`;
    clients[clientId] = socket;
    clientOutputs[clientId] = '';  // Initialize the output storage for this client
    console.log(`New connection: ${clientId}`);

    socket.on('data', (data) => {
        const output = data.toString().trim();
        console.log(`Received from ${clientId}: ${output}`);
        clientOutputs[clientId] += output + '\n';  // Append the output to the client's log
    });

    socket.on('end', () => {
        console.log(`Connection closed: ${clientId}`);
        delete clients[clientId];
        delete clientOutputs[clientId];  // Remove output storage when client disconnects
    });

    socket.on('error', (err) => {
        console.error(`Error with client ${clientId}: ${err.message}`);
        delete clients[clientId];
        delete clientOutputs[clientId];
    });

    socket.setKeepAlive(true); // Enable TCP keep-alive to prevent connection drops
});

server.listen(port, () => {
    console.log(`Server running on port ${port}`);
    startCommandLineInterface();
});

function startCommandLineInterface() {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
        prompt: '> '
    });

    rl.prompt();

    rl.on('line', (input) => {
        const [command, target, ...messageParts] = input.split(' ');
        const message = messageParts.join(' ');

        switch (command) {
            case 'list':
                console.log('Connected clients:');
                Object.keys(clients).forEach(clientId => {
                    if (clients[clientId].writable) {
                        console.log(clientId);
                    } else {
                        console.log(`${clientId} (disconnected)`);
                        delete clients[clientId];
                        delete clientOutputs[clientId];
                    }
                });
                break;

            case 'send':
                if (target === 'all') {
                    Object.values(clients).forEach(client => {
                        if (client.writable) {
                            client.write(message + '\n');
                        } else {
                            console.log('Client is not writable, skipping.');
                        }
                    });
                    console.log(`Sent to all: ${message}`);
                } else if (clients[target] && clients[target].writable) {
                    clients[target].write(message + '\n');
                    console.log(`Sent to ${target}: ${message}`);
                } else {
                    console.log('Client not found or not writable');
                }
                break;

            case 'show':
                if (clientOutputs[target]) {
                    console.log(`Output from ${target}:\n`);
                    console.log(clientOutputs[target]);
                } else {
                    console.log('Client not found or no output available');
                }
                break;

            case 'help':
                console.log('Available commands:');
                console.log('  list                - List all connected clients');
                console.log('  send <client_id> <message> - Send a command to a specific client');
                console.log('  send all <message>  - Send a command to all clients');
                console.log('  show <client_id>    - Show all output from a specific client');
                console.log('  help                - Show this help message');
                break;

            default:
                console.log('Unknown command');
                break;
        }

        rl.prompt();
    }).on('close', () => {
        console.log('Exiting command line interface');
        process.exit(0);
    });
}
