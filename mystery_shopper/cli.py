"""CLI interface for AI Mystery Shopper."""

import typer
from rich.console import Console

app = typer.Typer(help="🕵️ AI Mystery Shopper — Omnichannel service quality testing")
console = Console()


@app.command()
def demo(
    target: str = typer.Option("The Grand Hotel", help="Target business name"),
    quality: str = typer.Option("average", help="Simulated quality: good, average, poor"),
    channels: str = typer.Option("email,phone", help="Channels to test (comma-separated)"),
    output: str = typer.Option(None, help="Output HTML report path"),
):
    """Run a demo mystery shopping session (no API keys needed)."""
    from .demo import run_demo

    channel_list = [c.strip() for c in channels.split(",")]
    run_demo(
        target_name=target,
        quality=quality,
        channels=channel_list,
        output_html=output,
    )


@app.command()
def email_test(
    target_email: str = typer.Argument(..., help="Target hotel email address"),
    target_name: str = typer.Option("Hotel", help="Target business name"),
    persona: int = typer.Option(0, help="Persona index (0-2)"),
):
    """Send a mystery shopping email to a hotel."""
    from .channels.email import run_email_test

    result = run_email_test(
        target_email=target_email,
        target_name=target_name,
        persona_index=persona,
        send_only=True,
    )
    console.print(f"Status: {result.status.value}")
    if result.summary:
        console.print(f"Summary: {result.summary}")


@app.command()
def phone_test(
    phone_number: str = typer.Argument(..., help="Target phone number"),
    target_name: str = typer.Option("Hotel", help="Target business name"),
    persona: int = typer.Option(0, help="Persona index (0-2)"),
):
    """Make a mystery shopping phone call to a hotel."""
    from .channels.phone import run_phone_test

    result = run_phone_test(
        phone_number=phone_number,
        target_name=target_name,
        persona_index=persona,
    )
    console.print(f"Status: {result.status.value}")
    console.print(f"Score: {result.overall_score}/100")
    if result.summary:
        console.print(f"Summary: {result.summary}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host"),
    port: int = typer.Option(8000, help="Port"),
):
    """Start the web dashboard."""
    import uvicorn
    from .web import app as web_app

    console.print(f"🌐 Starting dashboard at http://{host}:{port}")
    uvicorn.run(web_app, host=host, port=port)


if __name__ == "__main__":
    app()
