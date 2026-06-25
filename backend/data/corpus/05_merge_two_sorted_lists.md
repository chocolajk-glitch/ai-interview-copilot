# 5. Merge Two Sorted Lists（合并两个有序链表）

## 题目描述

将两个升序链表合并为一个新的**升序**链表并返回。新链表是通过拼接给定的两个链表的所有节点组成的。

## 示例
输入：l1 = [1,2,4], l2 = [1,3,4] 输出：[1,1,2,3,4,4]
## 解题思路

**双指针 + 哨兵节点**：
- 哨兵节点 `dummy` 简化头节点处理
- `cur` 指针指向当前合并位置
- 比较 `l1.val` 和 `l2.val`，小的接到 `cur.next`，对应链表前移
- 任一链表为空，把另一个直接接上
- 返回 `dummy.next`（真正的头节点）

## 代码实现

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def merge_two_lists(l1, l2):
    dummy = ListNode(-1)
    cur = dummy
    while l1 and l2:
        if l1.val <= l2.val:
            cur.next = l1
            l1 = l1.next
        else:
            cur.next = l2
            l2 = l2.next
        cur = cur.next
    cur.next = l1 or l2
    return dummy.next
```

## 复杂度分析

- **时间复杂度**：O(n + m)，遍历两个链表各一次
- **空间复杂度**：O(1)，只用了哨兵 + 指针

## 关键点

- **哨兵节点 dummy**：避免单独处理"第一个节点"的特殊情况（head 可能是 l1 或 l2）
- **`cur.next = l1 or l2`**：Python 短路求值巧妙处理"剩余链表"
- 进阶：合并 K 个升序链表（LeetCode 23）—— 用分治或优先队列