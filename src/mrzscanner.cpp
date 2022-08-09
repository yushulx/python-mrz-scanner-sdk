// Python includes
#include <Python.h>

// STD includes
#include <stdio.h>

#include "dynamsoft_mrz_reader.h"

#define INITERROR return NULL

struct module_state {
    PyObject *error;
};

#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))

static PyObject *
error_out(PyObject *m)
{
    struct module_state *st = GETSTATE(m);
    PyErr_SetString(st->error, "something bad happened");
    return NULL;
}

#define DBR_NO_MEMORY 0
#define DBR_SUCCESS 1

// #define LOG_OFF

#ifdef LOG_OFF

#define printf(MESSAGE, __VA_ARGS__)

#endif

#define DEFAULT_MEMORY_SIZE 4096

static PyObject *createInstance(PyObject *obj, PyObject *args)
{
    if (PyType_Ready(&DynamsoftMrzReaderType) < 0)
         INITERROR;

    DynamsoftMrzReader* reader = PyObject_New(DynamsoftMrzReader, &DynamsoftMrzReaderType);
    reader->handler = DLR_CreateInstance();
    return (PyObject *)reader;
}

static PyObject *initLicense(PyObject *obj, PyObject *args)
{
    char *pszLicense;
    if (!PyArg_ParseTuple(args, "s", &pszLicense))
    {
        return NULL;
    }

    char errorMsgBuffer[512];
	// Click https://www.dynamsoft.com/customer/license/trialLicense/?product=dbr to get a trial license.
	int ret = DLR_InitLicense(pszLicense, errorMsgBuffer, 512);
	printf("DLR_InitLicense: %s\n", errorMsgBuffer);

    return Py_BuildValue("i", ret);
}

static PyMethodDef mrzscanner_methods[] = {
  {"initLicense", initLicense, METH_VARARGS, "Set license to activate the SDK"},
  {"createInstance", createInstance, METH_VARARGS, "Create Dynamsoft MRZ Reader object"},
  {NULL, NULL, 0, NULL}       
};

static struct PyModuleDef mrzscanner_module_def = {
  PyModuleDef_HEAD_INIT,
  "mrzscanner",
  "Internal \"mrzscanner\" module",
  -1,
  mrzscanner_methods
};

// https://docs.python.org/3/c-api/module.html
// https://docs.python.org/3/c-api/dict.html
PyMODINIT_FUNC PyInit_mrzscanner(void)
{
	PyObject *module = PyModule_Create(&mrzscanner_module_def);
    if (module == NULL)
        INITERROR;

    
    if (PyType_Ready(&DynamsoftMrzReaderType) < 0)
       INITERROR;

    Py_INCREF(&DynamsoftMrzReaderType);
    PyModule_AddObject(module, "DynamsoftMrzReader", (PyObject *)&DynamsoftMrzReaderType);
    
    if (PyType_Ready(&MrzResultType) < 0)
       INITERROR;

    Py_INCREF(&MrzResultType);
    PyModule_AddObject(module, "MrzResult", (PyObject *)&MrzResultType);

	PyModule_AddStringConstant(module, "version", DLR_GetVersion());
    return module;
}

