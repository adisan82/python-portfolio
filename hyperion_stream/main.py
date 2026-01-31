# -*- coding: utf-8 -*-
"""
Hyperion Stream - Entry Point
"""

import asyncio
import logging
import sys
import argparse
from hyperion_stream.storage.engine import HyperionEngine
from hyperion_stream.network.server import HyperionServer

# Configure high-performance logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def main(host, port, data_dir):
    print(f"""
    ========================================
       HYPERION STREAM ENGINE v0.1-alpha
    ========================================
    HOST      : {host}
    PORT      : {port}
    DATA_DIR  : {data_dir}
    ----------------------------------------
    Initializing Storage Engine...
    """)
    
    engine = HyperionEngine(data_dir=data_dir)
    await engine.start()
    
    server = HyperionServer(host=host, port=port, engine=engine)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await engine.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperion Stream Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8888, help="Bind port")
    parser.add_argument("--data-dir", default="./data", help="Storage directory")
    
    args = parser.parse_args()
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main(args.host, args.port, args.data_dir))
    except KeyboardInterrupt:
        pass
