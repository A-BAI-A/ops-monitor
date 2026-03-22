import requests
import pymysql
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── 配置区 ──────────────────────────
PROMETHEUS = "http://localhost:9090"

DB = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "bai1949",
    "database": "ops_monitor",
    "charset": "utf8mb4"
}

SMTP = {
    "host": "smtp.zoho.com",
    "port": 465,
    "user": "bai@lntu.tech",
    "password": "1kvNwExvngEj",
    "to": "bai@lntu.tech"
}

THRESHOLDS = {"cpu": 80.0, "memory": 75.0, "disk": 85.0}
# ────────────────────────────────────

def query(promql):
    try:
        r = requests.get(f"{PROMETHEUS}/api/v1/query",
                        params={"query": promql}, timeout=5)
        results = r.json()["data"]["result"]
        return float(results[0]["value"][1]) if results else 0.0
    except Exception as e:
        print(f"查询失败: {e}")
        return 0.0

def write_metric(cur, server_id, cpu, mem, disk):
    cur.execute("""
        INSERT INTO metric_record (server_id, cpu_percent, mem_percent, disk_percent)
        VALUES (%s, %s, %s, %s)
    """, (server_id, round(cpu, 2), round(mem, 2), round(disk, 2)))

def write_alert(cur, server_id, alert_type, value, threshold):
    cur.execute("""
        INSERT INTO alert_log (server_id, alert_type, metric_value, threshold)
        VALUES (%s, %s, %s, %s)
    """, (server_id, alert_type, round(value, 2), threshold))

def send_email(subject, alerts):
    body = f"告警时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    body += "\n".join(f"  · {a}" for a in alerts)
    body += "\n\n请登录 Grafana 查看详情：https://grafana.lntu.tech"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"]    = SMTP["user"]
    msg["To"]      = SMTP["to"]
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL(SMTP["host"], SMTP["port"]) as s:
        s.login(SMTP["user"], SMTP["password"])
        s.send_message(msg)
    print(f"邮件已发送：{subject}")

def check():
    conn = pymysql.connect(**DB)
    alerts = []

    try:
        with conn.cursor() as cur:
            # ── Linux VM ──
            cpu  = query('100 - avg(rate(node_cpu_seconds_total{job="linux-vm",mode="idle"}[5m]))*100')
            mem  = query('(1 - node_memory_MemAvailable_bytes{job="linux-vm"} / node_memory_MemTotal_bytes{job="linux-vm"})*100')
            disk = query('(1 - node_filesystem_avail_bytes{job="linux-vm",mountpoint="/"} / node_filesystem_size_bytes{job="linux-vm",mountpoint="/"})*100')

            write_metric(cur, 1, cpu, mem, disk)
            print(f"Linux  → CPU:{cpu:.1f}% 内存:{mem:.1f}% 磁盘:{disk:.1f}%")

            if cpu  > THRESHOLDS["cpu"]:
                alerts.append(f"Linux CPU {cpu:.1f}% 超过阈值 {THRESHOLDS['cpu']}%")
                write_alert(cur, 1, "cpu", cpu, THRESHOLDS["cpu"])
            if mem  > THRESHOLDS["memory"]:
                alerts.append(f"Linux 内存 {mem:.1f}% 超过阈值 {THRESHOLDS['memory']}%")
                write_alert(cur, 1, "memory", mem, THRESHOLDS["memory"])
            if disk > THRESHOLDS["disk"]:
                alerts.append(f"Linux 磁盘 {disk:.1f}% 超过阈值 {THRESHOLDS['disk']}%")
                write_alert(cur, 1, "disk", disk, THRESHOLDS["disk"])

            # ── Windows VM ──
            win_cpu  = query('100 - avg(rate(windows_cpu_time_total{job="windows-vm",mode="idle"}[5m]))*100')
            win_disk = query('(1 - windows_logical_disk_free_bytes{job="windows-vm",volume="C:"} / windows_logical_disk_size_bytes{job="windows-vm",volume="C:"})*100')

            write_metric(cur, 2, win_cpu, 0, win_disk)
            print(f"Windows → CPU:{win_cpu:.1f}% 磁盘:{win_disk:.1f}%")

            if win_cpu  > THRESHOLDS["cpu"]:
                alerts.append(f"Windows CPU {win_cpu:.1f}% 超过阈值 {THRESHOLDS['cpu']}%")
                write_alert(cur, 2, "cpu", win_cpu, THRESHOLDS["cpu"])
            if win_disk > THRESHOLDS["disk"]:
                alerts.append(f"Windows C盘 {win_disk:.1f}% 超过阈值 {THRESHOLDS['disk']}%")
                write_alert(cur, 2, "disk", win_disk, THRESHOLDS["disk"])

        conn.commit()

    finally:
        conn.close()

    if alerts:
        send_email("【运维告警】" + " | ".join(alerts[:2]), alerts)
    else:
        print(f"{datetime.now().strftime('%H:%M:%S')} 检查完毕，一切正常")

if __name__ == "__main__":
    check()
