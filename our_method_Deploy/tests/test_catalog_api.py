import json

from plc_deploy.main import app, get_catalog


def test_catalog_requires_authentication() -> None:
    route = next(route for route in app.routes if getattr(route, "path", None) == "/api/catalog")
    assert len(route.dependant.dependencies) == 1
    body = get_catalog()
    assert body["defaults"] == {
        "vendor": "delta",
        "plc_model": "DVP48ES300R",
        "llm_model": "deepseek-v4-pro",
        "output_language": "st",
    }
    assert {item["id"] for item in body["output_languages"]} == {"st", "ld"}
    ladder = next(item for item in body["output_languages"] if item["id"] == "ld")
    assert ladder["native_targets"] == [
        "delta/DVP48ES300R",
        "delta/AS228T-A",
    ]
    model_ids = {model["id"] for model in body["models"]}
    assert model_ids == {"sonnet-5", "deepseek-v4-pro"}
    sonnet = next(model for model in body["models"] if model["id"] == "sonnet-5")
    assert sonnet["label"] == "Claude Sonnet 5"
    assert sonnet["provider"] == "openai-proxy-anthropic"
    assert sonnet["api_protocol"] == "anthropic"
    assert "teamorouter" not in json.dumps(body["models"], ensure_ascii=False).casefold()
    assert "备用通道" not in json.dumps(body["models"], ensure_ascii=False)
    assert "deepseek-v4-pro" in model_ids
    assert "deepseek-v4-flash" not in model_ids
    assert "kimi-k3" not in model_ids
    assert [vendor["id"] for vendor in body["vendors"]] == ["delta"]
