const form = document.querySelector("#video-form");
const input = document.querySelector("#video-url");
const status = document.querySelector("#status");
const chat = document.querySelector("#chat");
const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const messages = document.querySelector("#messages");
let videoId = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.className = "";
  chat.classList.add("hidden");
  status.textContent = "جارٍ جلب النص وفهرسة الفيديو…";

  try {
    const response = await fetch("http://127.0.0.1:8000/api/video", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: input.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "تعذر فحص الرابط.");
    videoId = data.video_id;
    status.textContent = `${data.message} (${data.chunks} مقاطع)`;
    messages.innerHTML = "";
    chat.classList.remove("hidden");
  } catch (error) {
    status.className = "error";
    status.textContent = error.message.includes("fetch")
      ? "شغّل خادم FastAPI أولًا ثم حاول مجددًا."
      : error.message;
  }
});

function addMessage(kind, text, sources = []) {
  const element = document.createElement("article");
  element.className = `message ${kind}`;
  element.textContent = text;
  if (sources.length) {
    const sourceText = sources.map((source) => `[${source.timestamp}] ${source.text}`).join("\n");
    const details = document.createElement("div");
    details.className = "sources";
    details.textContent = sourceText;
    element.append(details);
  }
  messages.append(element);
  messages.scrollTop = messages.scrollHeight;
}

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!videoId || !question) return;
  addMessage("user", question);
  questionInput.value = "";
  questionInput.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, question }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "تعذر إنشاء الإجابة.");
    addMessage("assistant", data.answer, data.sources);
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    questionInput.disabled = false;
    questionInput.focus();
  }
});
