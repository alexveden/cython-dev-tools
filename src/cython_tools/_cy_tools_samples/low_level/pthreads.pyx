"""
Simple example how to run a detached pthread

Cython Tools run command:
cytool run cy_tools_samples/low_level/pthreads.pyx@main
"""
from libc.string cimport strlen, strcpy, strcat, strcmp, strtok
from libc.stdio cimport printf
from libc.stdlib cimport malloc, free
from libc.string cimport strerror
from libc.errno cimport errno, ENOENT
from posix.unistd cimport sleep

DEF N_SECONDS = 20

cdef extern from "pthread.h":
    ctypedef unsigned  long int pthread_t;
    int pthread_detach(pthread_t thread)
    # pthread_create(... , void* attr, ...) - has to be a pthread_attr_t, but this type is ambiguous union
    #    which depends on OS type (maybe it's worth to investigate if needed)
    int pthread_create(pthread_t *thread,  void *attr, void *(*start_routine)(void *), void *arg)
    int pthread_join(pthread_t thread, void **retval);

cdef void * logger(void * args):
    printf('logger: I am a one shot thread! Args: %s\n', <char*> args)
    printf('logger: I am going to start very heavy work which takes: 5 seconds\n')
    sleep(5)
    printf('logger: Done!!! Dont touch the red button\n')
    return NULL

cdef void * logger_detached(void * args):
    printf('logger_detached: I am a one long living detach thread! Args: %s\n', <char *> args)
    printf('logger_detached: Wait for %d seconds\n', N_SECONDS)

    cdef int i
    for i in range(N_SECONDS):
        printf('logger_detached: %d seconds before self destruction\n', N_SECONDS - i)
        sleep(1)
    printf('logger_detached: Boom\n')

cpdef main():
    cdef pthread_t thread;
    cdef pthread_t thread_detached;
    cdef char * test_args = "thread_args!"

    cdef retval = pthread_create(&thread, NULL, &logger, test_args)


    if retval != 0:
        printf('pthread_create error: %s\n', strerror(errno))
        exit(1)

    retval = pthread_create(&thread_detached, NULL, &logger_detached, test_args)
    if retval != 0:
        printf('pthread_create error: %s\n', strerror(errno))
        exit(1)

    pthread_join(thread, NULL)
    if pthread_detach(thread_detached) != 0:
        printf('pthread_detach error: %s\n', strerror(errno))
        exit(1)

    # We also need to do some work in the main thread to let thread run and finish properly
    for i in range(int(N_SECONDS/2)+5):
        printf('main(): tick...\n')
        sleep(2)
    printf('main(): Completed\n')