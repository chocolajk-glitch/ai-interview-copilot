# 两数之和

给定一个整数数组 nums 和目标值 target。

## 思路

用哈希表记录已遍历数字到下标的映射。

## 代码

```python
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
```

## 复杂度

O(n) 时间，O(n) 空间。
