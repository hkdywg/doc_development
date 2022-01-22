数组操作
=========


数组中重复的数字
-------------------

题目描述
^^^^^^^^^

找出数组中重复的数字。

在一个长度为 n 的数组 nums 里的所有数字都在 0～n-1 的范围内。数组中某些数字是重复的，但不知道有几个数字重复了，也不知道每个数字重复了几次。

请找出数组中任意一个重复的数字。

示例1:

::

    输入：
    [2, 3, 1, 0, 2, 5, 3]
    输出：2 或 3 


题目解析
^^^^^^^^^^

首先可能想到的是暴力算法，两个for循环，一一对比。缺点很明显:用时过多。或者再进一步可以先排序然后一次for循环，但依然用时较长。

注意题目描述：一个长度为 n 的数组 nums 里的所有数字都在 0～n-1 的 范围内，这个 范围 恰好与数组的下标可以一一对应。

我们考虑如果每个数字都只出现一次，那么此时是最完美的，每一个下标i对应元素numbers[i]，也就是说我们对于数组中的每个元素numbers[i]都把它放在自己该放的位置numbers[numbers[i]]上，
如果我们发现有两个元素想往同一个位置上放的时候，说明此元素必然重复

即如下过程

1) 如果numbers[i] == i，那么我们认为numbers[i]这个元素在自己的位置上
2) 否则的话，numbers[i]这个元素就应该在numbers[numbers[i]]这个位置上，于是交换numbers[i]和numbers[numbers[i]]
3) 重复操作1 2,直到numbers[i]==i


代码
^^^^^^

::

    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    int FindRepeatNumber(int *nums, int numSize)
    {
        int temp, i;
        for(i = 0; i < numSize; i++)
        {
            while(nums[i] != i)
            {
                if(nums[i] == nums[nums[i]])
                    return nums[i];
                temp = nums[i];
                nums[i] = nums[temp];
                nums[temp] = temp;
            }
        }
        return -1;
    }

    int main( )
    {
        int a[] ={6, 4, 1, 0, 6, 5, 3};
        printf("%d\n",FindRepeatNumber(a, sizeof(a)));
        return 0;
    }


二维数组中的查找
------------------

题目描述
^^^^^^^^^

在一个 n * m 的二维数组中，每一行都按照从左到右递增的顺序排序，每一列都按照从上到下递增的顺序排序。请完成一个函数，输入这样的一个二维数组和一个整数，判断数组中是否含有该整数。

示例

::

	[
	  [1,   4,  7, 11, 15],
	  [2,   5,  8, 12, 19],
	  [3,   6,  9, 16, 22],
	  [10, 13, 14, 17, 24],
	  [18, 21, 23, 26, 30]
	]


给定 target = 5，返回 true。

给定 target = 20，返回 false。


题目解析
^^^^^^^^^^

仔细观察矩阵，可以发现：左下角元素为所在列最大元素，所在行最小元素

如果 左下角元素 大于了目标值，则目标值一定在该行的上方， 左下角元素 所在行可以消去。

如果 左下角元素 小于了目标值，则目标值一定在该列的右方， 左下角元素 所在列可以消去

具体操作为从矩阵左下角元素开始遍历，并与目标对比。

1) 当matrix[i][j] > target时，行索引向上移动一格(i--)
2) 当matrix[i][j] < target时，列索引向右移动一格(j++)
3) 当matrix[i][j] == target 时： 返回 true，越界则返回false

代码
^^^^^^

::

    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    #define MATRIX_ROW  (5)
    #define MATRIX_LINE (5)

    unsigned char matrix[5][5] = {
        {1,   4,  7, 11, 15},
        {2,   5,  8, 12, 19},
        {3,   6,  9, 16, 22},
        {10, 13, 14, 17, 24},
        {18, 21, 23, 26, 30}
    };

    int FindTargetNumber(unsigned char *nums, int target)
    {
        int ret = -1;
        int i = MATRIX_ROW - 1;
        int j = 0;
        unsigned char tmp = 0;

        while(i >= 0)
        {
            tmp = *(nums + (MATRIX_ROW * i) + j);   //等价于matrix[i][j]
            if(tmp > target)
            {
                i--;
                continue;
            }
            if(tmp < target)
            {
                for(j = 1; j < MATRIX_LINE; j++)
                {
                    tmp = *(nums + (MATRIX_ROW * i) + j);   
                    if(tmp == target)
                        return 1;
                    if(tmp > target)
                        break;
                }
                i--;
            }
            j = 0;
        }
        return -1;
    }

    int main( )
    {
        int ret = 0;
        ret = FindTargetNumber(matrix, 20);
        if(ret == 1)
            printf("target found\n");
        else
            printf("target not found\n");
        return 0;
    }


