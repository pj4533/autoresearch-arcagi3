#!/usr/bin/env python3
"""Start a local ARC-AGI-3 game server for fast offline experiments."""

import sys

from arc_agi import Arcade, OperationMode
from arc_agi.server import create_app

arcade = Arcade(operation_mode=OperationMode.OFFLINE)
app, api = create_app(arcade, include_frame_data=True)

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5050
print(f"Starting local ARC-AGI-3 server on port {port}...")
app.run(host="0.0.0.0", port=port, debug=False)
