/* python_interface.c -- a raw CPython extension wrapping cdiffusion's evolve().
 *
 * This is the book's Example 8-23: the "last resort" FFI. Compare its bulk to ex05's
 * cffi binding (four lines of Python). Every type check, dimension check, contiguity
 * check, and the manual reference-count bump on the returned array is spelled out by
 * hand -- which is exactly the chapter's cautionary point. The payoff is that there is no
 * per-call marshalling layer between Python and the kernel, so it is minutely the fastest
 * way to call this C function.
 */
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION

#include <Python.h>
#include <numpy/arrayobject.h>
#include "cdiffusion.h"

static char module_docstring[] =
    "Optimized 2D diffusion via a hand-written CPython extension.";
static char evolve_docstring[] =
    "evolve(data, next_grid, dt, D=1.0) -- one diffusion step on a 512x512 grid.";

static PyObject *py_evolve(PyObject *self, PyObject *args) {
    PyArrayObject *data, *next_grid;
    double dt, D = 1.0;

    /* Parse evolve(data, next_grid, dt, D=1) -- two objects, a double, optional double. */
    if (!PyArg_ParseTuple(args, "OOd|d", &data, &next_grid, &dt, &D)) {
        PyErr_SetString(PyExc_RuntimeError, "Invalid arguments");
        return NULL;
    }
    if (!PyArray_Check(data) || !PyArray_ISCONTIGUOUS(data)) {
        PyErr_SetString(PyExc_RuntimeError, "data is not a contiguous array.");
        return NULL;
    }
    if (!PyArray_Check(next_grid) || !PyArray_ISCONTIGUOUS(next_grid)) {
        PyErr_SetString(PyExc_RuntimeError, "next_grid is not a contiguous array.");
        return NULL;
    }
    if (PyArray_TYPE(data) != PyArray_TYPE(next_grid)) {
        PyErr_SetString(PyExc_RuntimeError, "next_grid and data should have same type.");
        return NULL;
    }
    if (PyArray_NDIM(data) != 2 || PyArray_NDIM(next_grid) != 2) {
        PyErr_SetString(PyExc_RuntimeError, "data/next_grid should be two dimensional");
        return NULL;
    }

    evolve(PyArray_DATA(data), PyArray_DATA(next_grid), D, dt);

    Py_XINCREF(next_grid);
    return (PyObject *)next_grid;
}

static PyMethodDef module_methods[] = {
    {"evolve", (PyCFunction)py_evolve, METH_VARARGS, evolve_docstring},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef cdiffusionmodule = {
    PyModuleDef_HEAD_INIT, "cdiffusion", module_docstring, -1, module_methods,
};

PyMODINIT_FUNC PyInit_cdiffusion(void) {
    PyObject *m = PyModule_Create(&cdiffusionmodule);
    if (m == NULL) {
        return NULL;
    }
    import_array();  /* wire up the numpy C-API */
    return m;
}
