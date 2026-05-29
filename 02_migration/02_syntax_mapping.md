# Hive ↔ Lakehouse 语法对照

本文档列出本项目迁移过程中遇到的所有语法差异，以及实际验证过的 Lakehouse 等价写法。

## DDL

### 建表

| 场景 | Hive | Lakehouse |
|------|------|-----------|
| 普通表 | `CREATE TABLE t (...) STORED AS ORC` | `CREATE TABLE t (...)` |
| 分区表 | `CREATE TABLE t (...) PARTITIONED BY (dt STRING) STORED AS ORC` | `CREATE TABLE t (...) PARTITIONED BY (dt STRING)` |
| 外部表 | `CREATE EXTERNAL TABLE t (...) LOCATION '/path'` | 不需要，用 COPY INTO 从 Volume 加载 |
| 分桶表 | `CLUSTERED BY (col) INTO N BUCKETS` | 语法相同，直接兼容 |
| ORC 压缩 | `TBLPROPERTIES ("orc.compress"="SNAPPY")` | 删除，Lakehouse 自动压缩 |
| 跳过 header | `TBLPROPERTIES ("skip.header.line.count"="1")` | COPY INTO 时用 `OPTIONS ('header'='true')` |

### SerDe 配置

```sql
-- Hive：OpenCSVSerde
CREATE EXTERNAL TABLE t (...)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\"",
    "escapeChar"    = "\\"
)
STORED AS TEXTFILE
TBLPROPERTIES ("skip.header.line.count"="1");

-- Lakehouse：无 SerDe 概念，在 COPY INTO 时指定格式
-- 建表只需声明列，不需要任何格式配置
CREATE TABLE t (col1 STRING, col2 BIGINT, ...);
```

## 数据加载

### LOAD DATA → COPY INTO

```sql
-- Hive：从本地文件系统加载到 EXTERNAL TABLE
LOAD DATA LOCAL INPATH '/tmp/data/file.csv'
OVERWRITE INTO TABLE staging_table;

-- Lakehouse：从 Named Volume 加载
COPY INTO target_table
FROM VOLUME schema_name.volume_name
USING CSV
OPTIONS ('header' = 'true', 'nullValue' = '')
FILES ('path/to/file.csv')
ON_ERROR = CONTINUE;
```

**关键差异**：
- Hive `LOAD DATA` 支持任意列变换（通过 staging 表 + INSERT SELECT）
- Lakehouse `COPY INTO` 按列顺序直接映射，不支持 `$1` 列引用或计算列
- 需要计算列（如从 `event_time` 提取 `dt`）时，先 COPY INTO 无分区 staging 表，再 INSERT INTO 分区主表

### 动态分区写入

```sql
-- Hive：必须先 SET，否则报错
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
INSERT OVERWRITE TABLE t PARTITION (dt)
SELECT ..., dt FROM src;

-- Lakehouse：直接写，无需任何 SET
INSERT OVERWRITE TABLE t PARTITION (dt)
SELECT ..., dt FROM src;
```

## ETL 函数

以下函数在 Hive 和 Lakehouse 中语法完全一致，直接复用：

### 字符串处理

```sql
-- 正则替换（去掉时区后缀）
REGEXP_REPLACE(event_time, ' UTC$', '')   -- 两侧完全一致

-- 字符串分割
SPLIT(category_code, '\\.')               -- 两侧完全一致
SPLIT(category_code, '\\.')[0]            -- 取第一段，两侧完全一致
SIZE(SPLIT(category_code, '\\.'))         -- 获取分段数，两侧完全一致

-- 子字符串
SUBSTR(event_time, 1, 10)                 -- 两侧完全一致
```

### 类型转换

```sql
-- Hive
CAST(col AS BIGINT)

-- Lakehouse：支持 CAST，同时支持 TRY_CAST（失败返回 NULL，Hive 不支持）
CAST(col AS BIGINT)      -- 失败报错（与 Hive 一致）
TRY_CAST(col AS BIGINT)  -- 失败返回 NULL（Lakehouse 扩展，推荐用于 COPY INTO）
```

### 条件聚合

```sql
-- 两侧完全一致
SUM(CASE WHEN event_type = 'purchase' THEN price ELSE 0 END)
COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END)
```

### 窗口函数

```sql
-- 两侧完全一致
RANK() OVER (ORDER BY purchase_amt DESC)
ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_ts)
```

## 已知陷阱

### 陷阱 1：OpenCSVSerde 列偏移

**现象**：CSV 中有连续空字段（如 `brand` 为空，出现 `,,`）时，OpenCSVSerde 解析会导致后续列向左偏移。

**示例**：
```
2019-10-01,view,28719074,...,apparel.shoes.keds,,35.79,541312140,...
```
`brand` 为空 → `price=35.79` 被读成 `user_id`，`user_id=541312140` 被读成 `user_session`。

**Hive 处理**：在 INSERT INTO ODS 时过滤异常 `user_id`：
```sql
WHERE CAST(user_id AS BIGINT) > 100000
```

**Lakehouse 处理**：COPY INTO 使用 `ON_ERROR=CONTINUE` 跳过格式错误行，同样在 INSERT 时过滤：
```sql
WHERE user_id > 100000
```

### 陷阱 2：Hive 4.0 分桶表 GROUP BY 返回空

**现象**：Hive 4.0 + Tez 引擎下，对 `CLUSTERED BY` 分桶 ORC 表执行 `GROUP BY` 查询返回空结果，但 `COUNT(*)` 走 metadata stats 返回正确行数。

**根因**：`CombineHiveInputFormat`（默认）在分桶 ORC 表上的执行计划有 bug。

**Hive 临时解决**：
```sql
SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;
```

**Lakehouse 影响**：无此问题。Lakehouse 同样支持 `CLUSTERED BY ... INTO N BUCKETS` 分桶，但不存在这个 bug，GROUP BY 正常工作。

### 陷阱 3：COPY INTO 不支持列引用语法

**现象**：Lakehouse COPY INTO 不支持 Snowflake 风格的 `$1`、`$2` 列引用：
```sql
-- 报错：Syntax error at or near '$'
COPY INTO t FROM (SELECT $1, $2 FROM VOLUME ...)
```

**正确做法**：使用 `FROM VOLUME ... USING CSV OPTIONS (...) FILES (...)` 语法，按列顺序直接映射。需要列变换时，先 COPY INTO 无分区 staging 表，再 INSERT INTO 目标表。

### 陷阱 4：动态分区默认行为差异

| 行为 | Hive | Lakehouse |
|------|------|-----------|
| 动态分区开关 | 默认关闭，需 `SET hive.exec.dynamic.partition=true` | 默认开启 |
| 严格模式 | 默认严格（至少一个静态分区），需 `SET ... mode=nonstrict` | 无此限制 |
| 分桶写入 | 需 `SET hive.enforce.bucketing=true` | 默认支持，无需 SET |
