import { useCallback, useEffect, useRef, useState } from "react";


function readDraft(key) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? undefined : JSON.parse(raw);
  } catch {
    return undefined;
  }
}


export function firstDraftIndex(prefix, questions = []) {
  return questions.findIndex((question) => readDraft(`${prefix}:${question.id}`) !== undefined);
}


export async function flushStoredAnswerDrafts(prefix, questions = [], save) {
  for (let index = 0; index < questions.length; index += 1) {
    const question = questions[index];
    const key = `${prefix}:${question.id}`;
    const value = readDraft(key);
    if (value === undefined) continue;
    try {
      await save(question.id, value);
      window.localStorage.removeItem(key);
    } catch {
      return { ok: false, index, questionId: question.id };
    }
  }
  return { ok: true, index: -1, questionId: null };
}


export function useAnswerAutosave({ storageKey, initialValue, save }) {
  const [value, setValue] = useState(() => readDraft(storageKey) ?? initialValue ?? null);
  const [status, setStatus] = useState(() => readDraft(storageKey) === undefined ? "idle" : "retry");
  const timerRef = useRef(null);
  const pendingRef = useRef(null);
  const saveRef = useRef(save);
  saveRef.current = save;

  const persist = useCallback(async (nextValue, key = storageKey) => {
    if (nextValue === undefined) return true;
    pendingRef.current = { key, value: nextValue };
    setStatus("saving");
    try {
      await saveRef.current(nextValue);
      if (pendingRef.current?.key === key && Object.is(pendingRef.current.value, nextValue)) {
        pendingRef.current = null;
        window.localStorage.removeItem(key);
        setStatus("saved");
      }
      return true;
    } catch {
      setStatus("retry");
      return false;
    }
  }, [storageKey]);

  useEffect(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    const draft = readDraft(storageKey);
    setValue(draft ?? initialValue ?? null);
    setStatus(draft === undefined ? "idle" : "retry");
    pendingRef.current = draft === undefined ? null : { key: storageKey, value: draft };
  }, [initialValue, storageKey]);

  useEffect(() => {
    const retry = () => {
      const pending = pendingRef.current;
      if (pending) persist(pending.value, pending.key);
    };
    window.addEventListener("online", retry);
    return () => window.removeEventListener("online", retry);
  }, [persist]);

  useEffect(() => () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
  }, []);

  const change = useCallback((nextValue) => {
    setValue(nextValue);
    window.localStorage.setItem(storageKey, JSON.stringify(nextValue));
    pendingRef.current = { key: storageKey, value: nextValue };
    setStatus("saving");
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => persist(nextValue), 250);
  }, [persist, storageKey]);

  const flush = useCallback(async () => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const pending = pendingRef.current;
    return pending ? persist(pending.value, pending.key) : true;
  }, [persist]);

  return { value, change, flush, status };
}


export function saveStatusLabel(status) {
  if (status === "saving") return "正在保存";
  if (status === "saved") return "已保存";
  if (status === "retry") return "待重试";
  return "尚未作答";
}
