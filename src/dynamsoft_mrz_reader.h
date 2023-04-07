#ifndef __MRZ_READER_H__
#define __MRZ_READER_H__

#include <Python.h>
#include <structmember.h>
#include "DynamsoftLabelRecognizer.h"
#include "mrz_result.h"
#include <thread>
#include <condition_variable>
#include <mutex>
#include <queue>
#include <functional>

class Task
{
public:
    std::function<void()> func;
    unsigned char* buffer;
};

class WorkerThread
{
public:
    std::mutex m;
    std::condition_variable cv;
    std::queue<Task> tasks = {};
    volatile bool running;
	std::thread t;
};

typedef struct
{
    PyObject_HEAD 
    void *handler;
    PyObject *callback;
    WorkerThread *worker;
} DynamsoftMrzReader;

void clearTasks(DynamsoftMrzReader *self)
{
    if (self->worker->tasks.size() > 0)
    {
        for (int i = 0; i < self->worker->tasks.size(); i++)
        {
            free(self->worker->tasks.front().buffer);
            self->worker->tasks.pop();
        }
    }
}

void clear(DynamsoftMrzReader *self)
{
    if (self->callback)
    {
        Py_XDECREF(self->callback);
        self->callback = NULL;
    }

    if (self->worker)
    {
        self->worker->running = false;
        clearTasks(self);
        self->worker->cv.notify_one();
        self->worker->t.join();
        delete self->worker;
        self->worker = NULL;
        printf("Quit native thread.\n");
    }
}

static int DynamsoftMrzReader_clear(DynamsoftMrzReader *self)
{
    clear(self);
    if (self->handler)
    {
        DLR_DestroyInstance(self->handler);
        self->handler = NULL;
    }

    return 0;
}

static void DynamsoftMrzReader_dealloc(DynamsoftMrzReader *self)
{
    DynamsoftMrzReader_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *DynamsoftMrzReader_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    DynamsoftMrzReader *self;

    self = (DynamsoftMrzReader *)type->tp_alloc(type, 0);
    if (self != NULL)
    {
        self->handler = DLR_CreateInstance();
        self->worker = NULL;
        self->callback = NULL;
    }

    return (PyObject *)self;
}

PyObject *createPyList(DLR_ResultArray *pResults)
{
    int count = pResults->resultsCount;

    // Create a Python object to store results
    PyObject *list = PyList_New(0);
    for (int i = 0; i < count; i++)
    {
        DLR_Result *mrzResult = pResults->results[i];
        int lCount = mrzResult->lineResultsCount;
        for (int j = 0; j < lCount; j++)
        {
            // printf("Line result %d: %s\n", j, mrzResult->lineResults[j]->text);

            DM_Point *points = mrzResult->lineResults[j]->location.points;
            int x1 = points[0].x;
            int y1 = points[0].y;
            int x2 = points[1].x;
            int y2 = points[1].y;
            int x3 = points[2].x;
            int y3 = points[2].y;
            int x4 = points[3].x;
            int y4 = points[3].y;
            MrzResult *result = PyObject_New(MrzResult, &MrzResultType);
            result->confidence = Py_BuildValue("i", mrzResult->lineResults[j]->confidence);
            result->text = PyUnicode_FromString(mrzResult->lineResults[j]->text);
            result->x1 = Py_BuildValue("i", x1);
            result->y1 = Py_BuildValue("i", y1);
            result->x2 = Py_BuildValue("i", x2);
            result->y2 = Py_BuildValue("i", y2);
            result->x3 = Py_BuildValue("i", x3);
            result->y3 = Py_BuildValue("i", y3);
            result->x4 = Py_BuildValue("i", x4);
            result->y4 = Py_BuildValue("i", y4);

            PyList_Append(list, (PyObject *)result);
        }
    }

    return list;
}

static PyObject *createPyResults(DynamsoftMrzReader *self)
{
    DLR_ResultArray *pResults = NULL;
    DLR_GetAllResults(self->handler, &pResults);
    if (!pResults)
    {
        return NULL;
    }

    PyObject *list = createPyList(pResults);

    // Release memory
    DLR_FreeResults(&pResults);

    return list;
}

/**
 * Recognize MRZ from image files.
 *
 * @param string filename
 *
 * @return MrzResult list
 */
static PyObject *decodeFile(PyObject *obj, PyObject *args)
{
    DynamsoftMrzReader *self = (DynamsoftMrzReader *)obj;

    char *pFileName; // File name
    if (!PyArg_ParseTuple(args, "s", &pFileName))
    {
        return NULL;
    }

    int ret = DLR_RecognizeByFile(self->handler, pFileName, "locr");
    if (ret)
    {
        printf("Detection error: %s\n", DLR_GetErrorString(ret));
    }

    PyObject *list = createPyResults(self);
    return list;
}

