import { useEffect } from 'react';
import { apiRequest } from '../services/apiClient';
import { useLanguage } from '../context/LanguageContext';

// A safety-net for legacy screens that still contain raw English text. New UI
// should use dictionary keys/TranslatedText; this observer covers missed text,
// placeholders and accessibility labels without touching inputs, code or numbers.
const originalText = new WeakMap();
const originalAttributes = new WeakMap();
const translatedNodes = new WeakSet();
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'CODE', 'PRE', 'TEXTAREA', 'INPUT', 'SELECT', 'OPTION', 'SVG', 'PATH']);

function isTranslatableText(value) {
  const text = String(value || '').trim();
  if (text.length < 2 || text.length > 700 || !/[A-Za-z]{2}/.test(text)) return false;
  if (/^[\d\s.,:%$₹+\-/()]+$/.test(text)) return false;
  if (/^(https?:\/\/|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$)/.test(text)) return false;
  return true;
}

export default function AutoTranslateDocument() {
  const { currentLang } = useLanguage();

  useEffect(() => {
    let cancelled = false;
    let scheduled = false;
    const pending = new Set();
    const textOriginals = new Map();
    const attributeOriginals = new Map();

    const ignored = (node) => {
      const parent = node?.parentElement;
      return !parent || SKIP_TAGS.has(parent.tagName) ||
        parent.closest('[data-no-translate],.notranslate,[contenteditable="true"]') ||
        parent.getAttribute('translate') === 'no';
    };

    const scan = (root = document.body) => {
      if (!root || cancelled) return;
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        if (ignored(node) || !isTranslatableText(originalText.get(node) ?? node.nodeValue)) continue;
        if (!originalText.has(node)) originalText.set(node, node.nodeValue);
        const source = originalText.get(node);
        textOriginals.set(node, source);
        pending.add(node);
      }
      const elements = [ ...(root.nodeType === 1 ? [root] : []), ...(root.querySelectorAll?.('*') || []) ];
      for (const element of elements) {
        if (SKIP_TAGS.has(element.tagName) || element.closest?.('[data-no-translate],.notranslate')) continue;
        for (const attr of ['placeholder', 'title', 'aria-label']) {
          const value = element.getAttribute?.(attr);
          if (!isTranslatableText(originalAttributes.get(element)?.[attr] ?? value)) continue;
          if (!originalAttributes.has(element)) originalAttributes.set(element, {});
          const originals = originalAttributes.get(element);
          if (!(attr in originals)) originals[attr] = value;
          attributeOriginals.set(element, { ...(attributeOriginals.get(element) || {}), [attr]: originals[attr] });
        }
      }
      if (!scheduled && (pending.size || attributeOriginals.size)) {
        scheduled = true;
        queueMicrotask(runBatch);
      }
    };

    const restoreOriginal = () => {
      for (const [node, source] of textOriginals) if (node.isConnected) node.nodeValue = source;
      for (const [element, attrs] of attributeOriginals) {
        if (!element.isConnected) continue;
        for (const [attr, source] of Object.entries(attrs)) element.setAttribute(attr, source ?? '');
      }
      pending.clear();
      textOriginals.clear();
      attributeOriginals.clear();
    };

    async function runBatch() {
      scheduled = false;
      if (cancelled) return;
      const nodes = [...pending].filter((node) => node.isConnected);
      pending.clear();
      const attrs = [...attributeOriginals.entries()].filter(([el]) => el.isConnected);
      attributeOriginals.clear();
      if (currentLang === 'en') return;
      const entries = [
        ...nodes.map((node) => ({ kind: 'text', target: node, source: textOriginals.get(node) ?? originalText.get(node) ?? node.nodeValue })),
        ...attrs.flatMap(([element, values]) => Object.entries(values).map(([attr, source]) => ({ kind: 'attr', target: element, attr, source }))),
      ].filter((entry) => isTranslatableText(entry.source));
      // Batches obey the backend's 100-text request limit.
      for (let i = 0; i < entries.length && !cancelled; i += 80) {
        const group = entries.slice(i, i + 80);
        try {
          const response = await apiRequest('/translation/batch', {
            method: 'POST',
            body: JSON.stringify({ texts: group.map((entry) => entry.source), target_language: currentLang, source_language: 'en' }),
          });
          const translated = response?.data?.translated_texts;
          if (!Array.isArray(translated)) continue;
          group.forEach((entry, index) => {
            if (!entry.target.isConnected || typeof translated[index] !== 'string') return;
            const value = translated[index];
            if (entry.kind === 'text') {
              // Do not overwrite a node if React or the user changed it while the request was in flight.
              if ((originalText.get(entry.target) ?? entry.target.nodeValue) === entry.source) {
                entry.target.nodeValue = value;
                translatedNodes.add(entry.target);
              }
            } else if (entry.target.getAttribute(entry.attr) === entry.source) {
              entry.target.setAttribute(entry.attr, value);
            }
          });
        } catch (error) {
          console.warn('Automatic page translation failed; dictionary text remains available.', error?.message || error);
        }
      }
    }

    if (currentLang !== 'en') scan();
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'characterData') {
          const node = mutation.target;
          if (translatedNodes.has(node)) {
            translatedNodes.delete(node);
            continue;
          }
          originalText.set(node, node.nodeValue);
          pending.add(node);
        }
        for (const added of mutation.addedNodes || []) {
          if (added.nodeType === Node.ELEMENT_NODE) scan(added);
          else if (added.nodeType === Node.TEXT_NODE && !ignored(added)) {
            originalText.set(added, added.nodeValue);
            pending.add(added);
          }
        }
      }
      if (pending.size && !scheduled) {
        scheduled = true;
        queueMicrotask(runBatch);
      }
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });

    return () => {
      cancelled = true;
      observer.disconnect();
      restoreOriginal();
    };
  }, [currentLang]);

  return null;
}
