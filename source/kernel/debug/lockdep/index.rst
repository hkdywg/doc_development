死锁检测----lockdep
===========================


``lockdep`` 是内核提供的协助发现死锁问题的功能，主要是跟踪每个锁的自身状态和各个锁之间的依赖关系，经过一系列的验证规则来确保锁之间的依赖关系是
正确的。

Lockdep检测的锁包括:spinlock, rwlock, mutex, rwsem的死锁、锁的错误释放，原子操作中的睡眠等错误操作

::

    Kernel hacking  --->
      Lock Debugging (spinlocks, mutexes, etc...)  --->
        [*] Lock debugging: prove locking correctness
        [ ] Lock usage statistics
        -*- RT Mutex debugging, deadlock detection
        -*- Spinlock and rw-lock debugging: basic checks
        -*- Mutex debugging: basic checks
        -*- Wait/wound mutex debugging: Slowpath testing
        -*- RW Semaphore debugging: basic checks
        -*- Lock debugging: detect incorrect freeing of live locks
        [*] Lock dependency engine debugging
        [ ] Sleep inside atomic section checking
        [ ] Locking API boot-time self-tests
        < > torture tests for locking
        < > Wait/wound mutex selftests



配置说明
---------------

::

      CONFIG_DEBUG_KERNEL=y
      CONFIG_LOCK_DEBUGGING_SUPPORT=y
      CONFIG_DEBUG_LOCKDEP=y
      CONFIG_PROVE_LOCKING=y
      CONFIG_DEBUG_SPINLOCK=y                                                                                                                                                                                
      CONFIG_DEBUG_MUTEXES=y
      CONFIG_DEBUG_ATOMIC_SLEEP=y
      CONFIG_LOCK_STAT=y


.. note::
    - CONFIG_DEBUG_KERNEL: KERNEL DEBUG总开关
    - CONFNIG_LOCK_DEBUGGING_SUPPORT: 会对Lockdep的使用过程进行更多的自我检测，增加额外的开销
    - CONFIG_PROVE_LOCKING: 内核再死锁发生前报告死锁详细信息，参见/proc/lockdep_chains
    - CONFIG_LOCK_STAT: 记录锁持有竞争区域的信息，包括等待时间、持有时间等，参见/proc/lock_stat
    - CONFIG_DEBUG_MUTEXES: 检测并报告mutex错误
    - CONFIG_DEBUG_SPINLOCK: 检测并报告spinlock

死锁
--------

死锁是指多个进程因为长时间等待已被其他进程占有的资源而陷入阻塞的一种状态。当等待的资源一直不释放，死锁就会一直持续下去，死锁一旦发生，
程序本身是解决不了的。只能靠外部力量来使程序恢复运行,如重启、看门狗复位等。

Linux提供了检测死锁的机制，主要分为 ``D状态死锁`` 和 ``R状态死锁``

- D状态死锁

进程等待I/O资源无法得到满足，长时间(系统默认配置120s)处于TASK_UNINTERRUPTIBLE睡眠状态，这种状态下进程不响应异步信号(包括kill -9). 
对于这种死锁的检测Linux提供的是hung task机制，触发该问题成因比较复杂多样，如mutex lock, 内存不足等。D状态死锁只是局部多进程间互锁，
一般来说只是hang机，冻屏，但不会影响看门狗等。


- R状态死锁

进程长时间(系统默认配置60s)处于TASK_RUNNING状态垄断CPU而不发生切换，一般情况下只是进程关抢占或关中断后长时间执行任务、
死循环，此时往往会导致多CPU间互锁，整个系统无法正常调度，导致喂狗线程无法执行，最终引起看门狗复位。该问题多为原子操作, spinlock等CPU间
并发操作处理不当造成。

内核R状态死锁检测机制就是 ``lockdep机制`` 

lockdep
-------------

常见的死锁有以下两种:

- 递归死锁: 中断等延迟操作中使用了锁，和外面的锁构成了递归死锁。 

- AB-BA: 多个锁处理不当而引发死锁，多个内核路径上的处理顺序不一致也会导致死锁

当检测到死锁风险时，lockdep会打印以下几种类型的风险提示

- INFO: possible circular locking dependency detected 圆形锁，获取锁的顺序异常(ABBA)

- INFO: %s-safe -> %s-unsafe lock order detected: 获取从safe的锁类到unsafe的锁类操作

- INFO: possible recusive locking detected 重复获取同类锁(AA)

- INFO: inconsistent lock state 锁的状态前后不一致

- INFO: possble irq lock innversion dependency detected 嵌套获取锁的状态前后需要保持一致

- INFO: suspicious RCU usage 可疑的RCU用法

lockdep机制生效时，检测到死锁的打印示例

