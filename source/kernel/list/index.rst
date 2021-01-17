linux 通用双向循环链表
======================

在linux内核中，有一种通用的的双向循环链表，构成了各种队列的基础。链表的结构定义和相关函数均在 ``include/linux/list.h`` 中。

include/linux/types.h 中对 ``list_head`` 做出了定义

::
    
    struct list_head {
        struct list_head *next, *prev;
    };

这是链表的元素结构，因为时循环链表，表头和表中节点都是同样的结构。有prev和next两个指针，分别指向前一节点和后一节点。

::

    #define LIST_HEAD_INIT(name)    {&(name), &(name)}

    #define LIST_HEAD(name) \
        struct list_head name = LIST_HEAD_INIT(name)

    static inline void INIT_LIST_HEAD(struct list_head *list)
    {
        list->prev = list;
        list->next = list;
    }

初始化时，链表头的prev和next都是指向自身的。

::

    static inline void __list_add(struct list_head *new, struct list_head *prev, struct list_head *next)
    {
        new->next = next;
        next->prev = new;
        prev->next = new;
        new->prev = prev;
    
    }

    static inline void list_add(struct list_head *new, struct list_head *head)
    {
        __list_add(new, head, head->next);
    }

    static inline void list_add_tail(struct list_head *new, struct list_head *head)
    {
        __list_add(new, head-prev, head);
    }

双向循环链表的实现，很少有例外的情况，基本都可以用公共的方式来处理。

链表API实现时大致都是分为两层：一层是外部的,如 ``list_add`` ``list_add_tail`` ,用来消除一些例外情况，调用内部实现；
一层是内部的，函数名前会加双下划线，如 ``__list_add`` ,往往都是几个操作公共的部分，或者排除例外后的实现。

::
    
    static inline void __list_del(struct list_head *prev, struct list_head *next)
    {
        prev->next = next;
        next->prev = prev;
    }

    static inline void list_del(struct list_head *head)
    {
        __list_del(head->prev, head->next);
    }

    static inline void list_del_init(struct list_head *entry)
    {
        __list_del(entry->prev, entry->next);
        LIST_INIT_HEAD(entry);
    }

list_del是将链表中的节点删除，list_del_init则是将链表中的节点删除后再次把节点指针初始化。

::

    static inline void list_replace(struct list_head *old, struct list_head *new)
    {
        new->next = old->next;
        new->next->prev = new;
        new->prev = old->prev;
        new->prev->next = new;
    }
    

    static inline void list_replace_init(struct list_head *old, struct list_head *new)
    {
        list_replace(old, new);
        INIT_LIST_HEAD(old);
    }

list_replace 将链表中的一个节点old，替换为另一个节点new。


::

    static inline void list_move(struct list_head *list, struct list_head *head)
    {
        __list_del(list->prev, list->next);
        list_add(list, head);
    }

    static inline void list_move_tail(struct list_head *list, struct list_head *head)
    {
       __list_del(list->prev, list->next);
       list_add_tail(list, head);
    }

list_move 的作用是将list节点从原链表中删除，并加入新的链表head中。

::

    static inline int list_is_last(struct list_head *list, struct list_head *head)
    {
        return (list->next == head);
    }

list_is_last 判断list是否处于head链表的尾部。

::

    static inline int list_empty(struct list_head *head)
    {
        rerurn (head->next == head);
    }

    static inline int list_empty_careful(const struct list_head *head)
    {
        struct list_head *next = head->next;
        return (next == head) && (next == head->prev);
    }

list_empty 判断head链表是否为空

::

    static inline int list_is_singular(const list_head *head)
    {
        return !list_empty(head) && (head->next == head->prev);
    }

list_is_singular 判断head是否只有一个节点，即除链表头head外是否只有一个节点。


::

    static inline void __list_cut_position(struct list_head *list, struct list_head *head, struct list_head *entry)
    {
        entry->next->prev = head->prev;
        head->prev->next = entry->next;
        list->next = head;
        head->prev = list;
        entry->next = list;
        list->prev = entry;
    }

    static line void lis_cut_position(struct list_head *list, struct list_head *head, struct list_head entry)
    {
        if(list_entry(head))
            return;
        if(list_is_singular(head) && (list->next != entry && head != entry))
            return;
        if(entry == head)
            INIT_LIST_HEAD(list);
        else
            __list_cut_position(list, head, entry);
    }

list_cut_position 用于把head链表分为两部分，从head->next 一直到entry被从head链表中删除，加入新的链表list。
新的链表应该是空的，或者原来的节点可以被忽略掉。

::
        
    static inline void __list_splice(struct list_head *list, struct list_head *prev, struct list_head *next)
    {
        struct list_head *first = list->next;
        struct list_head *last = list->prev;

        prev->next = first;
        first->prev = prev;

        last->next = next;
        next->prev = last;
    }

    static inline void list_splice(struct list_head *list, struct list_head *head)
    {
        if(!list_empty(list))
            __list_splice(list, head, head->next);
    }

    static inline void list_splice_tail(struct list_head *list, struct list_head *head)
    {
        if(!list_emptu=y(list))
            __list_splice(list, head->prev, head)；
    }

list_splict 的功能和list_cut_posiotion相反，它合并两个链表。list_splice把list链表中的节点加入到head链表中。

list_splict是把原来list链表中的节点全部插入到head链表的头部，list_splice_tail则是把原来list链表中的节点全部加到head链表的尾部。

::

    #define list_entry(ptr, type, member) \
        container_of(ptr, type, member)

list_entry 主要用于从list节点查找其内嵌在的结构。比如定义了一个结构struct A{struct list_head list;},如果知道结构中链表的地址ptrlist，
就可以从ptrlist进而获取整个结构的指针，struct A \*Ptr = list_entry(ptrlist, struct A, list);

这种地址翻译的技巧是linux的拿手好戏，container_of随处可见，只是链表节点多被封装在更复杂的结构中，使用专门的list_entry定义也是对了使用方便


::

    #define __list_for_each(pos,head) \
        for(pos = (head)->next; pos != head; pos = pos->next)

list_for_each 遍历链表中的每一个节点。

::

    #define list_for_each_prev(pos,head) \
        for(pos = (head)->prev; pos != head; pos = pos->prev)

list_for_each_prev 遍历链表中的每一个节点，不同的是它是逆序的.

::

    #define list_for_each_safe(pos, n, head) \
        for(pos = (head)->next, n = pos->next;pos != head; pos = n,n = pos->next)

list_for_each_safe 也是链表顺序遍历，只是它更加安全，即使在遍历过程中喔咕，当前节点从链表中删除，也不会影响链表的遍历。参数中需要加一个暂存的链表节点指针n


::

    #define list_for_each_entry(pos, head, member) \
        for(pos = list_entry(head->next, typeof(*pos), member);
            &pos->member != head; \
            pos = list_entry(pos->memer.prev, typeof(*pos), member)
            )


list_for_each_entry 不是遍历链表节点，而是遍历链表节点所嵌套进的结list_for_each_entry 不是遍历链表节点，而是遍历链表节点所嵌套进的结构.


