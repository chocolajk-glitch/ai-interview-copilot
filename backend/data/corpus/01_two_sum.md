# 1. Two Sum（两数之和）

## 题目描述

给定一个整数数组 `nums` 和一个目标值 `target`，请你在数组中找出**和为目标值的那两个整数**，并返回它们的下标。

每种输入只会对应一个答案，数组中同一个元素不能被重复使用。

## 示例

输入：nums = [2,7,11,15], target = 9 输出：[0,1] 解释：nums[0] + nums[1] = 2 + 7 = 9
## 解题思路

**暴力解法**：双层循环枚举所有 (i, j) 对，O(n²) 时间。

**哈希表优化**：用哈希表存"已遍历 num → 下标"映射。遍历时对每个 num 检查 `target - num` 是否在表里：
- 在 → 找到答案
- 不在 → 把当前 num 和下标加入表

只一次遍历，O(n) 时间。

## 代码实现

```python
def two_sum(nums: list[int], target: int) -> list[int]:
    seen = {}  # num -> index
    for i, num in enumerate(nums):
        if target - num in seen:
            return [seen[target - num], i]
        seen[num] = i
    return []
```

## 复杂度分析

- **时间复杂度**：O(n)，一次遍历
- **空间复杂度**：O(n)，哈希表最多存 n 个元素

## 关键点

- **哈希查找 O(1)** 替代内层循环，把 O(n²) 优化到 O(n)
- 边遍历边插入哈希表，**保证不会用同一个元素两次**
- 进阶：Three Sum / Four Sum 需要换思路（排序 + 双指针）
