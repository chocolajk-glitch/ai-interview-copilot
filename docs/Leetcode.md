## Leetcode

#### 时间复杂度

时间复杂度是衡量算法运行时间随输入规模增长而增长的速度的一种度量。它通常使用大O符号表示，关注的是最坏情况下的增长趋势，忽略常数因子和低阶项。输入规模通常用 n*n* 表示，比如数组的长度。

1.两数之和：nums = [2,7,11,15]

暴力法：

将2与后面的数分别相加，观察是否得到target

将7与后面的数分别相加，观察是否得到tartget

以此类推

```python
# 两数之和 - 暴力法：双重循环枚举所有数对，找到和为target的两个索引，时间复杂度O(n^2)
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        for i in range(len(nums)):
            for j in range(i+1,len(nums)):
                if nums[i]+nums[j]==target:
                    return [i,j]
```

哈希表法：

内置函数enumerate，用于在遍历可迭代对象（列表、元组、字符串）时，同时获取元素的索引和值

返回值：一个枚举对象，每次迭代产生一个(index,value)元组

```python
# 两数之和 - 哈希表法：用字典记录已遍历的数，查找target-nums[i]是否在字典中，时间复杂度O(n)
list_0=[0,5,9,8]
for i,num in enumerate(list_0):
    print(i,num)
# 这是一条分割线
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = dict()
        for i,nums in enumerate(nums):
            need = target-nums
            if need in seen:
                return [seen[need],i]
            else:
                seen[nums]=i
```

2.两数相加

迭代法：两个链表逐位相加，用变量v记录当前位之和与进位，每次取v%10作为当前位结果，v//10作为进位，时间复杂度O(max(m,n))

整除与求余：12//10=1	12%10=2

链表：

链表是一种线性数据结构，其中的元素在物理存储单元上非连续、非顺序存放。链表由一系列节点（Node）构成，每个节点包含两个部分：

- 数据域（Data Field）：存储元素的值
- 指针域（Pointer/Reference Field）：存储指向下一个节点（前驱/后继节点）的地址

节点之间通过指针相互链接，形成逻辑上的线性序列

我们在此题中使用单向链表：节点仅含next指针，指向后继节点；尾节点next为NULL

```python
# 两数相加 - 迭代法：逐位相加，v同时记录当前和与进位，虚拟头节点简化链表构建
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def addTwoNumbers(self, l1: Optional[ListNode], l2: Optional[ListNode]) -> Optional[ListNode]:
        v = 0 # 使用v记录 1.：链表l1+l2后的值 2.：存储(l1+l2)之后向后进位的值
         # header指向虚拟头节点，始终指向0
         # l3作为结果链表向前推进的移动指针，始终指向结果链表的最后一个节点
        header=l3=ListNode(0)
        while(l1 or l2 or v):
            v=(l1.val if l1 else 0)+(l2.val if l2 else 0)+v
            l3.next = ListNode(v%10) # 创建结果链表的新节点，值为v%10
            v=v//10 # 计算进位值，供下一位使用
            l3=l3.next
            l1=l1.next if l1 else None
            l2=l2.next if l2 else None
        return header.next
```

3.无重复字符的最长子串

滑动窗口：用数组维护当前窗口内的字符，遇到重复字符时从左端逐个弹出，直到窗口内无重复，时间复杂度O(n)

```python
# 无重复字符的最长子串 - 滑动窗口：数组维护当前窗口，遇到重复则从左端弹出
class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        arr = []
        res = 0
        for i in s:
            while(i in arr):
                arr.pop(0)
            arr.append(i)
            res = max(res,len(arr))
        return res
```

4.寻找两个正序数组的中位数

合并排序法：将两个数组合并后排序，根据长度奇偶返回中位数，时间复杂度O((m+n)log(m+n))

```python
# 寻找两个正序数组的中位数 - 合并排序法：合并两数组后排序，取中位数
class Solution:
    def findMedianSortedArrays(self, nums1: List[int], nums2: List[int]) -> float:
        nums3 = nums1 + nums2
        nums3.sort()
        length = len(nums3)
        if length % 2 == 1:
            return nums3[length // 2]
        else:
            return (nums3[length // 2] + nums3[length // 2 -1]) /2.0
```

5.最长回文子串

动态规划（DP）：用二维布尔数组dp[i][j]表示子串s[i:j+1]是否为回文串，按子串长度从小到大填表，状态转移：当s[i]==s[j]且j-i<=2或dp[i+1][j-1]为True时dp[i][j]=True，时间复杂度O(n^2)

DP表格（二维数组）的定义：

