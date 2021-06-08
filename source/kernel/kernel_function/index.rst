linux 内核函数
==============

signal函数
----------

我们经常在睡眠的代码中会看到这样的例子:

::

    if(signal_pending(current))
    {
        ret = -ERESTARTSYS;
        return ret;
    }

``-ERESTARTSYS`` 表示信号处理函数处理完毕后重新执行信号函数前的某个系统调用.

signal_pending(current)----->检查当前进程是否有信号需要处理,返回不为0表示有信号需要处理.


