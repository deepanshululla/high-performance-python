// The chapter's contributed Rust/PyO3 section, updated to current crate versions.
//
// Rust gives us the same compiled-kernel speed as the C in ex05/ex10, but with memory
// safety (no buffer overruns) and thread safety enforced by the compiler. The `numpy`
// crate hands NumPy arrays to Rust as `ndarray` views: a read-only view for the input and
// a mutable view for the output, and Rust's borrow checker guarantees they can't alias.
use numpy::ndarray::{ArrayView2, ArrayViewMut2};
use numpy::{PyArray2, PyArrayMethods, PyReadonlyArray2, PyUntypedArrayMethods};
use pyo3::prelude::*;

// Pure Rust: the diffusion stencil over ndarray views. No Python in sight. Every index is
// bounds-checked by Rust, so an off-by-one is a clean panic, not memory corruption.
fn evolve(grid: ArrayView2<f64>, mut out: ArrayViewMut2<f64>, d: f64, dt: f64) {
    let shape = grid.shape();
    for i in 1..(shape[0] - 1) {
        for j in 1..(shape[1] - 1) {
            let laplacian = grid[(i + 1, j)] + grid[(i - 1, j)]
                + grid[(i, j + 1)] + grid[(i, j - 1)]
                - 4.0 * grid[(i, j)];
            out[(i, j)] = grid[(i, j)] + d * dt * laplacian;
        }
    }
}

// The Python-facing wrapper. PyO3 converts the NumPy array to a read-only view, allocates a
// zeroed output array, runs the kernel, and returns the output to Python.
#[pyfunction(name = "evolve")]
#[pyo3(signature = (grid, dt, d=1.0))]
fn evolve_py<'py>(
    py: Python<'py>,
    grid: PyReadonlyArray2<'py, f64>,
    dt: f64,
    d: f64,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let shape = grid.shape();
    let out = PyArray2::<f64>::zeros(py, [shape[0], shape[1]], false);
    evolve(grid.as_array(), out.readwrite().as_array_mut(), d, dt);
    Ok(out)
}

#[pymodule]
fn diffusion_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evolve_py, m)?)?;
    Ok(())
}
