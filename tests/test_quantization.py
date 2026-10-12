import pytest

torch = pytest.importorskip("torch")

from smolvla_service.quantization import quantize_linear_int8


class FakeInt8(torch.nn.Linear):
    def __init__(self, in_features, out_features, bias=True, **_):
        super().__init__(in_features, out_features, bias=bias)

    def forward(self, value):
        return torch.zeros(*value.shape[:-1], self.out_features, dtype=value.dtype)


class FakeBnb:
    class nn:
        Linear8bitLt = FakeInt8

        @staticmethod
        def Int8Params(tensor, **_):
            return torch.nn.Parameter(tensor, requires_grad=False)


def test_quantization_replaces_large_linears_and_reports_exclusions(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "bitsandbytes", FakeBnb)
    model = torch.nn.ModuleDict(
        {"large": torch.nn.Linear(64, 64), "small": torch.nn.Linear(2, 2),
         "lm_head": torch.nn.Linear(64, 64)}
    )
    result, report = quantize_linear_int8(model)
    assert isinstance(result["large"], FakeInt8)
    assert isinstance(result["small"], torch.nn.Linear)
    assert isinstance(result["lm_head"], torch.nn.Linear)
    assert report["converted_modules"] == ["large"]
    assert report["converted_parameters"] == 4096
    assert sorted(report["excluded_modules"]) == ["lm_head", "small"]
    output = result["large"](torch.ones(1, 64, dtype=torch.int8))
    assert output.is_floating_point()
