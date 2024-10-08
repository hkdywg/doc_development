stdlib标准库
==============

stdlib.h头文件定义了四个变量类型，一些宏和各种通用工具函数

stdlib定义的变量
--------------------

================    ===============================================================================
    变量　                              变量说明
----------------    -------------------------------------------------------------------------------
 size_t               无符号整数类型
 wchar_t                宽字符常量大小的整数类型
 div_t                  div函数返回的结构体
 ldiv_t                 ldiv函数返回的结构体
================    ===============================================================================

stdlib定义的宏
----------------

================    ===============================================================================
    宏　　                          说明
----------------    -------------------------------------------------------------------------------
 NULL                   空指针常量
 EXIT_FAILURE           exit函数失败返回返回的值
 EXIT_SUCCESS           exit函数成功返回的值
 RAND_MAX               rand函数返回的最大值
 MB_CUR_MAX             表示在多字节字符集中的最大字符数，不能大于MB_LEN_MAX
================    ===============================================================================

stdlib函数
-------------


=====================================================================    ======================================================================================================================================
  函数名　　                                                                    函数描述符
---------------------------------------------------------------------    --------------------------------------------------------------------------------------------------------------------------------------
 double atof(const char \*str)                                              把参数str所指向的字符串转换为一个浮点数
 int atoi(const char \*str)                                                 把参数str所指向的字符串转换为一个整数
 long int atol(const char \*str)
 double strtod(const char \*str, char \**endptr)                      
 long int strtol(const char \*str, char \**endptr, int base)
 unsigned long int strtoul(const char \*str,char \**endpptr,int base)
 void \*calloc(size_t nitems, size_t size)                                  分配所需的内存空间，返回指针
 void free(void \*ptr)                                                      释放calloc, malloc, realloc分配的内存空间
 void \*malloc(size_t size)
 void \*realloc(void \*ptr, size_t size)                                    尝试调整之前malloc或calloc所分配的ptr所指向的内存块的大小
 void abort(void)                                                           使一个异常程序终止
 int atexit(void (\*func)(void))                                            当程序正常终止时，调用指定的函数func
 void exit(int status)                                                      使程序正常终止
 char \*getenv(const char \*name)                                           搜索name所指向的环境变量
 int system(const char \*string)                                            执行string命令
 int abs(int x)                                                             返回x的绝对值
 long int labs(long int x)
 div_t div(int number, int denom)                                           分子除以分母
 ldiv_t ldiv(long int number, long int denom)       
 int rand(void)                                                             返回一个0到RAND_MAX之间的伪随机数
 void srand(unsigned int seed)                                              
 int mblen(const char \*str, size_t n)                                      返回参数str所指向的多字节字符的长度
 size_t mbstowcs(schar_t \*pwcs, const char \*str, size_t n)                把参数str所指向的字符串转换为pwcs所指向的数组
 int mbtowc(wchar_t \*pwc, const char \*str, size_t n)
 size_t wcstombs(char \*str, const wchar_t \*pwcs, size_t n)                将数组pwcs中的字符转换为str字符串
 int wctomb(char \*str, wchar_t wchar)
 void swab(char \*from, char \*to, int n)                                   from和to为需要交换的字符串，n表示要交换的字节数
 void qsort(void \*ditrict, int n, int m, int(\*fc)())                      对无序数列进行快速排序，n表示待排序元素数量，m表示每个排序元素的大小,fc为比较元素大小的函数指针
=====================================================================    ======================================================================================================================================








