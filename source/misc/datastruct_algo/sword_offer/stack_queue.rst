栈和队列操作
===============


用两个栈实现队列
-------------------

题目描述
^^^^^^^^^^

用两个栈来实现一个队列，完成队列的Push和Pop操作。 队列中的元素为int类型。


解题思路
^^^^^^^^^

一个队列包含了两个栈stack1和stack2，此题要求我们操作这两个先进后出的栈实现一个先进先出的队列。

入队: 将元素进栈stack1

出队: 判断 stack2是否为空，如果为空，则将栈stack1中的所有元素pop，并push进栈stack2，栈stack2出栈。如果不为空，直接出栈


代码
^^^^^^

::


    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    #define STACK_INIT_SIZE     (20)

    struct stack
    {
        int *data;
        int *top;
        int stacksize;
    };

    struct queue
    {
        struct stack *stack1;
        struct stack *stack2;
    };

    struct stack* init_stack()
    {
        struct stack *s;
        s = (struct stack*)malloc(sizeof(struct stack));
        if(s == NULL)
            return NULL;
        s->data = (int *)malloc(STACK_INIT_SIZE);
        s->top = s->data;
        s->stacksize = STACK_INIT_SIZE;
        return s;
    }

    int stack_destroy(struct stack* s)
    {
        if(s != NULL)
        {
            free(s->data);
            s->data = NULL;
            s->top = NULL;
            free(s);
        }
        return 0;
    }


    int push_stack(struct stack *s, int num)
    {
        if((s->top - s->data) >= s->stacksize)
        {
            s->data = (int *)realloc(s->data, s->stacksize + STACK_INIT_SIZE);
            printf("realloc...\n");
        }
        if(s->data == NULL)
            return -1;
        *(s->top++) = num;
    }

    int pop_stack(struct stack *s)
    {
        if(s->data == s->top)
            return -1;
        return *(--s->top);
    }

    int isempty_stack(struct stack *s)
    {
        return(s->top == s->data);
    }


    struct queue* queue_create()
    {
        struct queue *q = (struct queue*)malloc(sizeof(struct queue));
        if(q == NULL)
            return NULL;
        q->stack1 = init_stack();
        q->stack2 = init_stack();
        return q;
    }

    int queue_destroy(struct queue* q)
    {
        if(q != NULL)
        {
            stack_destroy(q->stack1);
            stack_destroy(q->stack2);
        }
        return 0;
    }

    int push_queue(struct queue *q, int num)
    {
        if(q->stack1 != NULL)
        {
            push_stack(q->stack1, num);
            return 0;
        }
    }

    int pop_queue(struct queue *q)
    {
        int ret;
        if(isempty_stack(q->stack2))
        {
            while(!isempty_stack(q->stack1))
            {
                push_stack(q->stack2, pop_stack(q->stack1));
            }
            ret = pop_stack(q->stack2);
        }
        else
        {
            ret = pop_stack(q->stack2);
        }
        printf("pop value = %d\n", ret);
        return ret;
    }

    int main() 
    {

        struct queue* test_queue = queue_create();
        if(test_queue != NULL)
        {
            push_queue(test_queue, 1);
            push_queue(test_queue, 2);
            push_queue(test_queue, 3);
            push_queue(test_queue, 4);
            push_queue(test_queue, 5);
            pop_queue(test_queue);
            pop_queue(test_queue);
            pop_queue(test_queue);
            pop_queue(test_queue);
            pop_queue(test_queue);
        }

        return 0;
    }


包含min函数的栈
-----------------

题目描述
^^^^^^^^^

定义栈的数据结构，在该类型中实现一个能够得到栈的最小元素的min函数，在该栈中，调用min、push以及pop的时间复杂度都是O(1)


题目解析
^^^^^^^^^^^

由于需要在常数时间内找到最小元素，那么说明不能使用遍历，因为遍历是O(n)级别的时间，那么只能使用辅助空间进行存储，这是一种空间换时间的思想。

需要设置两个栈: 普通栈和辅助栈

- push操作

普通栈: 直接添加push进来的值

辅助栈: 每次push一个新元素的时候，将普通栈中的最小元素push进辅助栈中

- pop操作

普通栈: 直接pop普通栈中的栈顶元素

辅助栈: 判断普通栈中移除的元素是否与辅助栈中的元素相同，如果相同则将辅助栈中的栈顶元素移除，否则不操作。这样做的目的是为了让辅助栈中的栈顶元素始终是普通栈中的最小值

- getmin操作

普通栈: 不执行操作

辅助栈: 返回辅助栈的栈顶元素


代码
^^^^^^

