import argparse
import os
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, send_file, url_for

from visualization_core import build_graph_from_ttl, create_html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a small local web app for RDF visualization.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8502, help="Port (default: 8502)")
    parser.add_argument(
        "--input",
        default=os.path.join("shacl_validation", "rdfGraph_smallExample.ttl"),
        help="Default input Turtle file",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("Notebooks", "rdf_graph_viewer.html"),
        help="Default output HTML file",
    )
    parser.add_argument("--title", default="IUC02 RDF Web Visualization", help="Default visualization title")
    return parser.parse_args()


def create_app(default_input: str, default_output: str, default_title: str) -> Flask:
    app = Flask(__name__)

    template = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <title>IUC02 Visualization Web App</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 24px; max-width: 1100px; }
        .row { margin-bottom: 12px; }
        input[type="text"] { width: 100%; padding: 8px; }
        button { padding: 8px 16px; }
        iframe { width: 100%; height: 760px; border: 1px solid #ddd; margin-top: 18px; }
        .error { color: #b00020; margin: 8px 0; }
        .ok { color: #0a7a2a; margin: 8px 0; }
      </style>
    </head>
    <body>
      <h1>IUC02 RDF Visualization</h1>
      <form method="post" action="{{ url_for('generate') }}">
        <div class="row">
          <label>Input TTL path</label>
          <input type="text" name="input" value="{{ input_value }}" required />
        </div>
        <div class="row">
          <label>Output HTML path</label>
          <input type="text" name="output" value="{{ output_value }}" required />
        </div>
        <div class="row">
          <label>Title</label>
          <input type="text" name="title" value="{{ title_value }}" required />
        </div>
        <button type="submit">Generate Visualization</button>
      </form>

      {% if error %}
        <p class="error">{{ error }}</p>
      {% endif %}

      {% if success %}
        <p class="ok">{{ success }}</p>
        <p><a href="{{ url_for('view_output') }}" target="_blank">Open generated HTML in new tab</a></p>
        <iframe src="{{ url_for('view_output') }}"></iframe>
      {% endif %}
    </body>
    </html>
    """

    state = {
        "input": default_input,
        "output": default_output,
        "title": default_title,
        "error": "",
        "success": "",
        "generated": False,
        "output_abs": "",
    }

    def render_home():
        return render_template_string(
            template,
            input_value=state["input"],
            output_value=state["output"],
            title_value=state["title"],
            error=state["error"],
            success=state["success"],
        )

    @app.get("/")
    def home():
        return render_home()

    @app.post("/generate")
    def generate():
        state["input"] = request.form.get("input", default_input).strip()
        state["output"] = request.form.get("output", default_output).strip()
        state["title"] = request.form.get("title", default_title).strip()
        state["error"] = ""
        state["success"] = ""
        state["generated"] = False

        input_path = Path(state["input"])
        output_path = Path(state["output"])

        if not input_path.exists():
            state["error"] = f"Input file not found: {input_path}"
            return render_home(), 400

        try:
            graph = build_graph_from_ttl(input_path)
            create_html(graph, output_path, state["title"])
        except Exception as exc:
            state["error"] = f"Failed to generate visualization: {exc}"
            return render_home(), 500

        state["generated"] = True
        state["output_abs"] = str(output_path.resolve())
        state["success"] = f"Visualization generated at: {state['output_abs']}"
        return redirect(url_for("home"))

    @app.get("/output")
    def view_output():
        if not state["generated"] or not state["output_abs"]:
            return redirect(url_for("home"))
        return send_file(state["output_abs"])

    return app


def main() -> None:
    args = parse_args()
    app = create_app(args.input, args.output, args.title)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
