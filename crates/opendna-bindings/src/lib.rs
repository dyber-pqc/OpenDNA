use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};

/// Python wrapper for Protein.
#[pyclass]
#[derive(Clone)]
struct PyProtein {
    inner: opendna_core::Protein,
}

#[pymethods]
impl PyProtein {
    #[new]
    fn new(name: String, sequence: String) -> Self {
        Self {
            inner: opendna_core::Protein::new(name, sequence),
        }
    }

    #[getter]
    fn id(&self) -> String {
        self.inner.id.clone()
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }

    #[getter]
    fn sequence(&self) -> String {
        self.inner.sequence.residues.clone()
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    fn __repr__(&self) -> String {
        format!(
            "Protein(name='{}', length={}, id='{}')",
            self.inner.name,
            self.inner.len(),
            self.inner.id,
        )
    }
}

/// Python wrapper for hardware detection.
#[pyfunction]
fn detect_hardware() -> PyResult<String> {
    let hw = opendna_hal::detect::detect_hardware();
    serde_json::to_string_pretty(&hw).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

/// Python wrapper for PDB parsing.
#[pyfunction]
fn parse_pdb(content: &str) -> PyResult<String> {
    let structure = opendna_core::parsers::parse_pdb(content)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    serde_json::to_string(&structure).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

/// Python wrapper for FASTA parsing.
#[pyfunction]
fn parse_fasta(content: &str) -> PyResult<Vec<(String, String)>> {
    opendna_core::parsers::parse_fasta(content)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// OpenDNA native Python module.
#[pymodule]
fn opendna_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyProtein>()?;
    m.add_function(wrap_pyfunction!(detect_hardware, m)?)?;
    m.add_function(wrap_pyfunction!(parse_pdb, m)?)?;
    m.add_function(wrap_pyfunction!(parse_fasta, m)?)?;
    Ok(())
}
