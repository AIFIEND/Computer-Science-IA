const entryForm = document.getElementById("entry-form");
const historyBody = document.getElementById("history-body");
const historyEmpty = document.getElementById("history-empty");
const saveStatus = document.getElementById("save-status");
const predictedScoreEl = document.getElementById("predicted-score");
const predictionNotesEl = document.getElementById("prediction-notes");

const predictInputs = {
  avg_glucose: document.getElementById("predict-avg-glucose"),
  glucose_sd: document.getElementById("predict-glucose-sd"),
  difficulty: document.getElementById("predict-difficulty"),
};

let scatterChart = null;
let predictTimeout = null;

const clearErrors = (prefix = "") => {
  document.querySelectorAll(".error").forEach((el) => {
    if (!prefix || el.dataset.errorFor?.startsWith(prefix)) {
      el.textContent = "";
    }
  });
};

const setErrors = (errors, prefix = "") => {
  Object.entries(errors).forEach(([field, message]) => {
    const el = document.querySelector(
      `.error[data-error-for="${prefix}${field}"]`
    );
    if (el) {
      el.textContent = message;
    }
  });
};

const formatNumber = (value) => {
  if (value === null || value === undefined) {
    return "--";
  }
  return Number(value).toFixed(1);
};

const formatDate = (value) => {
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value;
  }
};

const renderHistory = (entries) => {
  historyBody.innerHTML = "";
  if (!entries.length) {
    historyEmpty.style.display = "block";
    return;
  }
  historyEmpty.style.display = "none";

  entries.forEach((entry) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${formatDate(entry.created_at)}</td>
      <td>${formatNumber(entry.avg_glucose)}</td>
      <td>${formatNumber(entry.glucose_sd)}</td>
      <td>${formatNumber(entry.difficulty)}</td>
      <td>${formatNumber(entry.score)}</td>
    `;
    historyBody.appendChild(row);
  });
};

const renderChart = (entries) => {
  const dataPoints = entries.map((entry) => ({
    x: entry.avg_glucose,
    y: entry.score,
    difficulty: entry.difficulty,
    glucose_sd: entry.glucose_sd,
  }));

  const ctx = document.getElementById("scatter-chart");

  if (scatterChart) {
    scatterChart.data.datasets[0].data = dataPoints;
    scatterChart.update();
    return;
  }

  scatterChart = new Chart(ctx, {
    type: "scatter",
    data: {
      datasets: [
        {
          label: "Score vs Avg Glucose",
          data: dataPoints,
          backgroundColor: "rgba(37, 99, 235, 0.8)",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: (context) => {
              const point = context.raw;
              return `Avg glucose: ${point.x} | Score: ${point.y} | Difficulty: ${point.difficulty} | SD: ${point.glucose_sd}`;
            },
          },
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: "Average glucose (mg/dL)",
          },
        },
        y: {
          title: {
            display: true,
            text: "Score",
          },
          min: 0,
          max: 100,
        },
      },
    },
  });
};

const fetchEntries = async () => {
  const response = await fetch("/api/entries");
  const data = await response.json();
  renderHistory(data.entries);
  renderChart(data.entries);
  return data.entries;
};

const updatePrediction = async () => {
  clearErrors("predict_");
  const payload = {
    avg_glucose: predictInputs.avg_glucose.value,
    glucose_sd: predictInputs.glucose_sd.value,
    difficulty: predictInputs.difficulty.value,
  };

  if (!payload.avg_glucose || !payload.glucose_sd || !payload.difficulty) {
    predictedScoreEl.textContent = "--";
    predictionNotesEl.innerHTML = "";
    return;
  }

  const response = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();

  if (!response.ok) {
    const errors = {};
    Object.entries(data.errors || {}).forEach(([field, message]) => {
      errors[`predict_${field}`] = message;
    });
    setErrors(errors);
    predictedScoreEl.textContent = "--";
    predictionNotesEl.innerHTML = "";
    return;
  }

  predictedScoreEl.textContent = data.predicted_score.toFixed(1);
  predictionNotesEl.innerHTML = "";
  data.notes.forEach((note) => {
    const li = document.createElement("li");
    li.textContent = note;
    predictionNotesEl.appendChild(li);
  });
};

const debouncePrediction = () => {
  if (predictTimeout) {
    clearTimeout(predictTimeout);
  }
  predictTimeout = setTimeout(updatePrediction, 300);
};

entryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();
  saveStatus.textContent = "Saving...";

  const formData = new FormData(entryForm);
  const payload = Object.fromEntries(formData.entries());

  const response = await fetch("/api/entries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();

  if (!response.ok) {
    setErrors(data.errors || {});
    saveStatus.textContent = "Fix the highlighted fields.";
    return;
  }

  entryForm.reset();
  saveStatus.textContent = "Saved!";
  await fetchEntries();
  debouncePrediction();

  setTimeout(() => {
    saveStatus.textContent = "";
  }, 2000);
});

Object.values(predictInputs).forEach((input) => {
  input.addEventListener("input", debouncePrediction);
});

fetchEntries().then((entries) => {
  if (entries.length) {
    const last = entries[entries.length - 1];
    predictInputs.avg_glucose.value = last.avg_glucose;
    predictInputs.glucose_sd.value = last.glucose_sd;
    predictInputs.difficulty.value = last.difficulty;
  }
  updatePrediction();
});
