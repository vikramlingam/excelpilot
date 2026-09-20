import argparse
import asyncio

import uvicorn

from excelpilot.analysis.report import generate_audit_report
from excelpilot.bridge.file import FileBridge
from excelpilot.bridge.router import router
from excelpilot.cli.doctor import run_doctor
from excelpilot.cli.launcher import launch_all
from excelpilot.config import settings
from excelpilot.tools.registry import mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="ExcelPilot CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: start (one-command launcher for backend, add-in, and Excel)
    subparsers.add_parser("start", help="Start backend, add-in dev server, and open Excel")

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI bridge and chat server")
    serve_parser.add_argument("--host", default=settings.excelpilot_host, help="Host address to bind")
    serve_parser.add_argument("--port", type=int, default=settings.excelpilot_port, help="Port to listen on")

    # Command: mcp
    mcp_parser = subparsers.add_parser("mcp", help="Run the FastMCP tool server")
    mcp_parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="MCP transport type")

    # Command: doctor
    subparsers.add_parser("doctor", help="Run diagnostic health checks")

    # Command: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze an Excel workbook file")
    analyze_parser.add_argument("file_path", help="Path to the Excel file to analyze")

    args = parser.parse_args()

    if args.command == "start":
        launch_all()
    elif args.command == "serve":
        uvicorn.run(
            "excelpilot.app.api:app",
            host=args.host,
            port=args.port,
            reload=False,
            log_level=settings.log_level.lower(),
        )
    elif args.command == "mcp":
        if args.transport == "stdio":
            mcp.run(transport="stdio")
        else:
            mcp.run(transport="sse")
    elif args.command == "doctor":
        asyncio.run(run_doctor())
    elif args.command == "analyze":
        router.file_bridge = FileBridge(args.file_path)
        report = asyncio.run(generate_audit_report())
        print(report["report_markdown"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
