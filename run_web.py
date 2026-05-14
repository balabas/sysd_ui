#!/usr/bin/env python3
"""Launch the sysd_ui web interface."""

import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="sysd_ui web interface")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Starting at http://{args.host}:{args.port}")
    uvicorn.run("web.app:app", host=args.host, port=args.port, reload=False)
