const STATUS = {
  fetching: {
    text: '⏳ Fetching Email...',
    className: 'status-warning',
  },
  analyzing: {
    text: '⏳ Analyzing...',
    className: 'status-warning',
  },
  legitimate: {
    text: '✅ Legitimate Email',
    className: 'status-success',
  },
  phishing: {
    text: '⚠️ Potential Phishing',
    className: 'status-danger',
  },
  inconclusive: {
    text: '⚠️ Analysis Inconclusive',
    className: 'status-warning',
  },
};

const PHISHING_CONFIDENCE_THRESHOLD = 0.75;
const LEGITIMATE_CONFIDENCE_THRESHOLD = 0.55;

function setStatus(key, details = {}) {
  const statusEl = document.getElementById('status');
  const predictionEl = document.getElementById('prediction');
  const confidenceEl = document.getElementById('confidence');
  const headerPredictionEl = document.getElementById('headerPrediction');
  const bodyPredictionEl = document.getElementById('bodyPrediction');

  if (STATUS[key]) {
    statusEl.textContent = STATUS[key].text;
    statusEl.className = `value ${STATUS[key].className}`;
  }

  if (details.predictedLabel) {
    predictionEl.textContent = details.predictedLabel;
  }
  
  if (details.confidence != null) {
    confidenceEl.textContent = `${Number(details.confidence).toFixed(4)}`;
  }

  if (details.headerProb != null) {
    const prob = (details.headerProb * 100).toFixed(1);
    headerPredictionEl.textContent = `Spam Prob: ${prob}%`;
    if (details.headerProb >= 0.5) {
      headerPredictionEl.className = 'value status-danger';
    } else {
      headerPredictionEl.className = 'value status-success';
    }
  } else if (key === 'analyzing' || key === 'fetching') {
    if (headerPredictionEl) headerPredictionEl.textContent = '...';
    if (headerPredictionEl) headerPredictionEl.className = 'value muted';
  }

  if (details.bodyPrediction !== undefined) {
    const bp = details.bodyPrediction;
    if (!bp || bp === 'Skipped' || bp === null) {
      bodyPredictionEl.textContent = 'Skipped';
      bodyPredictionEl.className = 'value muted';
    } else {
      bodyPredictionEl.textContent = bp;
      if (bp.toLowerCase().includes('phish')) {
        bodyPredictionEl.className = 'value status-danger';
      } else {
        bodyPredictionEl.className = 'value status-success';
      }
    }
  } else if (key === 'analyzing' || key === 'fetching') {
    if (bodyPredictionEl) bodyPredictionEl.textContent = '...';
    if (bodyPredictionEl) bodyPredictionEl.className = 'value muted';
  }
}

async function analyzeCurrentTab(forceBodyCheck = false) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    setStatus('inconclusive');
    return;
  }

  document.getElementById('pageTitle').textContent = tab.title || 'Unknown page';
  document.getElementById('pageUrl').textContent = tab.url || 'Unknown URL';
  
  // Hide verify button when starting a new analysis
  document.getElementById('verifyBodyButton').style.display = 'none';

  setStatus('fetching');

  try {
    let payload = { text: '', url: tab.url || '' };

    try {
      payload = await chrome.tabs.sendMessage(tab.id, { type: 'GET_VISIBLE_TEXT' });
    } catch (error) {
      const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: async () => {
          const text = document.body ? (document.body.innerText || '').replace(/\s+/g, ' ').trim() : '';
          
          // Case 1: "Show Original" page
          const headerTable = document.querySelector('table.datatable');
          if (headerTable) {
            const rawMessageContainer = document.querySelector('pre') || document.querySelector('.message');
            const headers = rawMessageContainer ? rawMessageContainer.innerText.trim() : document.body.innerText;
            return {
              text: text.length > 3000 ? text.slice(0, 3000) : text,
              url: window.location.href,
              headers: headers
            };
          }

          // Case 2: Standard Gmail UI
          const messageNode = document.querySelector('[data-legacy-message-id]');
          const legacyMsgId = messageNode ? messageNode.getAttribute('data-legacy-message-id') : null;
          let headers = '';
          
          if (legacyMsgId) {
            try {
              const url = `https://mail.google.com/mail/u/0/?view=att&th=${legacyMsgId}&attid=0&disp=comp&safe=1&zw`;
              const response = await fetch(url);
              headers = await response.text();
              headers = headers.trim();
            } catch (error) {
              console.error('Error fetching raw email:', error);
            }
          }
          
          return {
            text: text.length > 3000 ? text.slice(0, 3000) : text,
            url: window.location.href,
            headers: headers
          };
        },
      });
      payload = result || { text: '', url: tab.url || '', headers: '' };
    }
    
    // Display extracted headers if they exist
    if (payload.headers && payload.headers.trim() !== '') {
      document.getElementById('headerField').style.display = 'flex';
      document.getElementById('emailHeaders').value = payload.headers;
    } else {
      document.getElementById('headerField').style.display = 'none';
    }

    if (!payload.text || payload.text.length < 20) {
      setStatus('inconclusive');
      return;
    }

    setStatus('analyzing');

    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage(
        {
          type: 'ANALYZE_PAGE',
          text: payload.text,
          url: payload.url,
          headers: payload.headers || '',
          forceBodyCheck: forceBodyCheck
        },
        (resp) => {
          resolve(resp || { ok: false, error: 'No response from background' });
        }
      );
    });

    if (!response.ok || !response.result) {
      setStatus('inconclusive');
      return;
    }

    const { predicted_label, confidence, header_spam_probability, body_prediction } = response.result;
    const normalized = (predicted_label || '').toLowerCase();
    const confidenceValue = typeof confidence === 'number' ? confidence : 0;

    let statusKey = 'inconclusive';

    if (normalized === 'legitimate' || normalized === 'legitimatef') {
      statusKey = confidenceValue >= LEGITIMATE_CONFIDENCE_THRESHOLD ? 'legitimate' : 'inconclusive';
    } else if (
      normalized === 'phishing' || 
      normalized.includes('phish') ||
      ['account_takeover', 'credential_harvesting', 'data_exfiltration', 'financial_fraud', 'identity_abuse', 'infrastructure_exploitation', 'malware_delivery'].includes(normalized)
    ) {
      statusKey = confidenceValue >= PHISHING_CONFIDENCE_THRESHOLD ? 'phishing' : 'inconclusive';
    }

    setStatus(statusKey, { 
      predictedLabel: predicted_label || 'Unknown', 
      confidence: confidenceValue,
      headerProb: header_spam_probability,
      bodyPrediction: body_prediction || 'Skipped'
    });

    // Determine if we need to show the Verify with Body button
    // Show it if header predicted phishing (>=0.5) but body was skipped
    if (header_spam_probability >= 0.5 && !body_prediction) {
      document.getElementById('verifyBodyButton').style.display = 'block';
    }

  } catch (error) {
    setStatus('inconclusive');
  }
}

document.getElementById('analyzeButton').addEventListener('click', () => analyzeCurrentTab(false));
document.getElementById('verifyBodyButton').addEventListener('click', () => analyzeCurrentTab(true));
analyzeCurrentTab(false);
