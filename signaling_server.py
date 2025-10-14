import asyncio
import json
import websockets

peers = set()

async def handler(websocket):
    peers.add(websocket)
    print(f"Peer connected. Total peers: {len(peers)}")

    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"Received message: {data['type']}")

            # Relay to other peers safely
            dead_peers = []
            for peer in peers:
                if peer != websocket:
                    try:
                        await peer.send(json.dumps(data))
                    except websockets.exceptions.ConnectionClosed:
                        dead_peers.append(peer)

            # Clean up any dead peers
            for dp in dead_peers:
                peers.remove(dp)

    except websockets.exceptions.ConnectionClosed:
        print("Peer disconnected.")
    finally:
        peers.remove(websocket)
        print(f"Peer removed. Total peers: {len(peers)}")

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8080):
        print("Signaling server running at ws://localhost:8080")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
