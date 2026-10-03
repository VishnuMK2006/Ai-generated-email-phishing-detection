const API_URL = 'http://127.0.0.1:8000/analyze-email';
const DEFAULT_TIMEOUT_MS = 15000;

async function fetchWithTimeout(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function classifyPage(text, url, headers, forceBodyCheck) {
  const payload = { 
    body_text: text,
    raw_header: headers || '',
    predict_body_if_phishing: !!forceBodyCheck 
  };

  const response = await fetchWithTimeout(API_URL, {
    method: 'POST',
    headers: {
      'x-api-key': 'my-secret-key',
    },
    body: JSON.stringify(payload),
  }, DEFAULT_TIMEOUT_MS);

  if (!response.ok) {
    const errText = await response.text().catch(() => '');
    throw new Error(`API error ${response.status}: ${errText || response.statusText}`);
  }

  const data = await response.json();
  if (!data || typeof data !== 'object') {
    throw new Error('Invalid API response format');
  }

  return {
    predicted_label: data.predicted_label || null,
    predicted_class: data.predicted_class ?? null,
    confidence: typeof data.confidence === 'number' ? data.confidence : null,
    header_spam_probability: typeof data.header_spam_probability === 'number' ? data.header_spam_probability : null,
    body_prediction: data.body_prediction || null,
    raw: data,
    url,
  };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'ANALYZE_PAGE') {
    classifyPage(message.text, message.url, message.headers, message.forceBodyCheck)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) => {
        sendResponse({
          ok: false,
          error: error.message || 'Analysis failed',
        });
      });

    return true;
  }

  return false;
});