```python
# 最长回文子串 - 动态规划：dp[i][j]表示s[i:j+1]是否为回文，按子串长度从小到大填表
# 我们创建一个n*n的布尔型二维数组dp,dp[i][j]表示从索引i到索引j的子串是否是回文串
# dp[1][3]表示子串s[1:4] (切片)
dp = [[False] * n for _ in range(n)]
# n为字符串长度 [False] * n 创建了一个长度为n的一维列表
# 外层列表推导式重复执行[False] * n共n次，每次生成一个新的列表，最终形成二维列表
# 填表顺序：按照子串的长度从小到大计算
# 长度大于三，当我们想计算dp[i][j]时，需要用到dp[i+1][j-1]
# 故计算dp[i][j]时，按j从小到大，i从0到j-1的顺序，保证依赖的小区间已经计算完毕

class Solution:
    def longestPalindrome(self, s: str) -> str:
        n=len(s)
        if n<2:
            return s
        dp = [[False] * n for _ in range(n)]
        max_length=1
        index=0
        for i in range(n):
            dp[i][i]=True
        for j in range(1,n):
            for i in range(j):
                if s[i]==s[j]:
                    if j-i<=2:
                        dp[i][j]=True
                    else:
                        dp[i][j]=dp[i+1][j-1]
                if dp[i][j]==True:
                    length = j-i+1
                    if length>max_length:
                        max_length=length
                        index=i
        return s[index:index+max_length]
```

6.Z字形变换：

![image-20260418092126596](C:\Users\24312\AppData\Roaming\Typora\typora-user-images\image-20260418092126596.png)

行号存在一个V形周期：0-5	6-11	12-17

我们可以计算出周期的长度：n=numRows+numRows-2

对于字符串中的第i个字符，它在周期中的位置x=i%n	此时行号取min(x,n-x)

```python
# Z字形变换 - 周期规律：计算V形周期长度n=numRows*2-2，每个字符的行号为min(x, n-x)
class Solution:
    def convert(self, s: str, numRows: int) -> str:
        if numRows==1:
            return s
        n=numRows*2-2
        res=[""] * numRows
        for i,num in enumerate(s):
            x=i % n
            row = min(x,n-x)
            res[row]=res[row]+num #将num追加到res[row]的末尾
        return "".join(res)
```

7.整数反转：

通过取余不断算出最后一位数字，如123

- 3
- 2+3*10 = 32
- 1+32*10 = 321

注意溢出判断：32位有符号整数范围为[-2^31, 2^31-1]

```python
# 整数反转 - 取余法：不断取出最后一位数字，拼接到结果上，注意溢出判断
class Solution:
    def reverse(self, x: int) -> int:
        y = abs(x)
        res = 0
        min_x = 2 ** 31
        max_x = 2 ** 31 - 1
        bou = max_x if x > 0 else min_x
        while(y!=0):
            res = y %10 + res * 10
            if res > bou:
                return 0
            y = y // 10
        return res if x > 0 else -res
```

8.字符串转换整数（and符的优先级大于or符）

按顺序处理：跳过前导空格、判断正负号、逐位转换数字，注意溢出截断到32位整数范围[-2^31, 2^31-1]

```python
# 字符串转换整数 - 逐位解析：跳过空格、判断正负、逐位转换，溢出时截断到32位范围
class Solution:
    def myAtoi(self, s: str) -> int:
        i = 0
        n = len(s)
        while(i<n and s[i]==' '):
            i=i+1
        if i==n:
            return 0
        flag=1
        if s[i]=='-':
            flag = -1
        if s[i]=='-' or s[i]=='+':
            i = i+1
        res = 0
        max_res = 2**31-1
        min_res = -2**31
        while(i<n and '0'<=s[i]<='9'):
            res = int(s[i])+ res * 10
            i=i+1
            if res>max_res:
                break
        res = res * flag
        if res > max_res:
            return max_res
        if res < min_res:
            return min_res
        else:
            return res
```

9.回文数

双指针法：将数字转为字符串，左右双指针向中间靠拢，逐位比较是否相等，时间复杂度O(n)

```python
# 回文数 - 双指针法：转为字符串后左右双指针向中间比较
class Solution:
    def isPalindrome(self, x: int) -> bool:
        s=str(x)
        if x==1:
            return True
        n=len(s)
        i,j=0,n-1
        while(i<j):
            if s[i]==s[j]:
                i=i+1
                j=j-1
            else:
                return False
        return True
```

10.正则表达式匹配

动态规划：dp[i][j]表示s前i个字符与p前j个字符是否匹配。当p[j-1]为'*'时，可匹配0次(dp[i][j-2])或1+次(dp[i-1][j])；否则需当前字符匹配且dp[i-1][j-1]为True，时间复杂度O(mn)

'.'：匹配单个字符	'*'：匹配零个或多个前面的那一个元素

dp = [[False] * n for _ in range(m)]	生成一个m行n列的列表

```python
# 正则表达式匹配 - 动态规划：dp[i][j]表示s[:i]与p[:j]是否匹配，'*'可匹配0次或多次
class Solution:
    def isMatch(self, s: str, p: str) -> bool:
        m = len(s)
        n = len(p)
        dp = [[False] * (n + 1) for _ in range(m + 1)]
        dp[0][0] = True

        def match(i, j):
            if i == 0:
                return False
            if p[j - 1] == '.':
                return True
            else:
                return s[i - 1] == p[j - 1]

        for i in range(m + 1): # 在match函数中对i==0的情况进行了保护处理
            for j in range(1, n + 1): # 若range(n+1) 当j为0时会访问p[-1]导致逻辑错误
                if p[j - 1] == '*':
                    # |= 实现了逻辑或累积，保证只要任一分支为True满足，结果即为 True
                    dp[i][j] |= dp[i][j - 2] # 匹配0次
                    if match(i, j - 1):
                        dp[i][j] |= dp[i - 1][j] # 匹配1次或多次
                if match(i, j):
                    dp[i][j] |= dp[i - 1][j - 1]
        return dp[m][n]
```

