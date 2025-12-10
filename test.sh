#!/bin/bash
# Test-Skript für das Group Chat System

echo "=== Group Chat System Test ==="
echo ""
echo "Dieses Skript startet Server und mehrere Test-Clients"
echo ""

# Server starten
echo "Starte Server auf Port 5555..."
python3 server.py 5555 &
SERVER_PID=$!
sleep 2

# Client 1 starten (im Hintergrund mit Testbefehlen)
echo "Starte Client Alice..."
{
    sleep 2
    echo "/users"
    sleep 2
    echo "/broadcast Hallo von Alice!"
    sleep 2
    echo "/chat Bob"
    sleep 2
    echo "/msg Bob Hallo Bob!"
    sleep 5
    echo "/quit"
} | python3 client.py Alice localhost 5555 6001 &
ALICE_PID=$!

# Client 2 starten
echo "Starte Client Bob..."
{
    sleep 3
    echo "/users"
    sleep 3
    echo "/broadcast Hallo von Bob!"
    sleep 5
    echo "/quit"
} | python3 client.py Bob localhost 5555 6002 &
BOB_PID=$!

# Client 3 starten
echo "Starte Client Charlie..."
{
    sleep 4
    echo "/users"
    sleep 4
    echo "/broadcast Hallo von Charlie!"
    sleep 5
    echo "/quit"
} | python3 client.py Charlie localhost 5555 6003 &
CHARLIE_PID=$!

# Warten auf Clients
echo ""
echo "Warte auf Clients..."
wait $ALICE_PID
wait $BOB_PID
wait $CHARLIE_PID

# Server beenden
echo ""
echo "Beende Server..."
kill $SERVER_PID
wait $SERVER_PID 2>/dev/null

echo ""
echo "=== Test abgeschlossen ==="
