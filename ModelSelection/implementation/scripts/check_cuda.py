import torch

assert torch.cuda.is_available(), "CUDA unavailable"
print("OK", torch.cuda.get_device_name(0))
