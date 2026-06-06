# 4. Binary Search（二分查找）

## 题目描述

给定一个 `n` 个元素有序的（升序）整型数组 `nums` 和一个目标值 `target`，写一个函数搜索 `nums` 中的 `target`，如果目标值存在返回下标，否则返回 `-1`。

## 示例

输入：nums = [-1,0,3,5,9,12], target = 9 输出：4 解释：9 出现在 nums[4]

输入：nums = [-1,0,3,5,9,12], target = 2 输出：-1
## 解题思路

**闭区间 [left, right]**：每次取 `mid = left + (right - left) // 2`（防整数溢出）：
- `nums[mid] == target` → 找到
- `nums[mid] < target` → 目标在右半边，`left = mid + 1`
- `nums[mid] > target` → 目标在左半边，`right = mid - 1`
- `left > right` → 不存在

## 代码实现

```python
def search(nums: list[int], target: int) -> int:
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

## 复杂度分析

- **时间复杂度**：O(log n)，每轮砍半
- **空间复杂度**：O(1)

## 关键点

- **闭区间 [left, right]**：循环条件 `left <= right`，right 初始化 `len-1`，更新 `right = mid - 1`
- **`mid = left + (right - left) // 2`**：防 (left+right) 整数溢出
- 进阶：查找第一个 ≥ target 的位置（lower_bound） / 旋转排序数组搜索