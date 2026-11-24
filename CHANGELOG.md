# Changelog

PagerMesh versions (the payload in `library/user/general/PagerMesh`). Newest first.

## 1.0.1
- **TAK chat is only bridged to a mesh channel with its own key.** Channel 0 is public on most meshes (no key, the default key or a well-known simple key), and 1.0.0 bridged TAK *All Chat Rooms* to channel 0 by default once the bridge was on.
  - Until you pick a private channel, bridge chat is paused both ways; node positions to TAK keep working.
  - The Pager menu (*Mesh <-> TAK > Mesh channel*) and the web console only offer channels with their own key, and the bridge status says why chat is paused.
  - A 1.0.0 setup still bridged to a public channel pauses chat until you pick a private one.
- **The Pager's position is only shared once you pick a channel.** 1.0.0 broadcast it on channel 0 every 15 minutes.
  - *Settings > Send position > Share on* and the web console (*Settings > PagerMesh*) pick the channel; *Nobody (off)* stops it. *How often* keeps the 5 / 15 / 30 / 60 min or manual choice.
  - Any channel can be picked. A public channel (no key, the default key or a well-known simple key) asks to confirm on the Pager and shows a warning in the web console, because anyone on it can see where the Pager is.
  - A 1.0.0 setup has no channel set, so position sharing is off until you pick one; *Send position now* says so.
- **Web console on every address by default**, like PagerTAK: it opens from the Pager's own Wi-Fi / USB-C and from the Wi-Fi the Pager joined. *Settings > Web console > Listen on > Pager Wi-Fi / USB-C* still narrows it.

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