11.盛最多水的容器：双指针

左右双指针从两端向中间靠拢，每次移动较短的一边，因为面积由较短边决定，移动较长边不可能增大面积，时间复杂度O(n)

```python
# 盛最多水的容器 - 双指针：左右指针从两端向中间，每次移动较短边，面积由短边决定
class Solution:
    def maxArea(self, height: List[int]) -> int:
        n=len(height)
        res=0
        i,j=0,n-1
        while(i<j):
            if height[i]<height[j]:
                area=height[i]*(j-i)
                res=max(res,area)
                i=i+1
            else:
                area=height[j]*(j-i)
                res=max(res,area)
                j=j-1
        return res
```

12.整数转罗马数字：

贪心法：从大到小遍历罗马数字符号表，每次尽量用最大的符号，减去对应数值，直到num为0

```python
# 整数转罗马数字 - 贪心法：从大到小遍历符号表，每次用最大符号减去对应值
class Solution:
    def intToRoman(self, num: int) -> str:
        list_d = [
            (1000, 'M'),
            (900, 'CM'),
            (500, 'D'),
            (400, 'CD'),
            (100, 'C'),
            (90, 'XC'),
            (50, 'L'),
            (40, 'XL'),
            (10, 'X'),
            (9, 'IX'),
            (5, 'V'),
            (4, 'IV'),
            (1, 'I')
        ]
        res = []
        for value, symbol in list_d:
            while (num >= value):
                num = num - value
                res.append(symbol)
                if (num == 0):
                    break
        return ''.join(res)
```

13.罗马数字转整数：

哈希表法：用字典存储罗马字符对应的数值，从左到右遍历，若当前字符值小于下一个字符值则减去，否则加上，最后加上最后一个字符的值，时间复杂度O(n)

```python
# 罗马数字转整数 - 哈希表法：当前字符值小于下一个则减去，否则加上
class Solution:
    def romanToInt(self, s: str) -> int:
        dict1={'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
        n=len(s)
        res=0
        for i in range(n-1):
            if dict1[s[i]]<dict1[s[i+1]]:
                res=res-dict1[s[i]]
            else:
                res=res+dict1[s[i]]
        return res + dict1[s[-1]]
```

14.最长公共前缀：

逐个比较法：以第一个字符串为基准，依次与每个字符串求公共前缀，若公共前缀为空则提前返回，时间复杂度O(S)，S为所有字符串总长度

```python
# 最长公共前缀 - 逐个比较法：以第一个字符串为基准，依次与每个字符串求公共前缀
class Solution:
    def longestCommonPrefix(self, strs: List[str]) -> str:
        def lcp(str1,str2):
            index=0
            min_len=min(len(str1),len(str2))
            while index<min_len and str1[index]==str2[index]:
                index=index+1
            return str1[:index]
        if not strs:
            return ''
        n=len(strs)
        prefix=strs[0]
        for i in range(1,n):
            prefix=lcp(prefix,strs[i])
            if not prefix:
                break
        return prefix
```

15.三数之和：

排序+双指针：先排序，固定第一个数，用左右双指针在剩余区间找两数之和等于负的第一个数，注意跳过重复元素，时间复杂度O(n^2)

```python
# 三数之和 - 排序+双指针：固定第一个数，左右指针找两数之和等于其相反数，跳过重复
class Solution:
    def threeSum(self, nums: list[int]) -> list[list[int]]:
        nums.sort()
        n=len(nums)
        res=[]
        for i in range(n):
            if nums[i]>0:
                return res
            # 防止访问nums[-1]
            if i>0 and nums[i]==nums[i-1]:
                continue #此处不能是i=i+1 i的值始终由range生成器控制
            L=i+1
            R=n-1
            while L<R:
                if nums[i]+nums[L]+nums[R]==0:
                    res.append([nums[i],nums[L],nums[R]])
                    while L<R and nums[L]==nums[L+1]:
                        L=L+1
                    while L<R and nums[R]==nums[R-1]:
                        R=R-1
                    L=L+1
                    R=R-1
                elif nums[i]+nums[L]+nums[R]>0:
                    R=R-1
                else:
                    L=L+1
        return res
```

16.最接近的三数之和：

排序+双指针：与三数之和类似，固定第一个数，双指针在剩余区间搜索，记录与target最接近的三数之和，时间复杂度O(n^2)

