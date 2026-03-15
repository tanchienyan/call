"""Entry point for python -m mystery_shopper."""
import sys

def main():
    args = sys.argv[1:]

    if not args or args[0] == "help":
        print("🕵️  AI Mystery Shopper")
        print()
        print("Commands:")
        print("  journey [--target 'Name'] [--no-ai]                    Run full journey demo ⭐")
        print("  demo [--quality good|average|poor] [--target 'Name']   Run single-channel demo")
        print("  serve [--port 8000]                                    Start web dashboard")
        print("  email <target@email.com> [--target 'Name']            Send test email")
        print("  phone <+number> [--target 'Name']                     Make test call")
        return

    cmd = args[0]

    if cmd == "journey":
        import asyncio
        from .orchestrator.demo_journey import run_demo_journey
        target = "The Grand Hotel London"
        use_ai = True
        i = 1
        while i < len(args):
            if args[i] == "--target" and i + 1 < len(args):
                target = args[i + 1]; i += 2
            elif args[i] == "--no-ai":
                use_ai = False; i += 1
            else:
                i += 1
        asyncio.run(run_demo_journey(target_name=target, use_real_analysis=use_ai))
        return

    if cmd == "demo":
        from .demo import run_demo
        quality = "average"
        target = "The Grand Hotel"
        channels = ["email", "phone"]
        output = None
        i = 1
        while i < len(args):
            if args[i] == "--quality" and i + 1 < len(args):
                quality = args[i + 1]; i += 2
            elif args[i] == "--target" and i + 1 < len(args):
                target = args[i + 1]; i += 2
            elif args[i] == "--channels" and i + 1 < len(args):
                channels = args[i + 1].split(","); i += 2
            elif args[i] == "--output" and i + 1 < len(args):
                output = args[i + 1]; i += 2
            else:
                i += 1
        run_demo(target_name=target, quality=quality, channels=channels, output_html=output)

    elif cmd == "serve":
        import uvicorn
        from .web import app
        port = 8000
        i = 1
        while i < len(args):
            if args[i] == "--port" and i + 1 < len(args):
                port = int(args[i + 1]); i += 2
            else:
                i += 1
        print(f"🌐 Starting dashboard at http://localhost:{port}")
        uvicorn.run(app, host="0.0.0.0", port=port)

    else:
        print(f"Unknown command: {cmd}")
        print("Run with 'help' for usage.")

main()
