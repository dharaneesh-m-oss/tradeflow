document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const fileInput = document.getElementById("fileInput");
    const resultDiv = document.getElementById("result");

    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a file");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    resultDiv.innerHTML = "Processing...";

    try {
        const response = await fetch("/upload/", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        resultDiv.innerHTML = `
            <h3>Status: ${data.review_status}</h3>
            <p><strong>Converted INR:</strong> ${data.converted_value_inr || "-"}</p>
            <pre>${JSON.stringify(data.auto_filled_form, null, 2)}</pre>
        `;
    } catch (error) {
        resultDiv.innerHTML = "Error processing document.";
        console.error(error);
    }
});