```python
# 最接近的三数之和 - 排序+双指针：固定第一个数，双指针搜索最接近target的三数之和
class Solution:
    def threeSumClosest(self, nums: List[int], target: int) -> int:
        nums.sort()
        n=len(nums)
        res=float("inf")
        for i in range(n-2):
            L=i+1
            R=n-1
            while L<R:
                tmp=nums[i]+nums[L]+nums[R]
                res=tmp if abs(tmp-target)<abs(res-target) else res
                if tmp==target:
                    return target
                elif tmp>target:
                    R=R-1
                else:
                    L=L+1
        return res
```

17.电话号码的字母组合（回溯）：

用字典存储数字到字母的映射，DFS回溯逐位选择字母，当path长度等于digits长度时加入结果，时间复杂度O(4^n)

```python
# 电话号码的字母组合 - 回溯DFS：逐位选择字母，path长度等于digits长度时收集结果
class Solution:
    def letterCombinations(self, digits: str) -> List[str]:
        dic={
            '2':['a','b','c'],
            '3':['d','e','f'],
            '4':['g','h','i'],
            '5':['j','k','l'],
            '6':['m','n','o'],
            '7':['p','q','r','s'],
            '8':['t','u','v'],
            '9':['w','x','y','z'],
        }
        res=[]
        if not digits:
            return res
        n=len(digits)
         # path存放当前正在构建的字母组合 depth表示当前处理到digits中的第几个数字
        def dfs(path,depth):
            if len(path)==n:
                res.append(''.join(path))
                return
            for v in dic[digits[depth]]:
                path.append(v)
                dfs(path,depth+1)
                path.pop()
        dfs([],0)
        return res
```

18.四数之和：与三数之和类似，最终转化为两数之和即可

排序+双指针：固定前两个数，双指针在剩余区间搜索，注意跳过重复元素，时间复杂度O(n^3)

```python
# 四数之和 - 排序+双指针：固定前两个数，双指针搜索剩余区间，跳过重复
class Solution:
    def fourSum(self, nums: List[int], target: int) -> List[List[int]]:
        nums.sort()
        n=len(nums)
        res=[]
        for i in range(n-3):
            if i>0 and nums[i]==nums[i-1]:
                continue
            for j in range(i+1,n-2):
                if j>i+1 and nums[j]==nums[j-1]:
                    continue
                L=j+1
                R=n-1
                while L<R:
                    tmp=nums[i]+nums[j]+nums[L]+nums[R]
                    if tmp==target:
                        res.append([nums[i],nums[j],nums[L],nums[R]])
                        while L<R and nums[L]==nums[L+1]:
                            L=L+1
                        while L<R and nums[R]==nums[R-1]:
                            R=R-1
                        L=L+1
                        R=R-1
                    elif tmp>target:
                        R=R-1
                    else:
                        L=L+1
        return res
```

19.删除链表的倒数第N个结点：快慢指针

快指针先走N步，然后快慢指针同时前进，当快指针到达末尾时，慢指针的下一个节点即为要删除的节点，使用虚拟头节点处理删除头节点的情况，时间复杂度O(n)

```python
# 删除链表的倒数第N个结点 - 快慢指针：快指针先走N步，然后同步前进，慢指针指向待删除节点的前驱
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def removeNthFromEnd(self, head: Optional[ListNode], n: int) -> Optional[ListNode]:
        res=ListNode(0,head)
        f,s=head,res
        for i in range(n):
            f=f.next
        while f:
            f=f.next
            s=s.next
        s.next=s.next.next
        return res.next
```

20.有效的括号：栈

用栈存储左括号，遇到右括号时检查栈顶是否为对应的左括号，遍历结束后栈应为空，时间复杂度O(n)

```python
# 有效的括号 - 栈：左括号入栈，右括号检查栈顶是否匹配，最终栈应为空
class Solution:
    def isValid(self, s: str) -> bool:
        n=len(s)
        if n%2==1:
            return False
        dic={
            ')':'(',
            '}':'{',
            ']':'['
        }
        stack=[]
        for i in s:
            # 将左括号存入栈stack中
            if i not in dic:
                stack.append(i)
            # 当取出的i为右括号时，进入elif分支
            elif not stack or dic[i]!=stack.pop(): #pop() 删除并返回列表的最后一个元素
                return False
        return not stack
```

21.合并两个有序链表：

递归法：比较两个链表头节点值，较小值的节点的next指向其余节点合并的结果，时间复杂度O(m+n)

```python
# 合并两个有序链表 - 递归法：比较头节点值，较小者的next指向剩余合并结果
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def mergeTwoLists(self, list1: Optional[ListNode], list2: Optional[ListNode]) -> Optional[ListNode]:
        if not list1:
            return list2
        if not list2:
            return list1
        if list1.val < list2.val:
            list1.next=self.mergeTwoLists(list1.next,list2)
            return list1
        else:
            list2.next=self.mergeTwoLists(list1,list2.next)
            return list2
```

49.字母异位词分组：

哈希表法：将每个字符串排序后作为key，相同key的字符串归为一组，时间复杂度O(n*klogk)，k为字符串最大长度

```python
# 字母异位词分组 - 哈希表法：排序后的字符串作为key，相同key归为一组
class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        n=len(strs)
        if n==1:
            return [strs]
        dict={}
        for ss in strs:
            s=str(sorted(ss)) #sorted后是list，将其转化为str
            if s not in dict:
                dict[s]=[ss]
            else:
                dict[s].append(ss)
        return list(dict.values())
```

