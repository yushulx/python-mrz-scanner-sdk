#ifndef __MRZ_RESULT_H__
#define __MRZ_RESULT_H__

#include <Python.h>
#include <structmember.h>

// https://docs.python.org/3/c-api/typeobj.html#typedef-examples
typedef struct 
{
	PyObject_HEAD
    PyObject *confidence;
	PyObject *text;
	PyObject *x1;
	PyObject *y1;
	PyObject *x2;
	PyObject *y2;
	PyObject *x3;
	PyObject *y3;
	PyObject *x4;
	PyObject *y4;
} MrzResult;

static void MrzResult_dealloc(MrzResult *self)
{
	if (self->confidence) Py_DECREF(self->confidence);
    if (self->text) Py_DECREF(self->text);
    if (self->x1) Py_DECREF(self->x1);
    if (self->y1) Py_DECREF(self->y1);
    if (self->x2) Py_DECREF(self->x2);
    if (self->y2) Py_DECREF(self->y2);
    if (self->x3) Py_DECREF(self->x3);
    if (self->y3) Py_DECREF(self->y3);
    if (self->x4) Py_DECREF(self->x4);
    if (self->y4) Py_DECREF(self->y4);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *MrzResult_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    MrzResult *self;

    self = (MrzResult *)type->tp_alloc(type, 0);
    return (PyObject *)self;
}

static PyMemberDef MrzResult_members[] = {
    {"confidence", T_OBJECT_EX, offsetof(MrzResult, confidence), 0, "confidence"},
    {"text", T_OBJECT_EX, offsetof(MrzResult, text), 0, "text"},
    {"x1", T_OBJECT_EX, offsetof(MrzResult, x1), 0, "x1"},
    {"y1", T_OBJECT_EX, offsetof(MrzResult, y1), 0, "y1"},
    {"x2", T_OBJECT_EX, offsetof(MrzResult, x2), 0, "x2"},
    {"y2", T_OBJECT_EX, offsetof(MrzResult, y2), 0, "y2"},
    {"x3", T_OBJECT_EX, offsetof(MrzResult, x3), 0, "x3"},
    {"y3", T_OBJECT_EX, offsetof(MrzResult, y3), 0, "y3"},
    {"x4", T_OBJECT_EX, offsetof(MrzResult, x4), 0, "x4"},
    {"y4", T_OBJECT_EX, offsetof(MrzResult, y4), 0, "y4"},
    {NULL}  /* Sentinel */
};

static PyTypeObject MrzResultType = {
    PyVarObject_HEAD_INIT(NULL, 0) "mrzscanner.MrzResult", /* tp_name */
    sizeof(MrzResult),                                       /* tp_basicsize */
    0,                                                           /* tp_itemsize */
    (destructor)MrzResult_dealloc,                           /* tp_dealloc */
    0,                                                           /* tp_print */
    0,                                                           /* tp_getattr */
    0,                                                           /* tp_setattr */
    0,                                                           /* tp_reserved */
    0,                                                           /* tp_repr */
    0,                                                           /* tp_as_number */
    0,                                                           /* tp_as_sequence */
    0,                                                           /* tp_as_mapping */
    0,                                                           /* tp_hash  */
    0,                                                           /* tp_call */
    0,                                                           /* tp_str */
    PyObject_GenericGetAttr,                                     /* tp_getattro */
    PyObject_GenericSetAttr,                                     /* tp_setattro */
    0,                                                           /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,                    /*tp_flags*/
    "MrzResult",                                             /* tp_doc */
    0,                                                           /* tp_traverse */
    0,                                                           /* tp_clear */
    0,                                                           /* tp_richcompare */
    0,                                                           /* tp_weaklistoffset */
    0,                                                           /* tp_iter */
    0,                                                           /* tp_iternext */
    0,                                                           /* tp_methods */
    MrzResult_members,                                       /* tp_members */
    0,                                                           /* tp_getset */
    0,                                                           /* tp_base */
    0,                                                           /* tp_dict */
    0,                                                           /* tp_descr_get */
    0,                                                           /* tp_descr_set */
    0,                                                           /* tp_dictoffset */
    0,                                                           /* tp_init */
    0,                                                           /* tp_alloc */
    MrzResult_new,                                           /* tp_new */
};

#endif