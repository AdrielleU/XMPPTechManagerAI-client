#!/usr/bin/env python3
"""
Simple XMPP Client
"""
import xmpp
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    # Get credentials
    jabberid = os.getenv('XMPP_JID', '')
    password = os.getenv('XMPP_PASSWORD', '')

    print(f"Connecting as: {jabberid}")

    # Parse JID
    jid = xmpp.protocol.JID(jabberid)

    # Create connection
    connection = xmpp.Client(server=jid.getDomain(), debug=False)

    # Connect without TLS (like Pidgin with "Allow plaintext auth over unencrypted streams")
    result = connection.connect(secure=False)
    if not result:
        print("Failed to connect!")
        return False

    print(f"Connected: {result}")

    # Authenticate
    print(f"Authenticating user: {jid.getNode()}")
    auth = connection.auth(user=jid.getNode(), password=password, resource='Python', sasl=1)
    if not auth:
        print("Authentication failed!")
        return False

    print("Authenticated successfully!")

    # Send presence (Available)
    connection.sendInitPresence()
    print("Status: Available")

    # Keep connection alive
    print("\nPress Ctrl+C to disconnect")
    try:
        while True:
            connection.Process(1)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        connection.disconnect()

    return True

if __name__ == "__main__":
    main()
