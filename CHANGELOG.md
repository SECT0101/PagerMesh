# Changelog

PagerMesh versions (the payload in `library/user/general/PagerMesh`). Newest first.

## 1.0.0
First release.
- **Three ways to reach the radio**: the Glytch Mesh Mod (meshtasticd on the Pager), a **Wi-Fi radio** (Meshtastic TCP API, port 4403, e.g. Heltec V3), or a **USB radio** (serial API).
- **Setup on the Pager or in a web browser**, with *Test connection*; change it later in *Settings > Radio connection* or the web console's *Settings* tab.
- **Mesh chat**: send and receive on every channel, direct messages with a *delivered* tick, quick messages, unread count and sound, chat log in `/root/loot/PagerMesh`.
- **Conversations**: one thread per DM contact and per channel, with unread counts, on the Pager and in the web console; the last 7 days of chat are loaded at start; delete a message, a conversation, or all chats (also removed from the chat logs; *Delete all* asks first).
- **Node list**: range and bearing from the Pager GPS, battery, SNR, hops, last heard; *Navigate to*, *Show on map*, *Direct message*.
- **Pager map** with mesh nodes and the nearest-nodes list (PagerTAK's map viewer).
- **Pager GPS position over the mesh**: every 5 / 15 / 30 / 60 minutes or on demand.
- **Web console**: map, node table, chat with channels and direct messages, *Send position*, radio *Settings*; password login; listens on the Pager's own Wi-Fi / USB-C, or also on the Wi-Fi the Pager joined (*Listen on*).
- **Mesh Mod setup**: runs Glytch's Meshtastic payload to install, start and enable meshtasticd at boot; checks the SD card first (packages there block Glytch's installer).
- **Radio settings** (Pager and web console): node name, region, modem preset, role, hop limit, position and telemetry intervals, Wi-Fi, MQTT, Bluetooth, display, power, channels with share link / QR code, restart; only edited fields are written; risky changes ask first.
- **Node tools**: details (hardware, role, position age, MQTT, favorite, RSSI), traceroute, request position, favorites, hide old nodes.
- **Waypoints** on both maps; drop and delete them from the web map.
- **Pager map**: pick a node or waypoint and navigate to it.
- **Set the Pager's location** by clicking the web map (used without a GPS fix).
- **DM alert** on the Pager (sound + light, optional popup).
- **Mesh SIGINT**: packet log with RSSI / SNR / hops (encrypted packets too), traffic stats, trails, pcap / CSV export, modem preset scan that restores the radio.
- **Mesh ↔ TAK bridge**: mesh nodes as TAK contacts, channel chat ↔ TAK All Chat Rooms (TLS / TCP / UDP).
- Saving a new radio address in the web console switches right away (it used to come back to the old address); reconnects after a radio restart are quick again.
- `tools/fake_meshtasticd.py`: a simulated meshtasticd for testing without a radio (settings, restarts, traceroute, waypoints); `tools/fake_takserver.py`: a stand-in TAK Server.
