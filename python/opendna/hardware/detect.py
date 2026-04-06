"""Hardware detection and optimization for OpenDNA."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ComputeBackend(str, Enum):
    CUDA = "cuda"
    METAL = "metal"
    ROCM = "rocm"
    DIRECTML = "directml"
    CPU = "cpu"


class ModelTier(str, Enum):
    POTATO = "potato"
    GAMING = "gaming"
    PROSUMER = "prosumer"
    WORKSTATION = "workstation"


class Precision(str, Enum):
    FLOAT32 = "fp32"
    FLOAT16 = "fp16"
    BFLOAT16 = "bf16"
    INT8 = "int8"


@dataclass
class GpuInfo:
    name: str
    vram_gb: float
    backend: ComputeBackend


@dataclass
class HardwareInfo:
    cpu_name: str
    cpu_cores: int
    total_ram_gb: float
    gpu: Optional[GpuInfo]
    os: str
    recommended_tier: ModelTier
    recommended_backend: ComputeBackend
    recommended_precision: Precision

    def summary(self) -> str:
        lines = [
            f"CPU: {self.cpu_name} ({self.cpu_cores} cores)",
            f"RAM: {self.total_ram_gb:.1f} GB",
        ]
        if self.gpu:
            lines.append(f"GPU: {self.gpu.name} ({self.gpu.vram_gb:.1f} GB VRAM)")
        else:
            lines.append("GPU: None detected")
        lines.extend([
            f"Backend: {self.recommended_backend.value}",
            f"Tier: {self.recommended_tier.value}",
            f"Precision: {self.recommended_precision.value}",
        ])
        return "\n".join(lines)


def detect_hardware() -> HardwareInfo:
    """Detect system hardware and recommend configuration."""
    import psutil

    cpu_name = platform.processor() or "Unknown"
    cpu_cores = psutil.cpu_count(logical=True) or 1
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    os_name = platform.system()

    gpu = _detect_gpu(os_name)

    tier = _determine_tier(gpu, total_ram_gb)
    backend = gpu.backend if gpu else ComputeBackend.CPU
    precision = _determine_precision(gpu, tier)

    return HardwareInfo(
        cpu_name=cpu_name,
        cpu_cores=cpu_cores,
        total_ram_gb=total_ram_gb,
        gpu=gpu,
        os=os_name,
        recommended_tier=tier,
        recommended_backend=backend,
        recommended_precision=precision,
    )


def _detect_gpu(os_name: str) -> Optional[GpuInfo]:
    # Try NVIDIA
    gpu = _detect_nvidia()
    if gpu:
        return gpu

    # Try torch detection as fallback
    gpu = _detect_via_torch()
    if gpu:
        return gpu

    # macOS = Apple Silicon
    if os_name == "Darwin":
        return GpuInfo(
            name="Apple Silicon",
            vram_gb=0,  # Unified memory
            backend=ComputeBackend.METAL,
        )

    return None


def _detect_nvidia() -> Optional[GpuInfo]:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            return GpuInfo(
                name=parts[0],
                vram_gb=float(parts[1]) / 1024,
                backend=ComputeBackend.CUDA,
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def _detect_via_torch() -> Optional[GpuInfo]:
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            return GpuInfo(name=name, vram_gb=vram, backend=ComputeBackend.CUDA)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return GpuInfo(name="Apple Silicon (MPS)", vram_gb=0, backend=ComputeBackend.METAL)
    except ImportError:
        pass
    return None


def _determine_tier(gpu: Optional[GpuInfo], ram_gb: float) -> ModelTier:
    if gpu is None:
        return ModelTier.POTATO
    if gpu.vram_gb >= 24:
        return ModelTier.WORKSTATION
    if gpu.vram_gb >= 16:
        return ModelTier.PROSUMER
    if gpu.vram_gb >= 6 or gpu.backend == ComputeBackend.METAL:
        return ModelTier.GAMING
    return ModelTier.POTATO


def _determine_precision(gpu: Optional[GpuInfo], tier: ModelTier) -> Precision:
    if tier == ModelTier.POTATO:
        return Precision.FLOAT32
    if gpu and gpu.backend == ComputeBackend.CUDA:
        return Precision.FLOAT16
    if gpu and gpu.backend == ComputeBackend.METAL:
        return Precision.FLOAT32  # MPS has limited FP16 support
    return Precision.FLOAT32


def get_torch_device(hw: Optional[HardwareInfo] = None) -> str:
    """Get the best torch device string, verifying torch actually supports it."""
    if hw is None:
        hw = detect_hardware()
    try:
        import torch
        if hw.recommended_backend == ComputeBackend.CUDA and torch.cuda.is_available():
            return "cuda"
        if hw.recommended_backend == ComputeBackend.METAL and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"
