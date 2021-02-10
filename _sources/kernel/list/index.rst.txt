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

list_cut_position 用于把head链表分为两部分，从head->next 一直到entry被从head链表中删除，加入新的链表list。
新的链表应该是空的，或者原来的节点可以被忽略掉。
