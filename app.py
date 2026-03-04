"""
AI Humanizer — Flask Web Application
A local tool for humanizing AI-generated text using Ollama models.
"""

import os
import json
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from humanizer.engine import HumanizerEngine

app = Flask(__name__)

# Configuration
DEFAULT_MODEL = os.environ.get("HUMANIZER_MODEL", "mistral")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Initialize engine
engine = HumanizerEngine(model=DEFAULT_MODEL, ollama_url=OLLAMA_URL)


@app.route("/")
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def status():
    """Check system status (Ollama running, model available)."""
    return jsonify(engine.check_status())


@app.route("/api/models", methods=["GET"])
def list_models():
    """List available Ollama models."""
    models = engine.client.list_models()
    return jsonify({
        "models": models,
        "current": engine.model,
    })


@app.route("/api/model", methods=["POST"])
def set_model():
    """Switch the active model."""
    data = request.get_json()
    model = data.get("model", "").strip()
    if not model:
        return jsonify({"error": "No model specified."}), 400
    engine.set_model(model)
    return jsonify({"message": f"Switched to {model}", "model": model})


@app.route("/api/humanize", methods=["POST"])
def humanize():
    """Humanize text (non-streaming)."""
    data = request.get_json()

    text = data.get("text", "").strip()
    tone = data.get("tone", "normal").lower()
    intensity = float(data.get("intensity", 0.7))

    if not text:
        return jsonify({"error": "No text provided."}), 400

    if tone not in ("academic", "casual", "normal"):
        return jsonify({"error": f"Invalid tone: {tone}"}), 400

    intensity = max(0.0, min(1.0, intensity))

    result = engine.humanize(text=text, tone=tone, intensity=intensity)

    if "error" in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route("/api/humanize/stream", methods=["POST"])
def humanize_stream():
    """Humanize text with streaming response."""
    data = request.get_json()

    text = data.get("text", "").strip()
    tone = data.get("tone", "normal").lower()

    if not text:
        return jsonify({"error": "No text provided."}), 400

    def generate():
        for token in engine.humanize_stream(text=text, tone=tone):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AI HUMANIZER — Local Text Humanization Tool")
    print("=" * 60)

    status_info = engine.check_status()
    print(f"\n  Status: {status_info['message']}")
    print(f"  Model:  {engine.model}")
    print(f"  Ollama: {OLLAMA_URL}")
    print(f"\n  Open http://localhost:5000 in your browser")
    print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
