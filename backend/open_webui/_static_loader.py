from pathlib import Path
import json
import os
import logging

log = logging.getLogger(__name__)


def load_static_models(app):
    try:
        # OPEN_WEBUI_DIR is available in env.py; try to import it, else infer
        try:
            from open_webui.env import OPEN_WEBUI_DIR
        except Exception:
            OPEN_WEBUI_DIR = Path(__file__).resolve().parent

        static_models_path = Path(os.environ.get("STATIC_MODELS_FILE", OPEN_WEBUI_DIR / "static_models.json"))
        static_models_example = Path(os.environ.get("STATIC_MODELS_EXAMPLE_FILE", OPEN_WEBUI_DIR / "static_models.example.json"))

        static_models = []
        if static_models_path.exists():
            try:
                static_models = json.loads(static_models_path.read_text())
            except Exception:
                log.exception(f"Unable to parse static models file: {static_models_path}")
        elif static_models_example.exists():
            try:
                static_models = json.loads(static_models_example.read_text())
            except Exception:
                log.exception(f"Unable to parse static models example file: {static_models_example}")

        app.state.OPENAI_STATIC_MODELS = {}

        if not static_models:
            return

        for m in static_models:
            try:
                model_id = m.get("id") or m.get("name")
                base_url = m.get("base_url", "https://api.openai.com/v1")
                if base_url.endswith("/"):
                    base_url = base_url[:-1]

                # find or register base_url in OPENAI_API_BASE_URLS
                base_urls = app.state.config.OPENAI_API_BASE_URLS
                if base_url in base_urls:
                    url_idx = base_urls.index(base_url)
                else:
                    base_urls = base_urls + [base_url]
                    app.state.config.OPENAI_API_BASE_URLS = base_urls

                    # ensure keys list length matches
                    keys = app.state.config.OPENAI_API_KEYS
                    if isinstance(keys, list) and len(keys) == 1 and keys[0]:
                        # broadcast single key
                        keys = [keys[0]] * len(base_urls)
                    else:
                        if len(keys) < len(base_urls):
                            keys = keys + [""] * (len(base_urls) - len(keys))
                    app.state.config.OPENAI_API_KEYS = keys

                    url_idx = base_urls.index(base_url)

                model_obj = {
                    **m,
                    "name": m.get("name", model_id),
                    "owned_by": m.get("owned_by", "static"),
                    "connection_type": m.get("connection_type", "external"),
                    "urlIdx": url_idx,
                }
                app.state.OPENAI_STATIC_MODELS[model_id] = model_obj
            except Exception:
                log.exception(f"Failed loading static model: {m}")

    except Exception:
        log.exception("Error while loading static models")
