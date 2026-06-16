GRAPH_API_KEY: str | None = None
GRAPH_MODEL_NAME: str | None = None
GRAPH_TEMPERATURE: float | None = None


def configure_graph(
    api_key: str | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
) -> None:
    global GRAPH_API_KEY, GRAPH_MODEL_NAME, GRAPH_TEMPERATURE

    GRAPH_API_KEY = api_key
    GRAPH_MODEL_NAME = model_name
    GRAPH_TEMPERATURE = temperature


def get_graph_settings() -> dict:
    return {
        "api_key": GRAPH_API_KEY,
        "model_name": GRAPH_MODEL_NAME,
        "temperature": GRAPH_TEMPERATURE,
    }
