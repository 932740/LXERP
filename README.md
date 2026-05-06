# LXERP 领星ERP自动化工具集

一套用于自动化处理领星ERP日常运营任务的Python脚本集合，支持亚马逊、eBay多平台运营数据管理。

[English](#lxerp-lingxing-erp-automation-toolkit) | 中文

---

## 功能模块

### 📦 订单与发货
- **获取FBA发货单** / FBA Shipment Fetcher - 自动抓取FBA发货单数据

### 📧 客户服务
- **24小时推送邮件** / 24-Hour Email Pusher - 监控并推送未处理邮件
- **24小时站内信** / 24-Hour Message Pusher - 监控未回复站内信并推送至钉钉

### ⭐ 评价管理
- **Review差评监控** / Negative Review Monitor - 自动获取Review中差评并推送至钉钉
- **Feedback差评监控** / Negative Feedback Monitor - 自动获取Feedback中差评并推送至钉钉

### 🛒 销售数据
- **Amazon列表管理** / Amazon Listing Manager - 亚马逊商品列表管理
- **ASIN日报** / ASIN Daily Report - 每日ASIN数据跟踪
- **eBay数据管理** / eBay Data Manager - eBay平台数据处理

### ⚠️ 预警通知
- **店铺异常监控** / Store Health Monitor - 监控店铺异常状态并推送至钉钉

## 技术栈 | Tech Stack
- **Python 3** - 主要开发语言
- **钉钉机器人** / DingTalk Bot - 企业级消息推送

## 快速开始 | Quick Start

### 环境要求
- Python 3.7+
- 领星ERP账号

### 配置说明
1. 配置领星ERP登录凭证
2. 配置钉钉机器人Webhook（用于接收通知）
3. 根据需要修改各脚本中的参数


## 项目结构 | Project Structure

```
LXERP/
├── Amazon_list.py              # 亚马逊列表
├── asinDaily_list.py           # ASIN日报
├── ebay.py                     # eBay数据
├── Windows批量执行脚本.bat      # Windows批量执行
├── 获取FBA发货单/               # FBA发货单
├── 获取24小时推送邮件/          # 邮件监控
├── 获取24小时站内信未回复并推送钉钉/  # 站内信监控
├── 获取Review中差评并推送至钉钉/    # Review差评
├── 获取feedback中差评并推送至钉钉/  # Feedback差评
├── 获取店铺异常信息并推送至钉钉/    # 店铺异常
└── 获取系统token/              # 系统Token
```

## 许可证 | License

MIT License

---

# LXERP Lingxing ERP Automation Toolkit

A Python script collection for automating daily Lingxing ERP operations, supporting Amazon and eBay multi-platform seller operations.

## Features

### 📦 Orders & Fulfillment
- **FBA Shipment Fetcher** - Automatically fetch FBA shipment data

### 📧 Customer Service
- **24-Hour Email Pusher** - Monitor and push unprocessed emails
- **24-Hour Message Pusher** - Monitor unread messages and push to DingTalk

### ⭐ Review Management
- **Negative Review Monitor** - Auto-fetch negative reviews and push to DingTalk
- **Negative Feedback Monitor** - Auto-fetch negative feedback and push to DingTalk

### 🛒 Sales Data
- **Amazon Listing Manager** - Amazon product listing management
- **ASIN Daily Report** - Daily ASIN data tracking
- **eBay Data Manager** - eBay platform data processing

### ⚠️ Alerts & Notifications
- **Store Health Monitor** - Monitor store anomalies and push to DingTalk

## Tech Stack
- **Python 3** - Primary language
- **DingTalk Bot** - Enterprise notification

## Quick Start

### Requirements
- Python 3.7+
- Lingxing ERP account

### Configuration
1. Configure Lingxing ERP credentials
2. Configure DingTalk bot webhook for notifications
3. Modify parameters in scripts as needed


## Project Structure

```
LXERP/
├── Amazon_list.py              # Amazon Listing
├── asinDaily_list.py           # ASIN Daily Report
├── ebay.py                     # eBay Data
├── Windows批量执行脚本.bat      # Windows Batch Runner
├── 获取FBA发货单/               # FBA Shipment
├── 获取24小时推送邮件/          # Email Monitor
├── 获取24小时站内信未回复并推送钉钉/  # Message Monitor
├── 获取Review中差评并推送至钉钉/    # Negative Reviews
├── 获取feedback中差评并推送至钉钉/  # Negative Feedback
├── 获取店铺异常信息并推送至钉钉/    # Store Alerts
└── 获取系统token/              # System Token
```

## License

MIT License
