"""Short compute/backprop check; run through h100_run.py, never on a default GPU."""

import os

import torch

assert os.environ.get("CUDA_VISIBLE_DEVICES") in {"1", "2", "3", "4", "5", "6", "7"}
assert torch.cuda.is_available()
x = torch.randn(128, 128, device="cuda", dtype=torch.bfloat16, requires_grad=True)
(x @ x).float().square().mean().backward()
torch.cuda.synchronize()
print("PASS", torch.__version__, torch.cuda.get_device_name(0), "BF16 forward/backward")
