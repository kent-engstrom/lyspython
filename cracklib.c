#include <Python.h>
#include <crack.h>

/* See the documentation for cracklib if you want more details */

static PyObject *cracklib_FascistCheck(PyObject *self,
				       PyObject *args)
{
  char *pw;
  char *dictpath;
  char *ret;

  if (!PyArg_ParseTuple(args, "ss", &pw, &dictpath))
    return NULL;

  ret = FascistCheck(pw, dictpath);

  if (ret == NULL)
  {
    Py_INCREF(Py_None);
    return Py_None;
  }
  else
  {
    return Py_BuildValue("s", ret);
  }
}

static PyMethodDef CracklibMethods[] =
{
  {"FascistCheck", cracklib_FascistCheck, 1},
  {NULL,    NULL}
};

void initcracklib()
{
  (void) Py_InitModule("cracklib", CracklibMethods);
}
