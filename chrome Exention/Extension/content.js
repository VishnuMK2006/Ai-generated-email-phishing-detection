(function () {
  const MAX_TEXT_LENGTH = 3000;

  function normalizeText(rawText) {
    if (!rawText || typeof rawText !== 'string') return '';

    return rawText
      .replace(/\s+/g, ' ')
      .replace(/\u00A0/g, ' ')
      .trim();
  }

  function getTextFromElement(element) {
    if (!element) return '';

    const cloned = element.cloneNode(true);

    cloned.querySelectorAll(
      'script, style, noscript, img, svg, input, textarea, button, select, video, audio, iframe, object'
    ).forEach((node) => node.remove());

    return normalizeText(cloned.innerText || '');
  }

  function extractGmailMessageText() {
    const selectors = [
      '.ii.gt',
      '.a3s.aiL',
      '.adn',
      '[data-message-id]',
      '.gmail_quote',
      '.msg',
    ];

    let bestText = '';
    let bestLength = 0;

    selectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((element) => {
        const text = getTextFromElement(element);

        if (text.length > bestLength) {
          bestText = text;
          bestLength = text.length;
        }
      });
    });

    return bestText;
  }

  function extractVisibleText() {
    const body = document.body;
    if (!body) return '';

    const gmailText = extractGmailMessageText();
    if (gmailText.length >= 50) {
      return gmailText.length > MAX_TEXT_LENGTH
        ? gmailText.slice(0, MAX_TEXT_LENGTH)
        : gmailText;
    }

    const text = body.innerText || '';
    const normalized = normalizeText(text);

    if (!normalized) return '';

    return normalized.length > MAX_TEXT_LENGTH
      ? normalized.slice(0, MAX_TEXT_LENGTH)
      : normalized;
  }

  async function fetchRawEmailHeaders() {
    // Case 1: We are already on the "Show Original" page
    const headerTable = document.querySelector('table.datatable');
    if (headerTable) {
      const rawMessageContainer = document.querySelector('pre') || document.querySelector('.message');
      if (rawMessageContainer) {
        return rawMessageContainer.innerText.trim();
      }
      return document.body.innerText;
    }

    // Case 2: We are in the standard Gmail UI. Find the legacy message ID.
    const messageNode = document.querySelector('[data-legacy-message-id]');
    const legacyMsgId = messageNode ? messageNode.getAttribute('data-legacy-message-id') : null;

    if (!legacyMsgId) {
      return ''; // Cannot find message ID, return empty
    }

    try {
      // Invisible background fetch directly to the raw .eml download endpoint
      const url = `https://mail.google.com/mail/u/0/?view=att&th=${legacyMsgId}&attid=0&disp=comp&safe=1&zw`;
      const response = await fetch(url);
      const rawEmlText = await response.text();
      return rawEmlText.trim();
    } catch (error) {
      console.error('Error fetching raw email:', error);
      return '';
    }
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === 'GET_VISIBLE_TEXT') {
      (async () => {
        const rawHeaders = await fetchRawEmailHeaders();
        sendResponse({
          ok: true,
          text: extractVisibleText(),
          url: window.location.href,
          headers: rawHeaders
        });
      })();
      return true; // Keep the message channel open for the async response
    }

    return false;
  });
})();
