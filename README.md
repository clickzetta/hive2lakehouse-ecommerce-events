# hive2lakehouse-ecommerce-events

> Hive → ClickZetta Lakehouse 迁移示例，以电商用户行为日志分析为载体。

本项目 fork 自 [Kaggle E-Commerce Events](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop) 数据集，在 Hive 4.0 Docker 环境中实现了完整的 ODS → DWD → DWS → ADS 四层数仓，并迁移到 ClickZetta Lakehouse，完成了端到端验证（**10/10 验证项全部通过**）。

---

## 迁移总结

### 整体结论

**迁移工作量中等，主要改动集中在存储格式和 UDF 替换。** Hive SQL 的 DML 语法（SELECT/JOIN/GROUP BY/窗口函数）与 Lakehouse 高度兼容，改动集中在 4 个已知差异点。

### 核心差异

| 类别 | Hive | Lakehouse | 迁移方式 |
|------|------|-----------|---------|
| 存储格式 | ORC / Parquet + SerDe | 原生 Parquet（无需声明） | 去掉 `STORED AS`、`ROW FORMAT` |
| 分区表 | `PARTITIONED BY (dt STRING)` + `MSCK REPAIR` | `PARTITIONED BY (dt STRING)` | 语法兼容，去掉 `MSCK REPAIR` |
| 分桶表 | `CLUSTERED BY ... INTO N BUCKETS` | 不支持，改用 Z-Order 索引 | 重写为 `CREATE INDEX ... ZORDER` |
| UDF | Java `GenericUDF` | 内置函数替代 | 逐一映射到内置函数 |
| 动态分区 | `SET hive.exec.dynamic.partition=true` | 默认支持，无需 SET | 删除 SET 语句 |
| `LOAD DATA INPATH` | 从 HDFS 加载 | `COPY INTO` 从 Volume 加载 | 改写加载语句 |

---

## 项目结构

```
hive2lakehouse-ecommerce-events/
├── 01_hive/                     # 原始 Hive 代码（可在 Docker 容器中运行）
│   ├── ddl/                     #   建表语句（分区表、分桶表、ORC 格式）
│   ├── etl/                     #   数据加载与转换
│   └── analysis/                #   分析查询（PV/UV、漏斗、用户路径）
├── 02_migration/                # 迁移说明文档
│   ├── 01_overview.md           #   迁移策略与关键差异
│   └── 02_syntax_mapping.md     #   Hive ↔ Lakehouse 语法对照
├── 03_lakehouse/                # ✅ Lakehouse 迁移后代码
│   ├── sql/                     #   迁移后的 SQL（可用 cz-cli 运行）
│   ├── includes/                #   配置常量
│   ├── setup.py                 #   一键初始化（建 Schema、Volume，上传数据）
│   └── e2e.py                   #   端到端验证
├── data/
│   └── sample/                  #   小型示例数据（可直接 git 提交，用于快速验证）
├── datasets/                    #   完整数据集（.gitignore，运行时下载）
├── .env.sample                  #   连接配置模板
└── README.md
```

---

## 数据架构

| 层 | 表 | 说明 |
|----|----|------|
| ODS | `ods_events_raw` | 原始事件日志，按日期分区，ORC 格式 |
| DWD | `dwd_events_clean` | 清洗后事件，去除无效记录，分桶加速 JOIN |
| DWS | `dws_user_behavior` | 用户行为汇总（日粒度） |
| ADS | `ads_funnel_daily` | 每日漏斗转化率（view→cart→purchase） |

---

## 快速开始

### 前置条件

- Docker（运行 Hive 验证环境）
- Python 3.10+（运行 Lakehouse 迁移代码）
- ClickZetta Lakehouse 账号（[免费注册](https://www.yunqi.tech)）

### 启动 Hive 验证环境

```bash
docker run -d --name hive-dev \
  -e SERVICE_NAME=hiveserver2 \
  -p 10000:10000 \
  apache/hive:4.0.1

# 等待约 15 秒后验证
docker exec hive-dev beeline -u 'jdbc:hive2://localhost:10000/' -e "SHOW DATABASES;"
```

### 运行 Hive 原始代码

```bash
# 建表
docker exec hive-dev beeline -u 'jdbc:hive2://localhost:10000/' -f /path/to/01_hive/ddl/01_create_tables.sql

# 加载数据
docker exec hive-dev beeline -u 'jdbc:hive2://localhost:10000/' -f /path/to/01_hive/etl/01_load_data.sql
```

### 运行 Lakehouse 迁移代码

```bash
pip install clickzetta_zettapark_python python-dotenv
cp .env.sample .env
# 编辑 .env 填写连接信息

cd 03_lakehouse
python setup.py
python e2e.py
```

---

## 原始数据

- 来源：[Kaggle - eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop)
- 格式：CSV，字段：`event_time, event_type, product_id, category_id, category_code, brand, price, user_id, user_session`
- 覆盖：2019 年 10 月（约 280 万行）、11 月（约 370 万行）
- License：CC0 Public Domain
