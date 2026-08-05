"""
Manages priority based from the priority state machine (Section 8.2 of the RFC):
  - AP gets priority at the start of each step
  - On PRIORITY_PASS: give priority to the other player
  - When both pass consecutively:
      - Stack non-empty: resolve top item, AP gets priority again
      - Stack empty: step ends
"""