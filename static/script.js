const statusPanel = document.getElementById('statusPanel');
const statusText = document.getElementById('statusText');
const alarmSound = document.getElementById('alarmSound');
const muteBtn = document.getElementById('muteBtn');
const testBtn = document.getElementById('testAlarmBtn');

let isMuted = false;

// Xử lý nút Mute
muteBtn.addEventListener('click', () => {
    isMuted = !isMuted;
    muteBtn.innerText = isMuted ? "Bật Âm" : "Tắt Âm";
    if (isMuted) alarmSound.pause();
});

// Xử lý nút Test còi
testBtn.addEventListener('mousedown', () => alarmSound.play());
testBtn.addEventListener('mouseup', () => { if(!isAlarming) alarmSound.pause(); });

let isAlarming = false;

function updateStatus() {
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            isAlarming = data.alarm;
            
            // Cập nhật giao diện dựa trên alarm
            if (isAlarming) {
                statusPanel.className = "status-card status-danger";
                statusText.innerText = "NGUY HIỂM: NGỦ GẬT!";
                if (!isMuted) alarmSound.play();
            } else {
                statusPanel.className = "status-card status-normal";
                statusText.innerText = "BÌNH THƯỜNG";
                alarmSound.pause();
            }

            // Gán các giá trị thông số (Nếu bạn cập nhật API /status ở Python)
            if(data.ear) document.getElementById('earVal').innerText = data.ear.toFixed(2);
            if(data.mar) document.getElementById('marVal').innerText = data.mar.toFixed(2);
        });
}

setInterval(updateStatus, 200); // Cập nhật mỗi 200ms