# 2. Reverse Linked List（反转链表）

## 题目描述

给你单链表的头节点 `head`，请你反转链表，并返回反转后的头节点。

## 示例

输入：head = [1,2,3,4,5] 输出：[5,4,3,2,1]
## 解题思路

**迭代法（推荐）**：用 prev / curr 两个指针，遍历时逐个反转指针方向：
1. 初始：prev = None, curr = head
2. 循环：保存 curr.next，把 curr.next 指向 prev，prev 和 curr 都前进一步
3. 终止：curr 为 None 时，prev 就是新头节点

**递归法**：递归到链表末尾，回溯时反转指针。代码更简洁但 O(n) 栈空间。

## 代码实现

```python
def reverse_list(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next   # 暂存 next
        curr.next = prev   # 反转指针
        prev = curr        # prev 前移
        curr = nxt         # curr 前移
    return prev
```

## 复杂度分析

- **时间复杂度**：O(n)
- **空间复杂度**：O(1) 迭代法 / O(n) 递归法

## 关键点

- **保存 next 指针**是核心 —— 反转 curr.next = prev 后，链表就断了，不存就找不到后续
- 迭代法空间 O(1)，**面试优先写迭代法**
- 进阶：反转链表前 N 个 / 反转链表 II（区间反转）—— 都是这个模板