128.最长连续序列：

哈希表法：用字典记录每个数所在连续序列的长度，对每个新数检查左右邻居是否已在字典中，合并更新序列长度，时间复杂度O(n)

```python
# 最长连续序列 - 哈希表法：字典记录每个数所在连续序列长度，检查左右邻居合并更新
class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        dict={}
        res=0
        for num in nums:
            if num not in dict: #num不在字典中时执行逻辑
                # 检查num1的左右邻居在哈希表中是否存在
                left=dict.get(num-1,0)
                right=dict.get(num+1,0)
                cur=left+right+1
                res=max(res,cur)
                dict[num]=cur
                dict[num-left]=cur
                dict[num+right]=cur
        return res
```

42.接雨水：单调栈

维护单调递减栈，当新柱子高度大于栈顶时弹出栈顶，计算弹出柱子与当前柱子和新栈顶之间的凹槽面积，时间复杂度O(n)

```python
# 接雨水 - 单调栈：维护单调递减栈，弹出栈顶时计算凹槽面积
class Solution:
    def trap(self, height: List[int]) -> int:
        n=len(height)
        stack=[]
        ans=0
        for i in range(n):
            while stack and height[i]>height[stack[-1]]:
                top=stack.pop() #每当新的柱子高度大于栈底元素时，弹出，确保栈的单调递减
                if not stack:
                    break
                w=i-stack[-1]-1
                # 取左右边界的最小值与弹出的值相减 计算出高度
                h=min(height[i],height[stack[-1]])-height[top]
                ans=ans+w*h
            stack.append(i)
        return ans
```

283.移动零

双指针法：左指针指向已处理的非零元素末尾，右指针遍历数组，遇到非零元素则与左指针位置交换，时间复杂度O(n)

```python
# 移动零 - 双指针：左指针指向非零末尾，右指针遍历，非零元素交换到前面
class Solution:
    def moveZeroes(self, nums: List[int]) -> None:

        """
        Do not return anything, modify nums in-place instead.
        """
        n = len(nums)
        l,r=0,0
        while r<n:
            if nums[r]!=0:
                nums[r],nums[l]=nums[l],nums[r]
                l=l+1
            r=r+1
```

438.找到字符串中所有字母异位词：滑动窗口

用两个长度为26的数组分别统计窗口和p的字符频率，滑动窗口右移时更新频率数组，频率相等则记录起始索引，时间复杂度O(n)

```python
# 找到字符串中所有字母异位词 - 滑动窗口：频率数组统计窗口和p的字符，频率相等则记录
class Solution:
    def findAnagrams(self, s: str, p: str) -> List[int]:
        n,m,res=len(s),len(p),[]
        if n<m:
            return res
        p_cou=[0]*26
        s_cou=[0]*26
        for i in range(m):
            s_cou[ord(s[i])-ord('a')]+=1
            p_cou[ord(p[i])-ord('a')]+=1
        if p_cou==s_cou:
            res.append(0)
        for i in range(m,n):
            s_cou[ord(s[i-m])-ord('a')]-=1
            s_cou[ord(s[i])-ord('a')]+=1
            if p_cou==s_cou:
                res.append(i-m+1)
        return res
```

76.最小覆盖子串：

滑动窗口：右指针扩展窗口直到包含t所有字符，然后左指针收缩窗口去除多余字符，记录最小窗口，时间复杂度O(|s|+|t|)

```python
# 最小覆盖子串 - 滑动窗口：右指针扩展到包含t所有字符，左指针收缩去多余字符，记录最小窗口
class Solution:
    def minWindow(self, s: str, t: str) -> str:
        needcnt=len(t)
         # 该字典在访问不存在的键时会自动调用int()返回0，并把这个键值对(key,0)存入字典
        need=collections.defaultdict(int)
        for c in t:
            need[c]+=1
        res=(0,float('inf'))
        i=0
        for j,c in enumerate(s):
            if need[c]>0:
                needcnt-=1
            need[c]-=1
            if needcnt==0:
                while True:
                    c=s[i] # 左指针指向的字符
                    if need[c]==0:
                        break
                    need[c]+=1
                    i+=1 # 跳过所有多余字符，直到i指向必需字符
                if j-i<res[1]-res[0]:
                    res=(i,j)
                need[s[i]]+=1
                needcnt+=1
                i+=1 # 跳过必需字符，寻找下一个可能的最优窗口
        return '' if res[1]==float('inf') else s[res[0]:res[1]+1]
```

560.和为K的子数组：

前缀和+哈希表：用字典记录前缀和出现的次数，对每个位置检查presum-k是否在字典中，若存在则累加对应次数，时间复杂度O(n)

```python
# 和为K的子数组 - 前缀和+哈希表：字典记录前缀和出现次数，查找presum-k是否存在
class Solution:
    def subarraySum(self, nums: List[int], k: int) -> int:
        presum=0
        pre={0:1} # 初始化 前缀和为0 出现1次
        n=len(nums)
        res=0
        for i in range(n):
            presum=presum+nums[i]
            r=presum-k
            if r in pre:
                res=res+pre[r]
            pre[presum]=pre.get(presum,0)+1
        return res
```

