export const handler = async (event) => {
  // Detect HTTP method
  const method =
    event.httpMethod ||
    event.requestContext?.http?.method ||
    "UNKNOWN";

  // Decode body if present
  let body = null;
  if (event.body) {
    body = event.isBase64Encoded
      ? Buffer.from(event.body, "base64").toString("utf-8")
      : event.body;
  }

  // Build response
  const responseBody = {
    message: "webhook callback",
    method,
    headers: event.headers || {},
  };

  if (method === "POST") {
    responseBody.body = body;
  }

  const response = {
    statusCode: 200,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(responseBody),
  };

  // --- Send to webhook ---
    const webhookUrl = process.env.WEBHOOK_URL; // get from environment variable
  try {
    await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        statusCode: response.statusCode,
        headers: response.headers,
        content: response.body,
        method,
      }),
    });
  } catch (err) {
    console.error("Webhook error:", err);
    // optionally, you could include webhook failure info in the response
  }

  // Return normal Lambda response only after webhook call finishes
  return response;
};
