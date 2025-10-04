// 显示提示消息
function showAlert(message, type = 'info') {
    // 颜色配置（可以按需要改）
    const colors = {
        success: {bg: '#d4edda', text: '#155724', border: '#c3e6cb'},
        danger: {bg: '#f8d7da', text: '#721c24', border: '#f5c6cb'},
        warning: {bg: '#fff3cd', text: '#856404', border: '#ffeeba'},
        info: {bg: '#d1ecf1', text: '#0c5460', border: '#bee5eb'}
    };

    const style = colors[type] || colors.info;

    // 创建提示元素
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        padding: 10px 15px;
        margin-bottom: 10px;
        border: 1px solid ${style.border};
        border-radius: 4px;
        background-color: ${style.bg};
        color: ${style.text};
        font-size: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        display: flex;
        justify-content: space-between;
        align-items: center;
        opacity: 1;
        transition: opacity 0.5s ease;
    `;

    // 设置内容
    alertDiv.innerHTML = `
        <span>${message}</span>
        <span style="cursor:pointer; font-weight:bold; margin-left:10px;">&times;</span>
    `;

    // 关闭按钮
    const closeBtn = alertDiv.querySelector("span:last-child");
    closeBtn.onclick = () => {
        alertDiv.style.opacity = "0";
        setTimeout(() => alertDiv.remove(), 500);
    };

    document.body.appendChild(alertDiv);

    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.style.opacity = "0";
            setTimeout(() => alertDiv.remove(), 500);
        }
    }, 3000);
}

function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return "";
    // 先去掉时区部分（+08:00 或 Z），如果有
    let cleanStr = dateTimeStr.split("+")[0].split("Z")[0];
    // 如果有 "T"，替换成空格
    cleanStr = cleanStr.replace("T", " ");
    // 去掉秒，只保留 yyyy-MM-dd HH:mm
    return cleanStr.slice(0, 16)
}

function progress(done_times, repeat_times) {
    let _progress;
    if (repeat_times > 0) {
        _progress = `${done_times}/${repeat_times}`;
    } else {
        _progress = `${done_times}`;
    }
    return _progress
}

function repeatTypeStr(repeat_type, repeat_interval) {
    if (repeat_interval < 0) return "无";

    let typeStr;
    switch (repeat_type) {
        case "days":
            typeStr = "天";
            break;
        case "weeks":
            typeStr = "周";
            break;
        case "months":
            typeStr = "月";
            break;
        case "years":
            typeStr = "年";
            break;
        default:
            return "无";
    }

    if (repeat_interval === 0) {
        return `每${typeStr}`;
    } else {
        return `间隔${repeat_interval}${typeStr}`;
    }
}

function advanceDaysStr(advance_days) {
    if (!advance_days || advance_days.length === 0) return "不提醒";
    return `提前${advance_days.join(",")}天`;
}

function currentAdvanceStatusStr(current_advance_status) {
    if (!current_advance_status || Object.keys(current_advance_status).length === 0) return "-";

    // 按 key 升序显示
    return Object.keys(current_advance_status)
        .sort((a, b) => Number(a) - Number(b))
        .map(day => `提前${day}天:${current_advance_status[day] ? "√" : "×"}`)
        .join("; ");
}
