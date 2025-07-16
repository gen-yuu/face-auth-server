document.addEventListener("DOMContentLoaded", () => {
  // WebSocketを優先的に使用する設定でサーバーに接続
  const socket = io("/live", {
    transports: ["websocket"],
  });

  const overlay = document.getElementById("overlay");
  const video = document.getElementById("video-stream");

  socket.on("connect", () => console.log("認証サーバーに接続しました。"));
  socket.on("disconnect", () =>
    console.log("認証サーバーから切断されました。")
  );
  socket.on("connect_error", (err) => {
    console.error("接続エラー:", err);
  });

  socket.on("faces_update", (data) => {
    console.log("受信データ:", data);
    // requestAnimationFrameを使ってスムーズな描画を行う
    requestAnimationFrame(() => {
      overlay.innerHTML = "";
      if (!video.naturalWidth || video.naturalWidth === 0) {
        // 映像の元サイズが取得できない場合は描画しない
        return;
      }
      // 映像の表示サイズと元サイズの比率を計算
      const scaleX = video.clientWidth / video.naturalWidth;
      const scaleY = video.clientHeight / video.naturalHeight;

      data.faces.forEach((face) => {
        const box = document.createElement("div");
        box.className = "face-box";
        box.style.left = `${face.x * scaleX}px`;
        box.style.top = `${face.y * scaleY}px`;
        box.style.width = `${face.w * scaleX}px`;
        box.style.height = `${face.h * scaleY}px`;

        const label = document.createElement("div");
        label.className = "face-label";
        label.textContent = face.id;

        box.appendChild(label);
        overlay.appendChild(box);
      });
    });
  });

  video.onerror = () => {
    console.error("映像ストリームの読み込みに失敗しました。");
    video.alt =
      "映像ストリームの読み込みに失敗しました。Raspberry Pi側の設定とURLを確認してください。";
  };
});
