/* static/script.js */
const alarmSound = document.getElementById("alarmSound");
const statusPanel = document.getElementById("statusPanel");
const statusText = document.getElementById("statusText");

let isPlaying = false;

// Yêu cầu người dùng tương tác lần đầu để trình duyệt cho phép phát âm thanh
document.body.addEventListener('click', function() {
    if(alarmSound.paused) {
        alarmSound.play().then(() => {
            alarmSound.pause();
            alarmSound.currentTime = 0;
        }).catch(e => console.log("Lỗi khởi tạo audio:", e));
    }
}, { once: true });

// Vòng lặp lấy trạng thái từ server
setInterval(async () => {
    try {
        const response = await fetch('/status');
        const data = await response.json();

        if (data.alarm === true) {
            statusPanel.classList.add("alarm-active");
            statusText.innerText = "CẢNH BÁO: ĐANG NGỦ GẬT !!!";
            
            if (!isPlaying) {
                alarmSound.play();
                isPlaying = true;
            }
        } else {
            statusPanel.classList.remove("alarm-active");
            statusText.innerText = "TRẠNG THÁI: BÌNH THƯỜNG";
            
            if (isPlaying) {
                alarmSound.pause();
                alarmSound.currentTime = 0;
                isPlaying = false;
            }
        }
    } catch (error) {
        console.error("Mất kết nối tới máy chủ:", error);
        statusText.innerText = "MẤT KẾT NỐI CAMERA";
        statusText.style.color = "orange";
    }
}, 500);