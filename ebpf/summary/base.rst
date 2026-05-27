eBPF函数定义展开过程
============================

以下函数为eBPF函数的一个简单示例, 后面会以这个函数为例进行 ``BPF_PROG`` 宏展开分析


.. code-block:: c

    SEC("fentry/trace_unlinkat")
    int BPF_PROG(trace_unlinkat, int dfd, struct filename *name)
    {
        pid_t pid;

        pid = bpf_get_current_pid_tgid() >> 32;
        bpf_printk("fentry: pid = %d, filename = %s\n", pid, name->name);
        return 0;
    }

``BPF_PROG`` 作为一个宏用于修饰ePBF函数，定义在 libbpf/src/bpf_tracing.h 中

.. code-block:: c

	#define BPF_PROG(name, args...)                         \
	name(unsigned long long *ctx);                          \
	static __always_inline typeof(name(0))                      \
	____##name(unsigned long long *ctx, ##args);                    \
	typeof(name(0)) name(unsigned long long *ctx)                   \
	{                                       \
		_Pragma("GCC diagnostic push")                      \
		_Pragma("GCC diagnostic ignored \"-Wint-conversion\"")          \
		return ____##name(___bpf_ctx_cast(args));               \
		_Pragma("GCC diagnostic pop")                       \
	}                                       \
	static __always_inline typeof(name(0))                      \
	____##name(unsigned long long *ctx, ##args)


逐行展开


- 前置声明

::

    // name = trace_unlinkat                                                                                                      
    trace_unlinkat(unsigned long long *ctx);


- 内联函数申明

::

     // ____##name ----> ____trace_unlinkat                                                                                            
     // ##args  ----> int dfd, struct filename *name                                                                                    
     static __always_inline typeof(trace_unlinkat(0))                                                                              
     ____trace_unlinkat(unsigned long long *ctx, int dfd, struct filename *name);  


- 包装函数定义

::

     typeof(trace_unlinkat(0)) trace_unlinkat(unsigned long long *ctx)                                                             
     {                                                                                                                             
         _Pragma("GCC diagnostic push")                                                                                            
         _Pragma("GCC diagnostic ignored \"-Wint-conversion\"")                                                                    
         // ___bpf_ctx_cast(args)  ctx, ctx[0], ctx[1]                                                                            
         return ____trace_unlinkat(ctx, ctx[0], ctx[1]);                                                                           
         _Pragma("GCC diagnostic pop")                                                                                             
     }      

- 实际实现函数定义

::

	tatic __always_inline typeof(trace_unlinkat(0))                                                                              
		 ____trace_unlinkat(unsigned long long *ctx, int dfd, struct filename *name)


**完整展开后**

::

     // ========== 完整展开后 ==========                                                             
                                                                                                     
     // 1. 前置声明                                                                                   
     int trace_unlinkat(unsigned long long *ctx);                                                     
                                                                                                      
     // 2. 内联函数前置声明                                                                           
     static __always_inline int ____trace_unlinkat(unsigned long long *ctx, int dfd,                  
     struct filename *name);                                                                          
                                                                                                      
     // 3. 包装函数（入口点，SEC 段）                                                                 
     int trace_unlinkat(unsigned long long *ctx)                                                      
     {                                                                                                
         #pragma GCC diagnostic push                                                                  
         #pragma GCC diagnostic ignored "-Wint-conversion"                                            
         return ____trace_unlinkat(ctx, ctx[0], ctx[1]);                                                                           
         #pragma GCC diagnostic pop                                                                                                
     }                                                                                                                             
                                                                                                                                   
     // 4. 实际实现函数（用户代码写在这里）                                                                                        
     static __always_inline int ____trace_unlinkat(unsigned long long *ctx, int dfd,                                               
     struct filename *name)                                                                                                        
     {                                                                                                                             
         // ========== 用户代码体 ==========                                                                                       
         bpf_printk("dfd=%d", dfd);                                                                                                
         return 0;                                                                                                                 
     }     