从尾到头打印链表
-----------------

题目描述
^^^^^^^^^

输入一个链表的头节点，从尾到头反过来返回每个节点的值（用数组返回）。

示例

::

    输入：head = [1,3,2]
    输出：[2,3,1]

解题思路
^^^^^^^^^^

方法1: 先求链表长度，然后再将链表中元素逆序存入数组中

方法2: 先反转链表并求其长度，在将反转后的链表数据拷贝至数组中



代码
^^^^^^

::


    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    #define USING_METHOD_1
    //#define USING_METHOD_2


    struct ListNode {
        int val;
        struct ListNode *next;
    };

    #ifdef USING_METHOD_1
    int *reversePrint(struct ListNode *head, int *returnSize)
    {
        int listlen= 0;
        struct ListNode *cur = head;
        
        while(cur)
        {
            listlen++;
            cur = cur->next;
        }

        int *arr = (int *)malloc(sizeof(int) * listlen);
        *returnSize = listlen;
        cur = head;

        while(cur)
        {
            *(arr + listlen - 1) = cur->val;
            cur = cur->next;
            listlen--;
        }
        return arr;
    }
    #else
    int *reversePrint(struct ListNode *head, int *returnSize)
    {
        int listlen = 0;
        struct ListNode *cur = head;
        struct ListNode *next = NULL;
        struct ListNode *tail = NULL;

        while(cur)
        {
            
            next = cur->next;
            cur->next = tail;
            tail = cur;

            cur = next;
            listlen++;
        }   //反转链表并求其长度
        int *arr = (int *)malloc(sizeof(int)*listlen);
        *returnSize = listlen;
        cur = tail;
        for(int i = 0; i < listlen; i++)
        {
            arr[i] = cur->val;
            cur = cur->next;
        }
        return arr;
    }
    #endif

    void AddListNode(struct ListNode *head, struct ListNode *node)
    {
        struct ListNode * cur = head;
        while(cur->next)
        {
            cur = cur->next;
        }
        cur->next = node;
        return;
    }


    int main()
    {
        int listlen = 0;
        int *arr;
        static struct ListNode listhead = {.val = 20, .next = NULL};
        struct ListNode node_1 = {.val = 30, .next = NULL};
        struct ListNode node_2 = {.val = 40, .next = NULL};
        struct ListNode node_3 = {.val = 50, .next = NULL};
        struct ListNode node_4 = {.val = 60, .next = NULL};
        struct ListNode node_5 = {.val = 70, .next = NULL};

        AddListNode(&listhead, &node_1);
        AddListNode(&listhead, &node_2);
        AddListNode(&listhead, &node_3);
        AddListNode(&listhead, &node_4);
        AddListNode(&listhead, &node_5);

        arr = reversePrint(&listhead, &listlen);
        for(int i = 0; i < listlen; i++)
            printf("%d\n", arr[i]);

        return 0;
    }


调整数组顺序使奇数位于偶数前面
--------------------------------

题目描述
^^^^^^^^^

输入一个整数数组，实现一个函数来调整该数组中数字的顺序，使得所有奇数位于数组的前半部分，所有偶数位于数组的后半部分。

示例

::

    输入：nums = [1,2,3,4]
    输出：[1,3,2,4] 
    注：[3,1,2,4] 也是正确的答案之一。


解题思路
^^^^^^^^^

1) 设置两个指针left和right，分别指向数组的头和尾
2) left向左移动，right向右移动
3) left为偶数，right为奇数时，调换位置，然后重复上面步骤。当left不小于right时循环结束



代码
^^^^^