/**
 * Recognize MRZ from OpenCV Mat.
 *
 * @param Mat image
 *
 * @return MrzResult list
 */
static PyObject *decodeMat(PyObject *obj, PyObject *args)
{
    DynamsoftMrzReader *self = (DynamsoftMrzReader *)obj;

    PyObject *o;
    if (!PyArg_ParseTuple(args, "O", &o))
        return NULL;

    Py_buffer *view;
    int nd;
    PyObject *memoryview = PyMemoryView_FromObject(o);
    if (memoryview == NULL)
    {
        PyErr_Clear();
        return NULL;
    }

    view = PyMemoryView_GET_BUFFER(memoryview);
    char *buffer = (char *)view->buf;
    nd = view->ndim;
    int len = view->len;
    int stride = view->strides[0];
    int width = view->strides[0] / view->strides[1];
    int height = len / stride;

    ImagePixelFormat format = IPF_RGB_888;

    if (width == stride)
    {
        format = IPF_GRAYSCALED;
    }
    else if (width * 3 == stride)
    {
        format = IPF_RGB_888;
    }
    else if (width * 4 == stride)
    {
        format = IPF_ARGB_8888;
    }

    ImageData data;
    data.bytes = (unsigned char *)buffer;
    data.width = width;
    data.height = height;
    data.stride = stride;
    data.format = format;
    data.bytesLength = len;

    int ret = DLR_RecognizeByBuffer(self->handler, &data, "locr");
    if (ret)
    {
        printf("Detection error: %s\n", DLR_GetErrorString(ret));
    }

    PyObject *list = createPyResults(self);

    Py_DECREF(memoryview);

    return list;
}

void onResultReady(DynamsoftMrzReader *self)
{
    PyGILState_STATE gstate;
    gstate = PyGILState_Ensure();
    PyObject *list = createPyResults(self);
    PyObject *result = PyObject_CallFunction(self->callback, "O", list);
    if (result != NULL)
        Py_DECREF(result);

    PyGILState_Release(gstate);
}

void scan(DynamsoftMrzReader *self, unsigned char *buffer, int width, int height, int stride, ImagePixelFormat format, int len)
{
    ImageData data;
    data.bytes = buffer;
    data.width = width;
    data.height = height;
    data.stride = stride;
    data.format = format;
    data.bytesLength = len;

    int ret = DLR_RecognizeByBuffer(self->handler, &data, "locr");
    if (ret)
    {
        printf("Detection error: %s\n", DLR_GetErrorString(ret));
    }

    free(buffer);
    if (self->callback)
    {
        onResultReady(self);
    }
}

/**
 * Recognize MRZ from OpenCV Mat asynchronously.
 *
 * @param Mat image
 *
 */
static PyObject *decodeMatAsync(PyObject *obj, PyObject *args)
{
    DynamsoftMrzReader *self = (DynamsoftMrzReader *)obj;
    PyObject *o;
    if (!PyArg_ParseTuple(args, "O", &o))
        Py_BuildValue("i", -1);

    Py_buffer *view;
    int nd;
    PyObject *memoryview = PyMemoryView_FromObject(o);
    if (memoryview == NULL)
    {
        PyErr_Clear();
        Py_BuildValue("i", -1);
    }

    view = PyMemoryView_GET_BUFFER(memoryview);
    char *buffer = (char *)view->buf;
    nd = view->ndim;
    int len = view->len;
    int stride = view->strides[0];
    int width = view->strides[0] / view->strides[1];
    int height = len / stride;

    ImagePixelFormat format = IPF_RGB_888;

    if (width == stride)
    {
        format = IPF_GRAYSCALED;
    }
    else if (width * 3 == stride)
    {
        format = IPF_RGB_888;
    }
    else if (width * 4 == stride)
    {
        format = IPF_ARGB_8888;
    }

    unsigned char *data = (unsigned char *)malloc(len);
    memcpy(data, buffer, len);

    std::unique_lock<std::mutex> lk(self->worker->m);
    clearTasks(self);
    std::function<void()> task_function = std::bind(scan, self, data, width, height, stride, format, len);
    Task task;
    task.func = task_function;
    task.buffer = data;
    self->worker->tasks.push(task);
    self->worker->cv.notify_one();
    lk.unlock();
    
    Py_DECREF(memoryview);
    return Py_BuildValue("i", 0);
}

/**
 * Load MRZ configuration file.
 *
 * @param string template content
 *
 * @return loading status
 */
