# CSNETWK-MP

## Build and Run
Before running the following instructions, make sure to install `asyncio` first
- To run server, type this in the terminal:
> python -m server.main
- To run client, type the following:
> python -m client.main \<player_id\> \<deck_slot\> (ex. python -m client.main player_1 1)

To add verbose mode, add the `-v` flag at the end of your command

## Work Distribution Matrix
| Task/Feature | Kharlene | TJ | Mika | Jam |
| ----------- | ----------- | ----------- | ----------- | ----------- |
| TCP Server: connection handling, framing, dispatch | [x] | [] | [] | [] |
| Game lifecycle: LOBBY, GAME_SETUP, MULLIGAN logic | [x] | [x] | [] | [] |
| Turn & phase engine (all phases/steps, transitions) | [x] | [] | [] | [] |
| Priority & Stack logic, spell/ability resolution | [] | [] | [x] | [] |
| Combat system (attackers, blockers, damage) | [] | [] | [] | [x] |
| Client implementation & state rendering | [x] | [] | [] | [] |
| PDU serialisation/deserialisation (all 25 PDU types) | [x] | [] | [x] | [] |
| Error handling, PING/PONG heartbeat, disconnect logic | [x] | [] | [x] | [] |
| Verbose mode (client + server PDU logging, toggle on/off) | [x] | [] | [] | [] |
| Testing & interoperability | [x] | [x] | [x] | [] |
| README / documentation / AI disclosure | [x] | [x] | [x] | [x] |

### AI Usage
Claude was mainly used in organizing the project/directory structure for the game, which was used as a foundation in the creation of this project. AI mostly assisted in understanding the game logic and mechanics, such as card effects, phases, and combat rules, which we first validated and then used as reference. This AI tool was also used for debugging the errors in the code as well as creating test cases, specifically for the PDU framing. Suggestions from AI to further improve the code design and terminal display was also used to enhance the project, which was thoroughly tested, reviewed, and validated. Other than that, we claim that the socket programming logic, implementation of the RFC, building of the client-server architecture, and handling of connections are primarily our own work.
