"""MCP JSON-RPC stdio server for genpark-proactive-intent-disambiguation-clarifier-skill."""
import sys
import json
from client import ProactiveIntentDisambiguationClarifier

clarifier = ProactiveIntentDisambiguationClarifier()

def handle_call_tool(params):
    name = params.get("name")
    args = params.get("arguments", {})
    if name != "disambiguate_intent":
        return {"error": f"Unknown tool '{name}'"}
        
    action = args.get("action")
    prompt = args.get("prompt", "")
    
    if action == "analyze_ambiguity":
        return clarifier.analyze_ambiguity(prompt)
    elif action == "generate_clarification":
        return clarifier.generate_clarification(prompt)
    elif action == "resolve_selection":
        return clarifier.resolve_selection(
            prompt=prompt,
            selection_index=args.get("selection_index", 1),
            custom_writein=args.get("custom_writein")
        )
    else:
        return {"error": f"Unknown action '{action}'"}

def main():
    if "--test" in sys.argv:
        print("[TEST] Running self-test for ProactiveIntentDisambiguationClarifier...")
        an = clarifier.analyze_ambiguity("clean up old database tables")
        assert an["needs_clarification"] is True
        cl = clarifier.generate_clarification("clean up old database tables")
        assert len(cl["options"]) >= 3
        res = clarifier.resolve_selection("clean up old database tables", 1)
        assert res["is_unambiguous"] is True
        print(f"[TEST] Success! Resolved plan: {res['executable_plan']}")
        return

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)
                continue
            if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}), flush=True)
                continue
            # JSON-RPC notifications never receive a response or execute request-only tools.
            if "id" not in req:
                continue
            if req["method"] == "initialize":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {
                    "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": 'genpark-proactive-intent-disambiguation-clarifier-skill', "version": "1.0.0"}
                }}), flush=True)
                continue
            if req["method"] == "ping":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {}}), flush=True)
                continue
            if req["method"] not in ("tools/list", "tools/call"):
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "Method not found"}}), flush=True)
                continue
            if req["method"] == "tools/call":
                params = req.get("params")
                if not isinstance(params, dict) or not isinstance(params.get("arguments", {}), dict) or params.get("name") not in ('disambiguate_intent',):
                    print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32602, "message": "Unknown tool or invalid arguments"}}), flush=True)
                    continue
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": [
                            {
                                "name": "disambiguate_intent",
                                "description": "Analyze user prompt ambiguity, assess execution risk, generate structured clarification options, and resolve intent.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "action": {"type": "string", "enum": ["analyze_ambiguity", "generate_clarification", "resolve_selection"]},
                                        "prompt": {"type": "string"},
                                        "selection_index": {"type": "integer"},
                                        "custom_writein": {"type": "string"}
                                    },
                                    "required": ["action"]
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                res = handle_call_tool(req.get("params", {}))
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
                }
            else:
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            print(json.dumps(resp), flush=True)
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None, "error": {"code": -32000, "message": str(e)}}
            print(json.dumps(err_resp), flush=True)

if __name__ == "__main__":
    main()
