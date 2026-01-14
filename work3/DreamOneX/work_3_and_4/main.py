"""
### 作业 3：矩阵操作与数据分析

#### 要求

1. **数组创建**：创建一个形状为 `(10， 10)` 的 NumPy 数组，命名为 `data_matrix`，使其包含从 0 到 99 的连续整数。
   - 应使用 `numpy.arange` 和 `numpy.reshape` 方法完成。

2. **子矩阵提取**：从 `data_matrix` 中提取出位于中心的 `4x4` 子矩阵。

3. **条件筛选与赋值**：
   - 在 `data_matrix` 中定位所有数值大于 75 的元素。
   - 使用布尔索引（Boolean Indexing）将这些元素的值全部重置为 0。此操作禁止使用任何形式的显式循环。

4. **向量化运算**：对上一步处理后的 `data_matrix` 进行整体缩放，将矩阵中的所有元素乘以 `0.8`。此操作应直接在原数组上（in-place）完成。

5. **数据聚合与定位**：
   - 找出最终矩阵中的最大值。
   - 确定该最大值在矩阵中的行和列索引。
   - **提示**：可结合使用 `numpy.argmax` 和 `numpy.unravel_index` 来高效完成定位。


### 作业 4：广播机制与向量化距离计算

**目标**：考察对 NumPy 核心特性——广播（Broadcasting）机制的理解与应用，以实现高效的向量化计算。

#### 要求

1. **数据生成**：
   - 创建数组 `points_A`，形状为 `(5， 2)`，代表 5 个点的二维坐标。
   - 创建数组 `points_B`，形状为 `(8， 2)`，代表另外 8 个点的二维坐标。
   - 两个数组的数据均使用 `numpy.random.randint` 在 `[0， 100]` 区间内随机生成。

2. **距离矩阵计算**：
   - 计算 `points_A` 中每个点到 `points_B` 中每个点的欧几里得距离，最终生成一个形状为 `(5， 8)` 的距离矩阵 `distance_matrix`。
   - `distance_matrix[i， j]` 应表示 `points_A[i]` 与 `points_B[j]` 之间的距离。
   - **核心要求**：此过程严禁使用任何形式的显式 `for` 或 `while` 循环。必须利用 NumPy 的广播机制完成。
   - **提示**：考虑使用 `numpy.newaxis` 或 `numpy.reshape` 调整数组维度以触发广播。欧几里得距离公式为 $\\sqrt{\\sum(p_i - q_i)^2}$。

3. **轴向数据聚合**：
   - 对于 `points_A` 中的每一个点，从 `distance_matrix` 中找出其与 `points_B` 中所有点的最小距离。
   - 结果应为一个长度为 5 的一维数组。
   - **提示**：研究 `numpy.min` 函数的 `axis` 参数。

4. **复合条件查询**：
   - 找出 `points_B` 中，与 `points_A` 中**至少一个点**的距离小于 20 的所有点的**索引**。
   - **提示**：综合运用布尔掩码、`numpy.any` 以及 `numpy.where`。
"""

import numpy as np

print("=" * 50)
print("作业 3：矩阵操作与数据分析")
print("=" * 50)

data_matrix = np.arange(100).reshape(10, 10).astype(float)  # 转换为浮点型以便后续运算
print("\n1. 原始矩阵 (10x10):")
print(data_matrix)

center_submatrix = data_matrix[3:7, 3:7]
print("\n2. 中心4x4子矩阵:")
print(center_submatrix)

data_matrix[data_matrix > 75] = 0
print("\n3. 将大于75的元素设为0后:")
print(data_matrix)

data_matrix *= 0.8
print("\n4. 所有元素乘以0.8后:")
print(data_matrix)

max_value = data_matrix.max()
max_index = np.argmax(data_matrix)
max_row, max_col = np.unravel_index(max_index, data_matrix.shape)
print(f"\n5. 最大值: {max_value}")
print(f"   位置: 行={max_row}, 列={max_col}")

print("\n" + "=" * 50)
print("作业 4：广播机制与向量化距离计算")
print("=" * 50)

np.random.seed(42)
points_A = np.random.randint(0, 101, size=(5, 2))
points_B = np.random.randint(0, 101, size=(8, 2))
print("\n1. points_A (5x2):")
print(points_A)
print("\npoints_B (8x2):")
print(points_B)

diff = points_A[:, np.newaxis, :] - points_B[np.newaxis, :, :]
distance_matrix = np.sqrt(np.sum(diff ** 2, axis=2))
print("\n2. 距离矩阵 (5x8):")
print(distance_matrix)

min_distances = np.min(distance_matrix, axis=1)
print("\n3. 每个points_A点到points_B的最小距离:")
print(min_distances)

mask = distance_matrix < 20
points_B_indices = np.where(np.any(mask, axis=0))[0]
print("\n4. 与points_A中至少一个点距离小于20的points_B索引:")
print(points_B_indices)