::

    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    #define STACK_SIZE      (1024)

    struct minstack
    {
        int *top;
        int *min_top;
        int *stack;
        int *min_stack;
    };

    struct minstack* minstack_create()
    {
        struct minstack* s = (struct minstack*)malloc(sizeof(struct minstack));

        s->stack = (int *)malloc(sizeof(int) * STACK_SIZE);
        s->min_stack = (int *)malloc(sizeof(int) * STACK_SIZE);
        s->top = s->stack;
        s->min_top = s->min_stack;
        return s;
    }


    void minstack_push(struct minstack* s, int num)
    {
        *(s->top) = num;
        if(s->min_top == s->min_stack)
        {
            *(++s->min_top) = num;
        }
        else if(*(s->min_top) >= num)
        {
            *(++s->min_top) = num;
        }
    }

    void minstack_pop(struct minstack* s)
    {
        if(*(s->top) == *(s->min_stack))
        {
            s->top--;
            s->min_top--;
        }
        else
        {
            s->top--;
        }
    }


    int minstack_top(struct minstack* s)
    {
        return *(s->top);
    }

    int minstack_min(struct minstack* s)
    {
        return *(s->min_top);
    }

    int main()
    {
        struct minstack *test_stack = minstack_create();
        minstack_push(test_stack, 1);
        minstack_push(test_stack, 10);
        minstack_push(test_stack, -13);
        minstack_push(test_stack, 12);
        minstack_push(test_stack, 100);
        minstack_push(test_stack, -3);
        minstack_push(test_stack, 8);

        int min = minstack_min(test_stack);
        printf("minstack number is %d\n", min);

        return 0;
    }


队列的最大值
---------------

题目描述
^^^^^^^^^^

定义一个队列并实现函数max_value得到队列里最大值，要求函数max_value, push_back, pop_front的均摊时间复杂度都是O(1) 

若队列为空，pop_front和max_value需要返回-1


题目解析
^^^^^^^^^^

此题采用链表进行操作



代码
^^^^^^

::

    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    struct maxqueue
    {
        int value;
        struct maxqueue *next;
    };

    struct maxqueue_head
    {
        struct maxqueue* front;
        struct maxqueue* rear;
    };


    struct maxqueue_head* maxqueuehead_create()
    {
        struct maxqueue_head* h = (struct head*)malloc(sizeof(struct maxqueue_head));
        h->front = h->rear = NULL;
        return h;
    }

    int maxqueue_maxvalue(struct maxqueue_head* h)
    {
        if(h->front ==  NULL)
            return -1;
        struct maxqueue* q = h->front;
        int maxvalue = q->value;
        while(q)
        {
            if(q->value > maxvalue)
                maxvalue = q->value;
            q = q->next;
        }
        return maxvalue;
    }


    void maxqueue_pushback(struct maxqueue_head* h, int value)
    {
        struct maxqueue *new = (struct maxqueue*)malloc(sizeof(struct maxqueue));
        new->value = value;
        new->next = NULL;

        if(h->front == NULL)
        {
            h->front = new;
            h->rear = new;
        }
        else
        {
            h->rear->next = new;
            h->rear = new;
        }
    }

    int maxqueue_popfront(struct maxqueue_head* h)
    {
        if(h->front == NULL)
            return -1;

        struct maxqueue* del = h->front;
        int tmp = del->value;
        h->front = del->next;
        del->next = NULL;
        return tmp;
    }

    int maxqueue_value(struct maxqueue* q)
    {

    }

    int main()
    {

        struct maxqueue_head* head = maxqueuehead_create();
        maxqueue_pushback(head, 14);
        maxqueue_pushback(head, 350);
        maxqueue_pushback(head, 89);
        maxqueue_pushback(head, 2);
        maxqueue_pushback(head, 66);

        maxqueue_popfront(head);
        maxqueue_popfront(head);

        int maxvalue = maxqueue_maxvalue(head);

        printf("maxvalue = %d\n", maxvalue);
        return 0;
    }


滑动窗口的最大值
------------------

题目描述
^^^^^^^^^

给定一个数组和一个滑动窗口的大小，找出所有滑动窗口里数值的最大值。

例

::

    如果输入数组{2,3,4,2,6,2,5,1}及滑动窗口的大小3，那么一共存在6个滑动窗口，他们的最大值分别为{4,4,6,6,6,5}； 
    针对数组{2,3,4,2,6,2,5,1}的滑动窗口有以下6个： 
    {[2,3,4],2,6,2,5,1}， {2,[3,4,2],6,2,5,1}， {2,3,[4,2,6],2,5,1}， {2,3,4,[2,6,2],5,1}， {2,3,4,2,[6,2,5],1}， {2,3,4,2,6,[2,5,1]}。



题目解析
^^^^^^^^^^^

可采用双指针解法


代码
^^^^^




















