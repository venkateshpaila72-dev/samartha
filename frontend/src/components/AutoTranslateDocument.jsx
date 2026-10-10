import { useEffect } from 'react';
import { apiRequest } from '../services/apiClient';
import { useLanguage } from '../context/LanguageContext';

const SKIP_TAGS = new Set(['SCRIPT','STYLE','NOSCRIPT','CODE','PRE','TEXTAREA','INPUT','SELECT','OPTION','SVG','PATH']);
const originals = new WeakMap();
const translated = new WeakSet();
const attrOriginals = new WeakMap();
const trackedNodes = new Set();
const trackedElements = new Set();

function eligible(value) {
  const text = String(value ?? '').trim();
  return text.length >= 2 && text.length <= 500 && /[A-Za-z]{2}/.test(text) &&
    !/^[\d\s.,:%$₹+\-/()]+$/.test(text) &&
    !/^(https?:\/\/|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$)/.test(text);
}

// Safety net for legacy components that still render raw English strings.
// Prefer local dictionary keys for fixed UI and this batch endpoint for missed
// text, placeholders, titles, and accessible labels.
export default function AutoTranslateDocument() {
  const { currentLang } = useLanguage();

  useEffect(() => {
    let disposed = false;
    let scheduled = false;
    const pending = new Map();

    const shouldSkip = (element) => !element || SKIP_TAGS.has(element.tagName) ||
      Boolean(element.closest?.('[data-no-translate],.notranslate,[contenteditable="true"]')) ||
      element.getAttribute?.('translate') === 'no';

    const queueElement = (element) => {
      if (!element || shouldSkip(element)) return;
      for (const attr of ['placeholder','title','aria-label']) {
        const value = element.getAttribute(attr);
        if (!eligible(value)) continue;
        let stored = attrOriginals.get(element);
        if (!stored) { stored = {}; attrOriginals.set(element, stored); }
        trackedElements.add(element);
        if (!(attr in stored)) stored[attr] = value;
        pending.set(element, { kind: 'attribute', attr, source: stored[attr] });
      }
    };

    const scan = (root) => {
      if (!root || disposed || currentLang === 'en') return;
      const elements = [];
      if (root.nodeType === Node.ELEMENT_NODE) elements.push(root);
      if (root.querySelectorAll) elements.push(...root.querySelectorAll('*'));
      for (const element of elements) {
        if (shouldSkip(element)) continue;
        queueElement(element);
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          if (shouldSkip(node.parentElement)) continue;
          if (translated.has(node)) continue;
          const value = originals.has(node) ? originals.get(node) : node.nodeValue;
          if (!eligible(value)) continue;
          if (!originals.has(node)) originals.set(node, value);
          trackedNodes.add(node);
          pending.set(node, { kind: 'text', source: originals.get(node) });
        }
      }
      schedule();
    };

    const schedule = () => {
      if (scheduled || !pending.size || disposed) return;
      scheduled = true;
      queueMicrotask(async () => {
        scheduled = false;
        const entries = [...pending.entries()];
        pending.clear();
        for (let i = 0; i < entries.length && !disposed; i += 60) {
          const batch = entries.slice(i, i + 60).filter(([target]) => target.isConnected);
          if (!batch.length) continue;
          try {
            const response = await apiRequest('/translation/batch', {
              method: 'POST',
              body: JSON.stringify({
                texts: batch.map(([, item]) => item.source),
                target_language: currentLang,
                source_language: 'en',
              }),
            });
            const values = response?.data?.translated_texts;
            if (!Array.isArray(values)) continue;
            batch.forEach(([target, item], index) => {
              if (!target.isConnected || typeof values[index] !== 'string' || !values[index].trim()) return;
              if (item.kind === 'text') {
                if ((originals.get(target) ?? target.nodeValue) !== item.source) return;
                target.nodeValue = values[index];
                translated.add(target);
              } else if (target.getAttribute(item.attr) === item.source) {
                target.setAttribute(item.attr, values[index]);
              }
            });
          } catch (error) {
            console.warn('Page translation failed; keeping original text.', error?.message || error);
          }
        }
      });
    };

    if (currentLang !== 'en') scan(document.body);
    const observer = new MutationObserver((mutations) => {
      if (currentLang === 'en') return;
      for (const mutation of mutations) {
        if (mutation.type === 'characterData') {
          const node = mutation.target;
          if (translated.has(node)) { translated.delete(node); continue; }
          if (eligible(node.nodeValue)) {
            originals.set(node, node.nodeValue);
            pending.set(node, { kind: 'text', source: node.nodeValue });
          }
        }
        mutation.addedNodes?.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) scan(node);
          else if (node.nodeType === Node.TEXT_NODE && !shouldSkip(node.parentElement) && eligible(node.nodeValue)) {
            originals.set(node, node.nodeValue);
            pending.set(node, { kind: 'text', source: node.nodeValue });
          }
        });
      }
      schedule();
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });

    return () => {
      disposed = true;
      observer.disconnect();
      // Restore text from its source when switching languages so we never
      // translate a translation as if it were English.
      for (const node of trackedNodes) {
        const source = originals.get(node);
        if (node.isConnected && source !== undefined) node.nodeValue = source;
        translated.delete(node);
      }
      for (const element of trackedElements) {
        const attrs = attrOriginals.get(element) || {};
        if (element.isConnected) Object.entries(attrs).forEach(([attr, source]) => element.setAttribute(attr, source));
      }
    };
  }, [currentLang]);

  return null;
}