static PyObject *loadModel(PyObject *obj, PyObject *args)
{
    DynamsoftMrzReader *self = (DynamsoftMrzReader *)obj;

    char *settings; // File name
    if (!PyArg_ParseTuple(args, "s", &settings))
    {
        Py_BuildValue("i", -1);
    }

    char errorMsgBuffer[512];
    int ret = DLR_AppendSettingsFromString(self->handler, settings, errorMsgBuffer, 512);
    printf("Load MRZ model: %s\n", errorMsgBuffer);

    return Py_BuildValue("i", ret);
}

void run(DynamsoftMrzReader *self)
{
    while (self->worker->running)
    {
        std::function<void()> task;
        std::unique_lock<std::mutex> lk(self->worker->m);
        self->worker->cv.wait(lk, [&]
                              { return !self->worker->tasks.empty() || !self->worker->running; });
        if (!self->worker->running)
		{
			break;
		}
        task = std::move(self->worker->tasks.front().func);
        self->worker->tasks.pop();
        lk.unlock();

        task();
    }
}

/**
 * Register callback function to receive MRZ decoding result asynchronously.
 */
static PyObject *addAsyncListener(PyObject *obj, PyObject *args)
{
    DynamsoftMrzReader *self = (DynamsoftMrzReader *)obj;

    PyObject *callback = NULL;
    if (!PyArg_ParseTuple(args, "O", &callback))
    {
        Py_BuildValue("i", -1);
    }

    if (!PyCallable_Check(callback))
    {
        PyErr_SetString(PyExc_TypeError, "parameter must be callable");
        Py_BuildValue("i", -1);
    }
    else
    {
        Py_XINCREF(callback);       /* Add a reference to new callback */
        Py_XDECREF(self->callback); /* Dispose of previous callback */
        self->callback = callback;
    }

    if (self->worker == NULL)
    {
        self->worker = new WorkerThread();
        self->worker->running = true;
        self->worker->t = std::thread(&run, self);
    }

    printf("Running native thread...\n");
    return Py_BuildValue("i", 0);
}

/**
 * Clear native thread and tasks.
 */
static PyObject *clearAsyncListener(PyObject *obj, PyObject *args)
{
    DynamsoftMrzReader *self = (DynamsoftMrzReader *)obj;
    clear(self);
    return Py_BuildValue("i", 0);
}

static PyMethodDef instance_methods[] = {
    {"decodeFile", decodeFile, METH_VARARGS, NULL},
    {"decodeMat", decodeMat, METH_VARARGS, NULL},
    {"loadModel", loadModel, METH_VARARGS, NULL},
    {"addAsyncListener", addAsyncListener, METH_VARARGS, NULL},
    {"decodeMatAsync", decodeMatAsync, METH_VARARGS, NULL},
    {"clearAsyncListener", clearAsyncListener, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}};

static PyTypeObject DynamsoftMrzReaderType = {
    PyVarObject_HEAD_INIT(NULL, 0) "mrzscanner.DynamsoftMrzReader", /* tp_name */
    sizeof(DynamsoftMrzReader),                                     /* tp_basicsize */
    0,                                                              /* tp_itemsize */
    (destructor)DynamsoftMrzReader_dealloc,                         /* tp_dealloc */
    0,                                                              /* tp_print */
    0,                                                              /* tp_getattr */
    0,                                                              /* tp_setattr */
    0,                                                              /* tp_reserved */
    0,                                                              /* tp_repr */
    0,                                                              /* tp_as_number */
    0,                                                              /* tp_as_sequence */
    0,                                                              /* tp_as_mapping */
    0,                                                              /* tp_hash  */
    0,                                                              /* tp_call */
    0,                                                              /* tp_str */
    PyObject_GenericGetAttr,                                        /* tp_getattro */
    PyObject_GenericSetAttr,                                        /* tp_setattro */
    0,                                                              /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,                       /*tp_flags*/
    "DynamsoftMrzReader",                                           /* tp_doc */
    0,                                                              /* tp_traverse */
    0,                                                              /* tp_clear */
    0,                                                              /* tp_richcompare */
    0,                                                              /* tp_weaklistoffset */
    0,                                                              /* tp_iter */
    0,                                                              /* tp_iternext */
    instance_methods,                                               /* tp_methods */
    0,                                                              /* tp_members */
    0,                                                              /* tp_getset */
    0,                                                              /* tp_base */
    0,                                                              /* tp_dict */
    0,                                                              /* tp_descr_get */
    0,                                                              /* tp_descr_set */
    0,                                                              /* tp_dictoffset */
    0,                                                              /* tp_init */
    0,                                                              /* tp_alloc */
    DynamsoftMrzReader_new,                                         /* tp_new */
};

#endif