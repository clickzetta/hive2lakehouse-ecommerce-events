# 迁移概述

本项目将一个典型的 Hive 电商数仓迁移到 ClickZetta Lakehouse，覆盖 ODS → DWD → DWS → ADS 四层架构。

## 整体结论

**迁移工作量中等，主要改动集中在存储格式声明和数据加载方式。** DML 逻辑（SELECT / JOIN / GROUP BY / 窗口函数）与 Hive 高度兼容，几乎不需要修改。改动集中在 5 个已知差异点。

## 迁移前后对比

| 层 | Hive 实现 | Lakehouse 实现 |
|----|-----------|---------------|
| ODS | EXTERNAL TABLE + OpenCSVSerde + TEXTFILE staging | 普通表 + COPY INTO FROM VOLUME |
| DWD | CLUSTERED BY 分桶 + ORC + 动态分区（需 SET） | 普通分区表（无分桶，可加 Z-Order 索引） |
| DWS | ORC 分区表 | 分区表（无需声明格式） |
| ADS | ORC 分区表 | 分区表（无需声明格式） |

## 5 个必须修改的地方

### 1. 存储格式声明

Hive 需要显式声明存储格式，Lakehouse 原生 Parquet，无需声明。

```sql
-- Hive
CREATE TABLE t (...)
STORED AS ORC
TBLPROPERTIES ("orc.compress"="SNAPPY");

-- Lakehouse（去掉即可）
CREATE TABLE t (...);
```

### 2. 数据加载方式

Hive 用 `LOAD DATA` + staging 表，Lakehouse 用 `COPY INTO FROM VOLUME`。

```sql
-- Hive：两步
LOAD DATA LOCAL INPATH '/path/file.csv' INTO TABLE staging;
INSERT INTO ods_raw SELECT ..., SUBSTR(event_time,1,10) AS dt FROM staging;

-- Lakehouse：同样两步，但语法不同
-- COPY INTO 不支持计算列（如提取 dt），需要先 COPY INTO staging，再 INSERT INTO 分区表
COPY INTO staging FROM VOLUME schema.vol_name
USING CSV OPTIONS ('header'='true') FILES ('file.csv') ON_ERROR=CONTINUE;
INSERT INTO ods_raw PARTITION (dt) SELECT ..., SUBSTR(event_time,1,10) FROM staging;
```

### 3. 分桶表替换

Hive 分桶表在 Lakehouse 中没有对应概念，改用 Z-Order 索引加速同等查询。

```sql
-- Hive
SET hive.enforce.bucketing=true;
CREATE TABLE dwd (...)
CLUSTERED BY (user_id) INTO 8 BUCKETS
STORED AS ORC;

-- Lakehouse：去掉分桶，建表后加 Z-Order 索引
CREATE TABLE dwd (...) PARTITIONED BY (dt STRING);
CREATE INDEX dwd_zorder ON dwd USING ZORDER (user_id);
```

### 4. 动态分区 SET 语句

Hive 动态分区需要显式开启，Lakehouse 默认支持，删除所有相关 SET 语句。

```sql
-- Hive（必须）
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
SET hive.enforce.bucketing=true;

-- Lakehouse：直接删除，无需任何 SET
```

### 5. SerDe 配置

Hive 解析 CSV 需要配置 SerDe，Lakehouse 在 COPY INTO 的 OPTIONS 里指定，更简洁。

```sql
-- Hive
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ("separatorChar"=",", "quoteChar"="\"")
STORED AS TEXTFILE
TBLPROPERTIES ("skip.header.line.count"="1");

-- Lakehouse
USING CSV OPTIONS ('header'='true', 'nullValue'='')
```

## 完全兼容的部分（无需修改）

以下 Hive SQL 语法在 Lakehouse 中直接运行，无需任何修改：

- `SELECT / WHERE / GROUP BY / ORDER BY / HAVING`
- `JOIN`（INNER / LEFT / RIGHT / FULL）
- `PARTITIONED BY (dt STRING)` 分区表语法
- `INSERT OVERWRITE TABLE ... PARTITION (dt)` 动态分区写入
- `REGEXP_REPLACE` / `SPLIT` / `SIZE` / `SUBSTR` 字符串函数
- `CAST` / `TRY_CAST` 类型转换
- `NULLIF` / `COALESCE` / `CASE WHEN`
- `COUNT(DISTINCT ...)` / `SUM(CASE WHEN ...)` 条件聚合
- `RANK() OVER (ORDER BY ...)` 窗口函数
- `ROUND` / `CONCAT` / `TRIM` 等常用函数

## 迁移工作量估算

| 类型 | 工作量 | 说明 |
|------|--------|------|
| DDL 改写 | 低 | 删除 STORED AS / CLUSTERED BY / TBLPROPERTIES |
| 数据加载改写 | 中 | LOAD DATA → COPY INTO，语法结构不同 |
| ETL SQL 改写 | 低 | 删除 SET 语句，其余不变 |
| 分析查询改写 | 极低 | 基本不需要改动 |
| UDF 替换 | 视情况 | 本项目未使用自定义 UDF |