::

    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    int main()
    {
        unsigned char nums[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 8, 4, 2};
        unsigned char *left, *right;
        unsigned char tmp;

        left = nums;
        right = nums + sizeof(nums) - 1;

        while(left < right)
        {
            while(*left % 2 != 0)
                left++;
            while(*right % 2 == 0)
                right--;
            tmp = *left;
            *left = *right;
            *right = tmp;
        }
        for(int i = 0; i < sizeof(nums); i++)
            printf("%d ,", nums[i]);
        return 0;
    }


旋转数组的最小数字
-------------------

题目描述
^^^^^^^^^

把一个数组最开始的若干个元素搬到数组的末尾，我们称之为数组的旋转。输入一个递增排序的数组的一个旋转，输出旋转数组的最小元素。例如，数组[3,4,5,1,2] 为 [1,2,3,4,5] 的一个旋转，该数组的最小值为 1。

示例

::

    输入：[2,2,2,0,1]
    输出：0

示例

::

    输入：[3,4,5,1,2]
    输出：1


题目解析
^^^^^^^^^

首先，我们明确知道这个数组是被旋转了，也就意味着，这个数组实际上可以被划分为两个部分。

1) 左边是一个递增的数组
2) 右边是一个递增的数组
3) 左右两部分相交的位置出现了一个异常点，小的数字在大的数字后面


代码
^^^^^

::


    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    int main()
    {
        unsigned char nums[] = { 4, 5, 6, 7, 8, 9, 10,  0, 1,  2, 3};
        unsigned char left, right;
        unsigned char mid;

        left = 0;
        right = sizeof(nums) - 1;

        while(left < right)
        {
            mid = (left + right) / 2;
            if(nums[right] < nums[mid])
            {
                left = mid;
            }
            else if(nums[left] > nums[mid])
            {
                right = mid;
            }
            if((right - left == 2) || (right - left == 1))
                break;
        }
        for(int i = left; i < right; i++)
        {
            if(nums[i] > nums[i+1])
            {
                printf("%d", nums[i+1]);
                break;
            }
        }
        return 0;
    }


连续子数组的最大和
--------------------

题目描述
^^^^^^^^^^

输入一个整型数组，数组中的一个或连续多个整数组成一个子数组。求所有子数组的和的最大值。

要求时间复杂度为O(n)。

示例

::

    输入: nums = [-2,1,-3,4,-1,2,1,-5,4]
    输出: 6
    解释: 连续子数组 [4,-1,2,1] 的和最大，为 6。


题目解析
^^^^^^^^^^




代码
^^^^^

::

    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>

    #define ARRAY_SIZE 12

    int main()
    {
        int nums[] = { 1, 2, -5, 4, 1, -2, 4, 6, -4, 12, -9, 12, 7, 8, -3, 2};
        int *dst;
        unsigned int start_pos = 0, end_pos = 0;
        int max_num = 0, num_len = sizeof(nums)/sizeof(int);

        dst = (int *)malloc(sizeof(nums));

        dst[0] = nums[0];
        
        printf("num_len = %d\n", num_len);

        for(int i = 1; i < num_len; i++)
        {
            dst[i] = dst[i-1] + nums[i]; 
            if(dst[i] < 0)
            {
                printf("dst[%d] = %d\n", i, dst[i]);
                i=i+1;
                dst[i] = nums[i];
                start_pos = i;
                end_pos = i;
            }
            if(dst[i] > max_num)
            {
                end_pos = i;
                max_num = dst[i];
            }

            printf("src = %d, dst[%d] = %d\n",nums[i], i, dst[i]);
        }
        printf("start_pos = %d, end_pos = %d\n", start_pos, end_pos);
        free(dst);
        return 0;
    }
    

把数组排成最小的数
--------------------

题目描述
^^^^^^^^^

输入一个非负整数数组，把数组里所有数字拼接起来排成一个数，打印能拼接出的所有数字中最小的一个。

示例 1:

::

    输入: [10,2]
    输出: "102"

示例2

::

    输入: [3,30,34,5,9]
    输出: "3033459"

说明

说明:

输出结果可能非常大，所以你需要返回一个字符串而不是整数

拼接起来的数字可能会有前导 0，最后结果不需要去掉前导 0

题目解析
^^^^^^^^


