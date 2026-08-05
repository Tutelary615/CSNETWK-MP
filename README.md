# CSNETWK-MP

## Build and Run
Before running the following instructions, make sure to install `asyncio` first
- To run server, type this in the terminal:
> python -m server.main
- To run client, type the following:
> python -m client.main

## Work Distribution Matrix
| Task/Feature | Kharlene | TJ | Mika | Jam |
| ----------- | ----------- | ----------- | ----------- | ----------- |
| TCP Server: connection handling, framing, dispatch | [x] | [] | [] | [] |
| Game lifecycle: LOBBY, GAME_SETUP, MULLIGAN logic | [] | [x] | [] | [] |
| Turn & phase engine (all phases/steps, transitions) | [] | [x] | [] | [] |
| Priority & Stack logic, spell/ability resolution | [] | [] | [x] | [] |
| Combat system (attackers, blockers, damage) | [] | [] | [] | [x] |
| Client implementation & state rendering | [x] | [] | [] | [] |
| PDU serialisation/deserialisation (all 25 PDU types) | [] | [] | [x] | [] |
| Error handling, PING/PONG heartbeat, disconnect logic | [] | [] | [] | [x] |
| Verbose mode (client + server PDU logging, toggle on/off) | [x] | [] | [] | [] |
| Testing & interoperability | [] | [] | [] | [] |
| README / documentation / AI disclosure | [x] | [] | [] | [] |

### AI Usage

### Limitations
