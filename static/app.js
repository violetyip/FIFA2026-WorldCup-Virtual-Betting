// FIFA 2026 虚拟赌球模拟器 - 前端交互

document.addEventListener('DOMContentLoaded', function() {
    // 自动关闭 flash 消息
    setTimeout(function() {
        document.querySelectorAll('.alert-dismissible').forEach(function(el) {
            var bsAlert = new bootstrap.Alert(el);
            bsAlert.close();
        });
    }, 5000);

    // 数字输入框限制
    document.querySelectorAll('input[type="number"]').forEach(function(input) {
        input.addEventListener('input', function() {
            var max = parseFloat(this.max);
            var min = parseFloat(this.min);
            var val = parseFloat(this.value);
            if (!isNaN(max) && val > max) this.value = max;
            if (!isNaN(min) && val < min) this.value = min;
        });
    });

    // 表格行悬停高亮
    document.querySelectorAll('.table tbody tr').forEach(function(row) {
        row.style.cursor = 'pointer';
    });
});
