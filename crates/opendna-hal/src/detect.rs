use serde::{Deserialize, Serialize};
use sysinfo::System;

/// Detected hardware capabilities.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareInfo {
    pub cpu_name: String,
    pub cpu_cores: usize,
    pub total_ram_gb: f64,
    pub available_ram_gb: f64,
    pub gpu: Option<GpuInfo>,
    pub os: String,
    pub recommended_tier: ModelTier,
    pub recommended_backend: ComputeBackend,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuInfo {
    pub name: String,
    pub vram_gb: f64,
    pub backend: ComputeBackend,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum ComputeBackend {
    Cuda,
    Metal,
    Rocm,
    DirectML,
    Cpu,
}

impl std::fmt::Display for ComputeBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ComputeBackend::Cuda => write!(f, "CUDA (NVIDIA)"),
            ComputeBackend::Metal => write!(f, "Metal (Apple)"),
            ComputeBackend::Rocm => write!(f, "ROCm (AMD)"),
            ComputeBackend::DirectML => write!(f, "DirectML (Windows)"),
            ComputeBackend::Cpu => write!(f, "CPU"),
        }
    }
}

/// Model complexity tier based on hardware.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, PartialOrd)]
pub enum ModelTier {
    /// 4GB RAM, CPU only - smallest models
    Potato = 1,
    /// 8GB VRAM, RTX 3060 - standard models
    Gaming = 2,
    /// 16GB+ VRAM, RTX 4080/4090 - large models
    Prosumer = 3,
    /// 24GB+ VRAM, A6000/H100 - full suite
    Workstation = 4,
}

impl std::fmt::Display for ModelTier {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ModelTier::Potato => write!(f, "Potato (CPU-only, smallest models)"),
            ModelTier::Gaming => write!(f, "Gaming (GPU, standard models)"),
            ModelTier::Prosumer => write!(f, "Prosumer (GPU, large models)"),
            ModelTier::Workstation => write!(f, "Workstation (GPU, full model suite)"),
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct DeviceCapability {
    pub max_sequence_length: usize,
    pub recommended_precision: Precision,
    pub max_batch_size: usize,
    pub supports_flash_attention: bool,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum Precision {
    Float32,
    Float16,
    BFloat16,
    Int8,
}

impl std::fmt::Display for Precision {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Precision::Float32 => write!(f, "FP32"),
            Precision::Float16 => write!(f, "FP16"),
            Precision::BFloat16 => write!(f, "BF16"),
            Precision::Int8 => write!(f, "INT8"),
        }
    }
}

/// Detect hardware and recommend configuration.
pub fn detect_hardware() -> HardwareInfo {
    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu_name = sys
        .cpus()
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_else(|| "Unknown CPU".to_string());

    let cpu_cores = sys.cpus().len();
    let total_ram_gb = sys.total_memory() as f64 / 1_073_741_824.0;
    let available_ram_gb = sys.available_memory() as f64 / 1_073_741_824.0;

    let os = std::env::consts::OS.to_string();

    // GPU detection is platform-specific and complex.
    // For now, we detect the platform and try basic heuristics.
    let gpu = detect_gpu(&os);

    let recommended_tier = determine_tier(&gpu, total_ram_gb);
    let recommended_backend = gpu
        .as_ref()
        .map(|g| g.backend)
        .unwrap_or(ComputeBackend::Cpu);

    HardwareInfo {
        cpu_name,
        cpu_cores,
        total_ram_gb,
        available_ram_gb,
        gpu,
        os,
        recommended_tier,
        recommended_backend,
    }
}

fn detect_gpu(os: &str) -> Option<GpuInfo> {
    // Try NVIDIA first (most common for ML)
    if let Some(gpu) = detect_nvidia() {
        return Some(gpu);
    }

    // On macOS, assume Apple Silicon with unified memory
    if os == "macos" {
        return Some(GpuInfo {
            name: "Apple Silicon (unified memory)".to_string(),
            vram_gb: 0.0, // Will use system RAM
            backend: ComputeBackend::Metal,
        });
    }

    None
}

fn detect_nvidia() -> Option<GpuInfo> {
    // Try nvidia-smi to detect GPU
    let output = std::process::Command::new("nvidia-smi")
        .args(["--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let line = stdout.lines().next()?;
    let parts: Vec<&str> = line.split(',').map(|s| s.trim()).collect();

    if parts.len() >= 2 {
        let name = parts[0].to_string();
        let vram_mb: f64 = parts[1].parse().unwrap_or(0.0);
        Some(GpuInfo {
            name,
            vram_gb: vram_mb / 1024.0,
            backend: ComputeBackend::Cuda,
        })
    } else {
        None
    }
}

fn determine_tier(gpu: &Option<GpuInfo>, total_ram_gb: f64) -> ModelTier {
    match gpu {
        Some(g) if g.vram_gb >= 24.0 => ModelTier::Workstation,
        Some(g) if g.vram_gb >= 16.0 => ModelTier::Prosumer,
        Some(g) if g.vram_gb >= 6.0 => ModelTier::Gaming,
        Some(g) if g.backend == ComputeBackend::Metal && total_ram_gb >= 16.0 => ModelTier::Gaming,
        Some(g) if g.backend == ComputeBackend::Metal => ModelTier::Potato,
        _ if total_ram_gb >= 16.0 => ModelTier::Potato,
        _ => ModelTier::Potato,
    }
}

pub fn get_device_capability(hw: &HardwareInfo) -> DeviceCapability {
    match hw.recommended_tier {
        ModelTier::Potato => DeviceCapability {
            max_sequence_length: 256,
            recommended_precision: Precision::Float32,
            max_batch_size: 1,
            supports_flash_attention: false,
        },
        ModelTier::Gaming => DeviceCapability {
            max_sequence_length: 512,
            recommended_precision: Precision::Float16,
            max_batch_size: 4,
            supports_flash_attention: true,
        },
        ModelTier::Prosumer => DeviceCapability {
            max_sequence_length: 1024,
            recommended_precision: Precision::Float16,
            max_batch_size: 8,
            supports_flash_attention: true,
        },
        ModelTier::Workstation => DeviceCapability {
            max_sequence_length: 2048,
            recommended_precision: Precision::Float16,
            max_batch_size: 16,
            supports_flash_attention: true,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_hardware() {
        let hw = detect_hardware();
        assert!(hw.cpu_cores > 0);
        assert!(hw.total_ram_gb > 0.0);
    }

    #[test]
    fn test_tier_determination() {
        let gpu_24gb = Some(GpuInfo {
            name: "RTX 4090".to_string(),
            vram_gb: 24.0,
            backend: ComputeBackend::Cuda,
        });
        assert_eq!(determine_tier(&gpu_24gb, 32.0), ModelTier::Workstation);

        assert_eq!(determine_tier(&None, 8.0), ModelTier::Potato);
    }
}
