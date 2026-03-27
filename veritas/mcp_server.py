"""Veritas MCP Server — exposes verify() as a tool for any MCP-compatible AI tool.

Run with:
    python -m veritas.mcp_server

Add to .mcp.json:
    {
        "mcpServers": {
            "veritas": {
                "command": "python",
                "args": ["-m", "veritas.mcp_server"],
                "env": {"ANTHROPIC_API_KEY": "sk-ant-..."}
            }
        }
    }
"""

from __future__ import annotations

import asyncio
import json
import sys


async def handle_request(request: dict) -> dict:
    """Handle a single MCP JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "veritas", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "verify",
                        "description": (
                            "Verify a claim for factual accuracy using adversarial "
                            "multi-agent verification. Returns verdict (VERIFIED/PARTIAL/"
                            "UNCERTAIN/DISPUTED/REFUTED), confidence score, evidence chain, "
                            "and failure mode classification."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "claim": {
                                    "type": "string",
                                    "description": "The claim or AI output to verify",
                                },
                                "context": {
                                    "type": "string",
                                    "description": "Optional: source context, retrieved documents, or system prompt",
                                },
                                "domain": {
                                    "type": "string",
                                    "enum": ["technical", "scientific", "medical", "legal", "general"],
                                    "description": "Optional: domain hint for the verification agents",
                                },
                            },
                            "required": ["claim"],
                        },
                    }
                ]
            },
        }

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "verify":
            return await _handle_verify(req_id, arguments)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
        }

    # Default: method not found
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


async def _handle_verify(req_id, arguments: dict) -> dict:
    """Handle a verify tool call."""
    from veritas.core.verify import verify

    claim = arguments.get("claim", "")
    context = arguments.get("context")
    domain = arguments.get("domain")

    if not claim:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": "Error: claim must not be empty"}],
                "isError": True,
            },
        }

    try:
        result = await verify(claim=claim, context=context, domain=domain)

        output = {
            "verdict": result.verdict.value,
            "confidence": result.confidence,
            "summary": result.summary,
            "failure_modes": [
                {"type": fm.type.value, "detail": fm.detail, "agent": fm.agent}
                for fm in result.failure_modes
            ],
            "evidence": [
                {
                    "agent": e.agent,
                    "finding": e.finding,
                    "confidence": e.confidence,
                }
                for e in result.evidence
            ],
        }

        # Format as readable text + structured JSON
        text_output = f"{result}\n\n"
        if result.failure_modes:
            text_output += "Failure modes:\n"
            for fm in result.failure_modes:
                text_output += f"  - {fm.type.value}: {fm.detail}\n"
            text_output += "\n"
        text_output += f"Full data: {json.dumps(output, indent=2)}"

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": text_output}],
            },
        }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": f"Verification error: {e}"}],
                "isError": True,
            },
        }


async def main():
    """Run the MCP server on stdin/stdout."""
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

    while True:
        # Read Content-Length header
        header_line = await reader.readline()
        if not header_line:
            break

        header = header_line.decode().strip()
        if not header.startswith("Content-Length:"):
            continue

        content_length = int(header.split(":")[1].strip())

        # Skip empty line after header
        await reader.readline()

        # Read body
        body = await reader.readexactly(content_length)
        request = json.loads(body.decode())

        response = await handle_request(request)
        if response is None:
            continue

        response_bytes = json.dumps(response).encode()
        output = f"Content-Length: {len(response_bytes)}\r\n\r\n".encode() + response_bytes
        writer.write(output)
        await writer.drain()


if __name__ == "__main__":
    asyncio.run(main())
