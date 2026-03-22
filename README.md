# 跨平台异构监控系统与 MySQL 性能调优实践

基于 Prometheus + Grafana，在两台 Azure 云服务器（Linux + Windows）上实现跨平台异构监控，集成 MariaDB 性能采集与索引优化实验，Python 告警脚本实现无人值守监控闭环。

## 架构概览
```
用户浏览器
    ↓ HTTPS
Cloudflare（SSL + Tunnel）
    ↓
Azure Linux VM（主控节点）
├── Flarum 论坛（现有服务）
├── MariaDB（数据库）
├── Nginx（反向代理）
├── Prometheus（指标采集，15s 间隔）
├── Grafana（可视化，grafana.lntu.tech）
├── Node Exporter（Linux 指标 :9100）
├── mysqld_exporter（MariaDB 指标 :9104）
└── Python 告警脚本（crontab 每5分钟）

Azure Windows VM（被监控节点，不同 VNet）
└── windows_exporter（Windows 指标）
    ↓ Cloudflare Tunnel（win-metrics.lntu.tech）
    ↑ Prometheus 主动拉取
```

## 技术要点

**跨 VNet 监控方案**

两台 VM 位于不同 Azure VNet，内网不通。通过 Cloudflare Tunnel 将 Windows 节点的 windows_exporter 暴露为 HTTPS 端点，Prometheus 通过域名拉取指标，无需公网 IP 或 VPN。

**告警设计决策**

未使用 Alertmanager，原因：当前场景需要将告警数据持久化到数据库做审计，Python 脚本通过 Prometheus HTTP API 查询指标，维护成本低于引入 Alertmanager。

## 监控指标

| 采集源 | 关键指标 |
|--------|---------|
| Linux VM | CPU、内存、磁盘、网络 I/O |
| Windows VM | CPU、内存、磁盘、服务状态 |
| MariaDB | QPS、连接数、InnoDB Buffer Pool、慢查询 |

## MySQL 索引优化实验

**实验环境**：MariaDB 10.11，orders 表 10 万条数据

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| EXPLAIN type | ALL（全表扫描） | fulltext / ref |
| 扫描行数（rows） | 99,835 | 1 ~ 17 |
| 使用索引（key） | NULL | ft_comment / idx_user_id |

**结论**：`LIKE '%keyword%'` 无法使用 B-Tree 索引，改用全文索引（FULLTEXT）后扫描行数从 99,835 降至 1，普通等值查询加索引后扫描行数从 99,835 降至 17。

## 告警阈值

| 指标 | 阈值 |
|------|------|
| CPU 使用率 | > 80% |
| 内存使用率 | > 75% |
| 磁盘使用率 | > 85% |

触发后自动发送邮件并写入 `ops_monitor.alert_log` 表。

## Grafana Dashboard

| 面板 | ID |
|------|-----|
| Node Exporter Full（Linux） | 1860 |
| MySQL Exporter Quickstart | 14057 |
| Windows Exporter Dashboard | 10467 |

## 部署说明
```bash
# 1. 克隆仓库
git clone https://github.com/A-BAI-A/ops-monitor.git
cd ops-monitor

# 2. 配置数据库监控账号
cp mysqld-exporter.cnf.example mysqld-exporter.cnf
# 编辑 mysqld-exporter.cnf，填入实际密码

# 3. 追加监控服务到现有 docker-compose.yml
cat monitoring-compose.yml >> /path/to/your/docker-compose.yml

# 4. 启动监控栈
docker compose up -d node-exporter mysqld-exporter prometheus grafana

# 5. 初始化运维日志数据库
docker exec -i mariadb mariadb -u root -p < ops_monitor.sql

# 6. 配置告警脚本
cp alert.py /home/user/alert.py
# 编辑 alert.py，填入 SMTP 密码和数据库密码
crontab -e
# 添加：*/5 * * * * python3 /home/user/alert.py >> /var/log/ops_alert.log 2>&1
```

## 项目文件
```
ops-monitor/
├── README.md
├── prometheus.yml          # Prometheus 采集配置
├── monitoring-compose.yml  # 监控服务 compose 片段
├── mysqld-exporter.cnf.example  # 数据库监控账号模板
├── alert.py                # Python 告警脚本
└── ops_monitor.sql         # 运维日志数据库建表语句
```