239.滑动窗口最大值：

单调队列：用双端队列存储数组索引，维护队列单调递减，队首始终为当前窗口最大值的索引，时间复杂度O(n)

```python
# 滑动窗口最大值 - 单调队列：双端队列维护单调递减，队首为当前窗口最大值索引
class Solution:
    def maxSlidingWindow(self, nums: List[int], k: int) -> List[int]:
        n=len(nums)
         # 创建一个空的双端队列(double-ended queue)，允许两端进两端出，普通队列只允许一端
        q=collections.deque()
        res=[]
        for i in range(k):
            while q and nums[i]>nums[q[-1]]:
                q.pop()
            q.append(i)
        res.append(nums[q[0]])
        for i in range(k,n):
            while q and nums[i]>nums[q[-1]]:
                q.pop()
            q.append(i)
            while q and q[0]+k<=i:
                q.popleft()
            res.append(nums[q[0]])
        return res
```

53.最大子数组和：

动态规划：dp[i]表示以nums[i]结尾的最大子数组和，状态转移dp[i]=max(nums[i], dp[i-1]+nums[i])，时间复杂度O(n)

```python
# 最大子数组和 - 动态规划：dp[i]为以nums[i]结尾的最大子数组和，dp[i]=max(nums[i], dp[i-1]+nums[i])
class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        n=len(nums)
        dp=[0]*n
        dp[0]=nums[0]
        for i in range(1,n):
            dp[i]=max(nums[i],dp[i-1]+nums[i])
        return max(dp)
```

56.合并区间：

排序法：按区间左端点排序，遍历区间，若当前区间与结果中最后一个区间重叠则合并，否则直接加入结果，时间复杂度O(nlogn)

```python
# 合并区间 - 排序法：按左端点排序，重叠则合并，否则加入结果
class Solution:
    def merge(self, intervals: List[List[int]]) -> List[List[int]]:
        if not intervals:
            return []
        intervals.sort()
        res=[intervals[0]]
        for x,y in intervals[1:]:
            # res[-1][-1]表示最后一个区间的最后一个元素
            if x>res[-1][-1]:
                res.append([x,y])
            else:
                y=max(res[-1][-1],y)
                res[-1][-1]=y
        return res    
```

189.轮转数组

三次反转法：先反转整个数组，再反转前k个元素，再反转后n-k个元素，轮转k步等价于轮转k%n步，时间复杂度O(n)，空间复杂度O(1)

```python
# 轮转数组 - 三次反转法：整体反转→前k个反转→后n-k个反转，k等价于k%n
class Solution:
    def rotate(self, nums: List[int], k: int) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        def reverse(i,j):
            while i<j:
                nums[i],nums[j]=nums[j],nums[i]
                i+=1
                j-=1
        n=len(nums)
        # 轮转k步与轮转k%n步的效果完全相同 如n为4时，轮转4步与轮转0步效果一样
        k = k%n
        reverse(0,n-1)
        reverse(0,k-1)
        reverse(k,n-1)
```

238.除了自身以外数组的乘积：

左右前缀积法：用left数组记录每个元素左侧所有元素的乘积，right数组记录右侧乘积，结果为left[i]*right[i]，时间复杂度O(n)，空间复杂度O(n)

```python
# 除了自身以外数组的乘积 - 左右前缀积：left[i]为左侧乘积，right[i]为右侧乘积，结果为两者相乘
class Solution:
    def productExceptSelf(self, nums: List[int]) -> List[int]:
        n=len(nums)
        left=[1]*n
        for i in range(1,n):
            left[i]=left[i-1]*nums[i-1]
        right=[1]*n
        # range(start,stop,step) 包含start不包含stop 从倒数第二个元素开始计算每个元素右侧乘积
        for i in range(n-2,-1,-1):
            right[i]=right[i+1]*nums[i+1]
        ans=[]
        for i in range(n):
            ans.append(left[i]*right[i])
        return ans
```

41.缺失的第一个正数：

原地哈希法：先将非正数替换为n+1，然后对每个绝对值<=n的数，将对应位置标记为负，最后第一个正数的位置+1即为答案，时间复杂度O(n)，空间复杂度O(1)

```python
# 缺失的第一个正数 - 原地哈希：非正数替换为n+1，用数组下标标记存在的数，第一个正数位置即为答案
class Solution:
    def firstMissingPositive(self, nums: List[int]) -> int:
        n=len(nums)
        for i in range(n):
            if nums[i]<=0:
                nums[i]=n+1
        for i in range(n):
            num=abs(nums[i])
            if num<=n:
                nums[num-1]=-abs(nums[num-1])
        for i in range(n):
            if nums[i]>0:
                return i+1
        return n+1
```

73.矩阵置零：

标记法：用两个布尔数组分别记录哪一行和哪一列需要置零，先遍历记录0的位置，再根据标记置零，时间复杂度O(mn)，空间复杂度O(m+n)

