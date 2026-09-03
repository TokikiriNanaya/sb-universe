# 300宇宙自动签到

一个用于自动完成300宇宙每日任务的Python工具。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置Token

复制 `config_example.yaml` 为 `config.yaml` 并编辑：

```bash
cp config_example.yaml config.yaml
```

然后编辑 `config.yaml` 文件，填入你的 token：

```yaml
token: 你的token在这里
```

> **如何获取Token？** 见下方[获取Token](#-获取token)部分

### 3. 执行任务

```bash
python main.py
```

## 📋 功能列表

- Token验证
- 每日签到
- 月度累计签到奖励领取（3/7/15/28天）
- 游玩共鸣引擎并领取奖励
- 点赞帖子（每次点赞新发布的帖子）
- 评论帖子
- 发布/删除帖子
- 浏览帖子（失败自动重试）
- 关注任务（从社区帖子动态找不同作者关注，计数成功后即时取关，不固定骚扰同一用户）
- 查询战绩和历史战绩
- **任务驱动补足**（读取每日随机任务，自动补足未完成的动作次数）
- 动态领取任务奖励（自动识别今日可领取任务，批量领取）
- 购买道具
- 网络异常自动重试

## 🔑 获取Token

### 方法1: PC浏览器抓包（推荐）

⚠️ 注意：会与手机端互相顶号

1. 访问300宇宙 [https://300universe.tygms.com/](https://300universe.tygms.com/) 并登录
2. 按F12打开开发者工具
3. 依次点击 "应用" → "本地存储空间"，找到 `ClientToken`，复制value值

   ![Token位置](assets/img_1.png)
   
### 方法2: 手机抓包

使用HttpCanary等抓包工具（可能需要root权限）：

1. 打开HttpCanary，选择目标应用为"宅基地"
2. 开始抓包后打开宅基地APP
3. 执行任意操作（如点赞）
4. 在抓包记录中找到请求，查看token字段

![HttpCanary示例](assets/HttpCanary01.png)
![Token位置](assets/HttpCanary02.png)

## ⚙️ 配置说明

`config.yaml` 配置项：

```yaml
# ==================== 账号配置 ====================
accounts:
  - name: "账号1"              # 账号备注名称
    token: "你的token"
  
  # 添加更多账号（可选）
  # - name: "账号2"
  #   token: "第二个账号的token"

# ==================== 全局配置 ====================
api_base_url: "https://300zjd.tygms.cn/"  # API地址
monthly_signin_task_ids: [2001, 2002, 2003, 2004]  # 月度累计签到奖励ID (3/7/15/28天)
request_delay: 1.0               # 请求间隔(秒)
account_delay: 5.0               # 账号间延迟(秒)
timeout: 30                      # 请求超时(秒)
max_retries: 3                   # 网络请求/发帖/浏览失败重试次数
retry_delay: 5.0                 # 重试间隔(秒)
```

> 每日任务奖励无需配置：脚本会自动拉取服务器下发的当日任务并动态领取。
> 购买道具的商品ID/地址ID为固定值（26/0），已写入代码，无需配置。

## ⏰ 定时执行

### Linux/Mac (Crontab)

```bash
# 每小时执行一次
0 * * * * cd /path/to/sb-universe && python main.py >> logs/cron.log 2>&1
```

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务，设置触发器（如每小时）
3. 操作：启动程序 `python`，参数 `main.py`

### 青龙面板（推荐）

1. 上传项目到青龙面板
2. 创建定时任务
3. 命令：`python main.py`

## 📁 项目结构

```
sb-universe/
├── config_example.yaml  # 配置文件模板
├── config.yaml          # 你的配置文件（需自行创建，不纳入版本控制）
├── main.py              # 主程序入口 ⭐
│
├── config_manager.py    # 配置管理模块
├── logger.py           # 日志模块
├── api_client.py       # HTTP客户端模块
├── services.py         # 业务服务模块

├── requirements.txt    # 依赖包列表
└── README.md          # 说明文档
```

## 🏗️ 架构设计

采用分层架构：

```
main.py (表现层 - 任务编排)
    ↓
services.py (业务层 - 5个Service类)
    ↓
api_client.py (数据访问层 - HTTP请求)
    ↓
config_manager.py + logger.py (基础设施层)
```

**核心模块：**

- **config_manager.py**: 配置管理
- **logger.py**: 日志系统
- **api_client.py**: HTTP客户端
- **services.py**: 业务服务（UserService, PostService, SocialService, TaskService, StatsService）
- **main.py**: 任务执行器

## 💡 进阶使用

### 

### 添加新功能

1. 在 `services.py` 中添加Service方法
2. 在 `main.py` 中调用
3. 如需新配置，在 `config.yaml` 和 `config_manager.py` 中添加

详见代码注释和示例。

## 📝 更新日志

### v2.1.0 (2026-09-03)

- ✨ 关注任务重做：不再固定关注同一用户（改版后按"不同的人"计数，固定ID无效）
- ✨ 自动从社区帖子流寻找真实作者作为关注对象，每次不同人
- ✨ 每次关注后复查任务进度确认计数，随后即时取关，账号不残留关注
- 🗑️ 移除 `default_follow_id` 配置项与每日开场无条件关注/取关动作

### v2.0.0 (2026-05-27)

- ✨ 重构为模块化架构
- ✨ 添加完善的日志系统
- ✨ 统一错误处理机制
- ✨ 优化配置管理
- ✨ 添加类型注解
- ✨ 完善文档

### v1.0.0

- 初始版本，单文件实现

## 📄 许可证

本项目仅供学习交流使用，请勿用于商业用途。
