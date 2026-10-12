"""Auditable bitsandbytes INT8 replacement for eligible policy linear layers."""

from dataclasses import asdict, dataclass

import torch


@dataclass
class QuantizationReport:
    backend: str
    converted_modules: list[str]
    converted_parameters: int
    excluded_modules: list[str]


def quantize_linear_int8(model, min_parameters=4096, excluded=("lm_head",)):
    import bitsandbytes as bnb

    converted = []
    skipped = []
    parameter_count = 0

    def visit(module, prefix=""):
        nonlocal parameter_count
        for name, child in list(module.named_children()):
            path = f"{prefix}.{name}" if prefix else name
            if isinstance(child, torch.nn.Linear):
                excluded_by_name = any(token in path for token in excluded)
                if excluded_by_name or child.weight.numel() < min_parameters:
                    skipped.append(path)
                    continue
                replacement = bnb.nn.Linear8bitLt(
                    child.in_features,
                    child.out_features,
                    bias=child.bias is not None,
                    has_fp16_weights=False,
                )
                replacement.weight = bnb.nn.Int8Params(
                    child.weight.detach().clone(), requires_grad=False, has_fp16_weights=False
                )
                if child.bias is not None:
                    replacement.bias = torch.nn.Parameter(
                        child.bias.detach().clone(), requires_grad=False
                    )
                replacement = replacement.to(child.weight.device)
                setattr(module, name, replacement)
                converted.append(path)
                parameter_count += child.weight.numel()
            else:
                visit(child, path)

    visit(model)
    if not converted:
        raise RuntimeError("No eligible Linear modules were converted to INT8")
    report = QuantizationReport("bitsandbytes.Linear8bitLt", converted, parameter_count, skipped)
    return model, asdict(report)