```python
# 矩阵置零 - 标记法：用布尔数组记录含零的行和列，再统一置零
class Solution:
    def setZeroes(self, matrix: List[List[int]]) -> None:
        """
        Do not return anything, modify matrix in-place instead.
        """
        m,n=len(matrix),len(matrix[0])
        row,col=[False]*m,[False]*n
        for i in range(m):
            for j in range(n):
                if matrix[i][j]==0:
                    row[i]=col[j]=True
        for i in range(m):
            for j in range(n):
                if row[i] or col[j]:
                    matrix[i][j]=0
```

54.螺旋矩阵：

边界模拟法：维护上下左右四个边界，按顺时针方向逐层遍历，每遍历完一条边收缩对应边界，时间复杂度O(mn)

```python
# 螺旋矩阵 - 边界模拟法：维护上下左右四个边界，顺时针逐层遍历并收缩边界
class Solution:
    def spiralOrder(self, matrix: List[List[int]]) -> List[int]:
        if not matrix or not matrix[0]:
            return []
        res=[]
        top,left,bottom,right=0,0,len(matrix)-1,len(matrix[0])-1
        while left<=right and top<=bottom:
            for i in range(left,right+1):
                res.append(matrix[top][i])
            for i in range(top+1,bottom+1):
                res.append(matrix[i][right])
            if left<right and top<bottom:
                for i in range(right-1,left,-1):
                    res.append(matrix[bottom][i])
                for i in range(bottom,top,-1):
                    res.append(matrix[i][left])
            left+=1
            top+=1
            bottom-=1
            right-=1
        return res
```

48.旋转图像：

两次翻转法：先沿水平中线上下翻转，再沿主对角线转置，即可实现顺时针旋转90度，时间复杂度O(n^2)，空间复杂度O(1)

```python
# 旋转图像 - 两次翻转法：先上下翻转，再沿主对角线转置，实现顺时针旋转90度
class Solution:
    def rotate(self, matrix: List[List[int]]) -> None:
        """
        Do not return anything, modify matrix in-place instead.
        """
        n=len(matrix)
        i,j=0,n-1
        while i<j:
            for m in range(n):
                matrix[i][m],matrix[j][m]=matrix[j][m],matrix[i][m]
            i+=1
            j-=1
        for x in range(1,n):
            for y in range(x):
                matrix[x][y],matrix[y][x]=matrix[y][x],matrix[x][y]
```

240.搜索二维矩阵||：二分查找

逐行二分查找：对每一行使用二分查找搜索target，时间复杂度O(mlogn)

```python
# 搜索二维矩阵II - 逐行二分查找：对每一行使用二分搜索target
class Solution:
    def searchMatrix(self, matrix: List[List[int]], target: int) -> bool:
        m=len(matrix)    # 矩阵的行数
        n=len(matrix[0]) # 取第一行的长度计算矩阵的列数
        for row in range(m):
            i,j=0,n-1
            while i<=j:
                mid=i+(j-i)//2
                if matrix[row][mid]==target:
                    return True
                elif matrix[row][mid]>target:
                    j=mid-1
                else:
                    i=mid+1
        return False
```

160.相交链表：

双指针法：指针A遍历完链表A后跳到链表B头部，指针B反之，两指针必在交点处相遇，若不相交则同时到达None，时间复杂度O(m+n)，空间复杂度O(1)

```python
# 相交链表 - 双指针法：A走完链表A后跳到B，B反之，必在交点相遇
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def getIntersectionNode(self, headA: ListNode, headB: ListNode) -> Optional[ListNode]:
        A=headA
        B=headB
        while A!=B:
            A=A.next if A else headB
            B=B.next if B else headA
        return A
```

206.反转链表：

迭代法：用pre和cur两个指针，每次保存cur的下一个节点，将cur.next指向pre，然后pre和cur分别后移，时间复杂度O(n)，空间复杂度O(1)

```python
# 反转链表 - 迭代法：pre和cur双指针，逐个反转指针方向
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:
        pre,cur=None,head
        while cur:
            next=cur.next
            cur.next=pre # 反转指针
            pre=cur
            cur=next
        return pre
```

234.回文链表

快慢指针+反转：快慢指针找到链表中点，反转后半部分，然后前后半部分逐节点比较，时间复杂度O(n)，空间复杂度O(1)

```python
# 回文链表 - 快慢指针找中点+反转后半部分+逐节点比较
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def isPalindrome(self, head: Optional[ListNode]) -> bool:
        # 快慢指针，快指针一次走两步，慢指针一次走一步
        def move(head):
            f,s=head,head
            while f.next and f.next.next:
                f=f.next.next
                s=s.next
            return s
        def reverse(head):
            pre,cur=None,head
            while cur:
                next=cur.next
                cur.next=pre
                pre=cur
                cur=next
            return pre
        first_step=move(head)
        second_step=reverse(first_step.next)
        result=True
        first_position=head
        second_position=second_step
        while second_position and result:
            if first_position.val != second_position.val:
                return False
            first_position=first_position.next
            second_position=second_position.next
        return result
```

