const API_BASE_URL = "http://127.0.0.1:8000";

const textInput = document.getElementById("text");
const sourceInput = document.getElementById("source");
const submitButton = document.getElementById("submit");
const resultBox = document.getElementById("result");

function setResult(message) {
  resultBox.textContent = message;
}

async function submitTranslateTask() {
  const text = textInput.value.trim();
  const sourceDeclaration = sourceInput.value.trim();

  if (!text) {
    setResult("请输入文本");
    return;
  }

  if (!sourceDeclaration) {
    setResult("请输入来源声明");
    return;
  }

  setResult("提交中...");

  try {
    const response = await fetch(`${API_BASE_URL}/tasks/translate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text,
        source_declaration: sourceDeclaration
      })
    });

    const payload = await response.json();
    if (!response.ok) {
      setResult(`请求失败: ${payload.detail || response.status}`);
      return;
    }

    setResult(JSON.stringify(payload, null, 2));
  } catch (error) {
    setResult(`网络错误: ${error}`);
  }
}

submitButton.addEventListener("click", submitTranslateTask);
