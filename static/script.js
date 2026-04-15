const statusPanel = document.getElementById("statusPanel");
const statusText = document.getElementById("statusText");
const alarmSound = document.getElementById("alarmSound");
const muteBtn = document.getElementById("muteBtn");
const testBtn = document.getElementById("testAlarmBtn");

let isMuted = false;

// Xử lý nút Mute (Tắt âm thanh rảnh tay)
muteBtn.addEventListener("click", () => {
  isMuted = !isMuted;
  muteBtn.innerText = isMuted ? "Bật Âm" : "Tắt Âm";
  // Nếu đang hú còi mà bấm Mute thì tắt ngay
  if (isMuted) alarmSound.pause();
});

// Xử lý nút Test còi
testBtn.addEventListener("click", async () => {
  try {
    // Tua lại từ đầu trước khi phát
    alarmSound.currentTime = 0;

    // Hàm play() trả về một Promise. Mình dùng await để bắt lỗi nếu trình duyệt chặn.
    await alarmSound.play();

    testBtn.innerText = "Đang Test...";
    testBtn.style.background = "#f44336"; // Bật đèn đỏ báo hiệu đang kêu

    // Kêu thử đúng 2 giây rồi tự tắt
    setTimeout(() => {
      if (!isAlarming) {
        alarmSound.pause();
      }
      testBtn.innerText = "Test Còi";
      testBtn.style.background = "#444"; // Tắt đèn đỏ
    }, 2000);
  } catch (err) {
    // Nếu trình duyệt chặn, nó sẽ báo lỗi ở đây
    console.error("Lỗi phát âm thanh (Trình duyệt chặn):", err);
    alert(
      "Trình duyệt đang chặn âm thanh! Vui lòng cho phép tự động phát âm thanh ở thanh địa chỉ góc trên bên phải.",
    );
  }
});

function updateStatus() {
  // Gọi API lấy dữ liệu từ Python
  fetch("/status")
    .then((response) => response.json())
    .then((data) => {
      isAlarming = data.alarm;

      // 1. XỬ LÝ GIAO DIỆN CẢNH BÁO
      if (isAlarming) {
        statusPanel.className = "status-card status-danger";
        statusText.innerText = "NGUY HIỂM: VI PHẠM!";
        if (!isMuted) alarmSound.play(); // Hú còi nếu chưa bị mute
      } else {
        statusPanel.className = "status-card status-normal";
        statusText.innerText = "BÌNH THƯỜNG";
        alarmSound.pause(); // Tắt còi
      }

      // 2. CẬP NHẬT 4 THÔNG SỐ LÊN MÀN HÌNH
      // Dùng !== undefined để tránh lỗi khi giá trị bằng 0
      if (data.ear !== undefined) {
        document.getElementById("earVal").innerText = data.ear.toFixed(2);
      }
      if (data.mar !== undefined) {
        document.getElementById("marVal").innerText = data.mar.toFixed(2);
      }
      if (data.pitch !== undefined) {
        document.getElementById("pitchVal").innerText =
          data.pitch.toFixed(0) + "°";
      }
      if (data.yaw !== undefined) {
        document.getElementById("yawVal").innerText = data.yaw.toFixed(0) + "°";
      }
    })
    .catch((error) => console.error("Lỗi mất kết nối với Python:", error));
}

// Chạy vòng lặp lấy dữ liệu siêu tốc (mỗi 100 mili-giây)
setInterval(updateStatus, 100);