::

    [   11.841571] Deadlock example: Initializing
    [   11.842570] Thread 1: Trying to lock lock_a...
    [   11.842907] Thread 1: Acquired lock_a
    [   11.845990] Thread 2: Trying to lock lock_b...
    [   11.846217] Thread 2: Acquired lock_b
    [   11.951178] Thread 1: Trying to lock lock_b...
    [   11.954377] Thread 2: Trying to lock lock_a...
    [   11.955362] 
    [   11.955558] ======================================================
    [   11.956057] WARNING: possible circular locking dependency detected
    [   11.956839] 5.4.0 #18 Tainted: G           O     
    [   11.957253] ------------------------------------------------------
    [   11.957810] thread2/178 is trying to acquire lock:
    [   11.958359] ffffde46cc52f110 (lock_a){+.+.}, at: thread2_fn+0x5c/0x88 [simple_lock]
    [   11.959062] 
    [   11.959062] but task is already holding lock:
    [   11.959202] ffffde46cc52f070 (lock_b){+.+.}, at: thread2_fn+0x2c/0x88 [simple_lock]
    [   11.959364] 
    [   11.959364] which lock already depends on the new lock.
    [   11.959364] 
    [   11.959519] 
    [   11.959519] the existing dependency chain (in reverse order) is:
    [   11.959676] 
    [   11.959676] -> #1 (lock_b){+.+.}:
    [   11.959838]        __mutex_lock+0xa4/0x970
    [   11.959936]        mutex_lock_nested+0x1c/0x28
    [   11.960027]        thread1_fn+0x5c/0xb8 [simple_lock]
    [   11.960138]        kthread+0x134/0x138
    [   11.960217]        ret_from_fork+0x10/0x18
    [   11.960331] 
    [   11.960331] -> #0 (lock_a){+.+.}:
    [   11.960436]        __lock_acquire+0xdc0/0x11c0
    [   11.960528]        lock_acquire+0xf8/0x280
    [   11.960614]        __mutex_lock+0xa4/0x970
    [   11.960695]        mutex_lock_nested+0x1c/0x28
    [   11.960785]        thread2_fn+0x5c/0x88 [simple_lock]
    [   11.960884]        kthread+0x134/0x138
    [   11.960956]        ret_from_fork+0x10/0x18
    [   11.961049] 
    [   11.961049] other info that might help us debug this:
    [   11.961049] 
    [   11.961237]  Possible unsafe locking scenario:
    [   11.961237] 
    [   11.961362]        CPU0                    CPU1
    [   11.961460]        ----                    ----
    [   11.961561]   lock(lock_b);
    [   11.961644]                                lock(lock_a);
    [   11.961766]                                lock(lock_b);
    [   11.961878]   lock(lock_a);
    [   11.961951] 
    [   11.961951]  *** DEADLOCK ***
    [   11.961951] 
    [   11.962087] 1 lock held by thread2/178:
    [   11.962194]  #0: ffffde46cc52f070 (lock_b){+.+.}, at: thread2_fn+0x2c/0x88 [simple_lock]
    [   11.962379] 
    [   11.962379] stack backtrace:
    [   11.962585] CPU: 0 PID: 178 Comm: thread2 Tainted: G           O      5.4.0 #18
    [   11.962732] Hardware name: linux,dummy-virt (DT)
    [   11.962915] Call trace:
    [   11.962978]  dump_backtrace+0x0/0x158
    [   11.963062]  show_stack+0x14/0x20
    [   11.963132]  dump_stack+0xe8/0x154
    [   11.963207]  print_circular_bug.isra.41+0x1b8/0x210
    [   11.963299]  check_noncircular+0x178/0x1e0
    [   11.963382]  __lock_acquire+0xdc0/0x11c0
    [   11.963463]  lock_acquire+0xf8/0x280
    [   11.963539]  __mutex_lock+0xa4/0x970
    [   11.963618]  mutex_lock_nested+0x1c/0x28
    [   11.963692]  thread2_fn+0x5c/0x88 [simple_lock]
    [   11.963777]  kthread+0x134/0x138
    [   11.963846]  ret_from_fork+0x10/0x18


实现原理
-----------

::

    #ifdef CONFIG_DEBUG_SPINLOCK
      extern void __raw_spin_lock_init(raw_spinlock_t *lock, const char *name,
                       struct lock_class_key *key, short inner);

    # define raw_spin_lock_init(lock)                   \
    do {                                    \
        static struct lock_class_key __key;             \
                                        \
        __raw_spin_lock_init((lock), #lock, &__key, LD_WAIT_SPIN);  \
    } while (0)                                                                                                                                                                                                

    #else
    # define raw_spin_lock_init(lock)               \
        do { *(lock) = __RAW_SPIN_LOCK_UNLOCKED(lock); } while (0)
    #endif


对于每个锁的初始化，这段代码创建了一个静态变量(__key)，并使用它的地址作为识别锁的类型。因此，系统中每个锁(包括rwlock和mutex)
都会被分配一个特定的key值，并且都是静态申明的，同一类的锁会对应同一个key值。

Lockdep为每个锁类维护了befor和after两个链表来记录锁的依赖关系，从而能够检测死锁、潜在的锁顺序问题、锁的获取和释放状态

- befor: 表示当前锁依赖其他锁的关系，也就是说某个锁必须在其他锁之前被获取。例如Lock1必须在Lock2之前你获取，那么Lock2会出现在Lock1的befor链表中

- after: 表示其他锁依赖当前锁的关系，也就是说某个锁必须在当前锁获取之后才能获取

**Lockdep逻辑**

当获取L时，检查after链表中的锁类是否已经被获取，如果存在则报重复上锁。