141.环形链表：

快慢指针法：快指针每次走两步，慢指针每次走一步，若存在环则两指针必在环内相遇，时间复杂度O(n)，空间复杂度O(1)

```python
# 环形链表 - 快慢指针法：快指针走两步慢指针走一步，有环则必相遇
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None
class Solution:
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        if not head or not head.next:
            return False
        f,s=head,head # 定义快慢指针，若存在环，则两个指针会相遇
        while f and f.next:
            s=s.next
            f=f.next.next
            if s==f:
                return True
        return False
```

142.环形链表 ||：

哈希表法：用set记录已访问的节点，第一个重复出现的节点即为环的入口，时间复杂度O(n)，空间复杂度O(n)

```python
# 环形链表II - 哈希表法：set记录已访问节点，第一个重复出现的即为环入口
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def detectCycle(self, head: Optional[ListNode]) -> Optional[ListNode]:
        seen=set()
        while head:
            if head in seen:
                return head
            seen.add(head)
            head=head.next
        return 
```

24.两两交换链表中的节点

递归法：交换前两个节点，将第二个节点的next指向递归处理后的子链表头，时间复杂度O(n)

```python
# 两两交换链表中的节点 - 递归法：交换前两个节点，第二个的next指向递归处理后的子链表
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def swapPairs(self, head: Optional[ListNode]) -> Optional[ListNode]:
        if not head or not head.next:
            return head
        tmp=head.next
        head.next=self.swapPairs(tmp.next)
        tmp.next=head
        return tmp
```

25.K个一组翻转链表

迭代法：每k个节点为一组进行翻转，用辅助函数reverse翻转指定区间，翻转后将子链表接回原链表，不足k个的不翻转，时间复杂度O(n)

```python
# K个一组翻转链表 - 迭代法：每k个节点一组翻转，辅助函数reverse翻转区间，不足k个不翻转
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def reverseKGroup(self, head: Optional[ListNode], k: int) -> Optional[ListNode]:
        def reverse(head,tail):
            pre=None
            cur=head
            while pre != tail:
                next=cur.next
                cur.next=pre
                pre=cur
                cur=next
            return tail,head
        start=ListNode(0)
        start.next=head
        pre=start
        while head:
            tail=pre
            for i in range(k):
                tail=tail.next
                if not tail:
                    return start.next
            next=tail.next
            head,tail=reverse(head,tail)
            # 将翻转后的子链表接回原链表
            pre.next=head
            tail.next=next
		   # 移动pre和head到下一组
            pre=tail
            head=tail.next
        return start.next

```

138.随机链表的复制：

哈希表法：第一遍遍历创建所有新节点并用字典建立原节点到新节点的映射，第二遍遍历根据映射设置新节点的next和random指针，时间复杂度O(n)，空间复杂度O(n)

```python
# 随机链表的复制 - 哈希表法：第一遍创建新节点建立映射，第二遍设置next和random指针
"""
# Definition for a Node.
class Node:
    def __init__(self, x: int, next: 'Node' = None, random: 'Node' = None):
        self.val = int(x)
        self.next = next
        self.random = random
"""

class Solution:
    def copyRandomList(self, head: 'Optional[Node]') -> 'Optional[Node]':
        if not head:
            return None
        node_map={}
        cur=head
        while cur:
            node_map[cur]=Node(cur.val)
            cur=cur.next
        cur=head
        while cur:
            if cur.next:
                node_map[cur].next=node_map[cur.next]
            if cur.random:
                node_map[cur].random=node_map[cur.random]
            cur=cur.next
        return node_map[head]
```

148.排序链表：

归并排序：快慢指针找中点，递归排序左右两半，然后合并两个有序链表，时间复杂度O(nlogn)，空间复杂度O(logn)（递归栈）

```python
# 排序链表 - 归并排序：快慢指针找中点，递归排序左右两半，合并有序链表
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def sortList(self, head: Optional[ListNode]) -> Optional[ListNode]:
        if not head or not head.next:
            return head
        f,s=head.next,head
        while f and f.next:
            f=f.next.next
            s=s.next
        mid=s.next
        s.next=None
        l=self.sortList(head)
        r=self.sortList(mid)
        ans=res=ListNode(0)
        while l and r:
            if l.val<r.val:
                res.next=l
                l=l.next
            else:
                res.next=r
                r=r.next
            res=res.next
        res.next=l if l else r
        return ans.next
```

23.合并K个升序链表：

收集排序法：遍历所有链表将节点值收集到数组中，排序后重新构建链表，时间复杂度O(NlogN)，N为所有节点总数

```python
# 合并K个升序链表 - 收集排序法：遍历所有链表收集节点值，排序后重建链表
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def mergeKLists(self, lists: List[Optional[ListNode]]) -> Optional[ListNode]:
        nums=[]
        for l in lists:
            i=l
            while i:
                nums.append(i.val)
                i=i.next
        nums.sort()
        head=cur=ListNode(0)
        for i in range(len(nums)):
            cur.next=ListNode(nums[i])
            cur=cur.next
        return head.next
```
